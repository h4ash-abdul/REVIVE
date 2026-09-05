import json
import random
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.domain.models import Mandate, PaymentAttempt, PaymentObligation, ObligationStatus, PolicyDecision
from src.domain.audit import RecoveryTrace, RecoveryEventType
from src.audit.trail import AuditLogger
from src.simulation.latent.models import CustomerLatentState, MerchantLatentState
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.decision.generator import CandidateGenerator
from src.features.builder import PointInTimeFeatureBuilder
from src.models.hierarchical import HierarchicalPredictor
from src.decision.scorer import CandidateScoringService
from src.decision.ml_strategies import MLProbabilityStrategy
from src.decision.policy import DeterministicPolicyEngine
from src.configs.models import PolicyConfig
from src.execution.adapter import SimulatedExecutionAdapter, OutcomeVerifier

app = FastAPI(title="REVIVE End-to-End Demo API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
DEMO_CASES = {}
TRACES: Dict[str, RecoveryTrace] = {}

# Services
feature_builder = PointInTimeFeatureBuilder()
import joblib
with open("models/artifacts/model_manifest_v1.1.json", "r") as f:
    manifest = json.load(f)
pipeline = joblib.load(manifest["artifact_path"])
predictor = HierarchicalPredictor(base_model=pipeline)
scorer = CandidateScoringService(feature_builder, predictor)
generator = CandidateGenerator(days_ahead=30)
policy_config = PolicyConfig(policy_version="1.0", max_retries_per_mandate=3, min_hours_between_retries=1, allowed_execution_windows_utc=["00:00-23:59"], stop_on_success=True)
policy_engine = DeterministicPolicyEngine(policy_config)
outcome_engine = OutcomeEngine(random.Random(42))
adapter = SimulatedExecutionAdapter(outcome_engine)
verifier = OutcomeVerifier()

class DemoCaseResponse(BaseModel):
    scenario_key: str
    title: str
    mandate_id: UUID
    amount: float
    failure_code: str
    initial_probability: float

def init_case(c: dict) -> tuple:
    m_dict = c["mandate"]
    m = Mandate(**m_dict)
    h = [PaymentAttempt(**h_dict) for h_dict in c["history"]]
    c_lat = CustomerLatentState(**c["customer_latent"])
    m_lat = MerchantLatentState(**c["merchant_latent"])
    
    # Initialize Trace
    last_attempt = sorted(h, key=lambda x: x.timestamp)[-1]
    obligation = PaymentObligation(
        obligation_id=uuid4(),
        mandate_id=m.mandate_id,
        due_time=last_attempt.timestamp,
        amount=m.amount,
        status=ObligationStatus.ACTIVE_RECOVERY,
        original_attempt_id=last_attempt.attempt_id
    )
    
    trace = RecoveryTrace(
        mandate_id=m.mandate_id,
        obligation_id=obligation.obligation_id,
        amount=m.amount,
        currency="INR",
        failure_category="technical" if last_attempt.network_return_code in ["ERR_CONNECTION_TIMEOUT", "ERR_GATEWAY", "E0001_SYS", "technical_failure"] else "financial",
        failure_code=last_attempt.network_return_code or "unknown",
        budget_remaining=policy_config.max_retries_per_mandate
    )
    
    case_data = {
        "title": c["title"],
        "mandate": m,
        "history": h,
        "c_lat": c_lat,
        "m_lat": m_lat,
        "raw": c
    }
    
    trace_data = {
        "trace": trace,
        "obligation": obligation,
        "logger": AuditLogger()
    }
    return case_data, trace_data

@app.on_event("startup")
def load_demo_cases():
    cases_path = Path("data/demo/cases.json")
    if cases_path.exists():
        with open(cases_path, "r") as f:
            cases = json.load(f)
            for c in cases:
                case_data, trace_data = init_case(c)
                DEMO_CASES[c["scenario_key"]] = case_data
                TRACES[c["scenario_key"]] = trace_data
                
                # Precompute initial probabilities for the queue
                current_time = datetime.now(timezone.utc)
                m = case_data["mandate"]
                h = case_data["history"]
                raw_candidates = generator.generate(m, current_time)
                policy_decisions = policy_engine.pre_filter(raw_candidates, m, h, trace_data["obligation"])
                valid_candidates = [cand for cand, dec in zip(raw_candidates, policy_decisions) if dec.is_allowed]
                
                if valid_candidates:
                    strategy = MLProbabilityStrategy(policy_engine, scorer)
                    strategy.global_mandates = [m]
                    strat_res = strategy.evaluate(m, h, current_time, trace_data["obligation"], valid_candidates)
                    if strat_res.selected_action:
                        preds_dict = scorer.score_candidates(valid_candidates, m, h, [m], current_time)
                        case_data["initial_probability"] = preds_dict[strat_res.selected_action.candidate_id].probability
                    else:
                        case_data["initial_probability"] = 0.0
                else:
                    case_data["initial_probability"] = 0.0
                


@app.get("/cases", response_model=List[DemoCaseResponse])
def get_cases():
    res = []
    for k, v in DEMO_CASES.items():
        res.append(DemoCaseResponse(
            scenario_key=k,
            title=v["title"],
            mandate_id=v["mandate"].mandate_id,
            amount=v["mandate"].amount,
            failure_code=v["history"][-1].network_return_code or "unknown",
            initial_probability=v.get("initial_probability", 0.0)
        ))
    return res

@app.post("/cases/{key}/reset")
def reset_case(key: str):
    if key not in DEMO_CASES:
        raise HTTPException(status_code=404)
        
    c = DEMO_CASES[key]["raw"]
    case_data, trace_data = init_case(c)
    case_data["initial_probability"] = DEMO_CASES[key]["initial_probability"]
    DEMO_CASES[key] = case_data
    TRACES[key] = trace_data
    return {"status": "reset"}

@app.get("/cases/{key}/trace")
def get_trace(key: str):
    if key not in TRACES:
        raise HTTPException(status_code=404)
    t = TRACES[key]
    trace_obj = t["trace"].model_copy()
    trace_obj.audit_trail = t["logger"].get_events()
    
    # Return as dict to inject obligation status
    res = trace_obj.model_dump()
    res["obligation_status"] = t["obligation"].status.value
    return res

@app.post("/cases/{key}/trigger")
def trigger_recovery(key: str):
    if key not in DEMO_CASES:
        raise HTTPException(status_code=404)
        
    case = DEMO_CASES[key]
    t = TRACES[key]
    
    mandate = case["mandate"]
    history = case["history"]
    c_lat = case["c_lat"]
    m_lat = case["m_lat"]
    
    obligation = t["obligation"]
    trace: RecoveryTrace = t["trace"]
    logger: AuditLogger = t["logger"]
    
    current_time = datetime.now(timezone.utc)
    
    if obligation.status != ObligationStatus.ACTIVE_RECOVERY:
        raise HTTPException(status_code=400, detail="Obligation is already resolved or exhausted.")
        
    # 1. Failure Classified
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.PAYMENT_FAILED, "Bank", current_time, {"code": trace.failure_code})
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.FAILURE_CLASSIFIED, "Revive", current_time, {"category": trace.failure_category})
    
    # 2. Candidates Generated
    raw_candidates = generator.generate(mandate, current_time)
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.CANDIDATES_GENERATED, "Generator", current_time, {"count": len(raw_candidates)})
    
    # 3. Policy Precheck
    policy_decisions = policy_engine.pre_filter(raw_candidates, mandate, history, obligation)
    valid_candidates = [c for c, d in zip(raw_candidates, policy_decisions) if d.is_allowed]
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.POLICY_PRECHECK, "PolicyEngine", current_time, {"valid_count": len(valid_candidates)})
    
    if not valid_candidates:
        trace.budget_remaining = 0
        t["obligation"] = obligation.model_copy(update={"status": ObligationStatus.FAILED_EXHAUSTED})
        raise HTTPException(status_code=400, detail="No policy-valid candidates generated (e.g. budget exhausted or mandate restricted).")
        
    # 4. Features & Prediction
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.FEATURES_COMPUTED, "FeatureBuilder", current_time, {"feature_count": 25})
    
    strategy = MLProbabilityStrategy(policy_engine, scorer)
    strategy.global_mandates = [mandate]
    
    strat_res = strategy.evaluate(mandate, history, current_time, obligation, valid_candidates)
    trace.strategy_result = strat_res
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.RECOVERY_PREDICTION_CREATED, "MLPredictor", current_time, {"mode": strat_res.prediction_mode})
    
    if not strat_res.selected_action:
        raise HTTPException(status_code=400, detail="Strategy could not select a valid action.")
        
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.ACTION_SELECTED, "Strategy", current_time, {"action_time": strat_res.selected_time.isoformat()})
    
    # 5. Execution Requested
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.EXECUTION_REQUESTED, "Revive", current_time, {"action_id": str(strat_res.selected_action.candidate_id)})
    
    final_decision = strat_res.policy_decisions[0]
    exec_record, sim_attempt = adapter.execute(strat_res.selected_action, final_decision, obligation, mandate, c_lat, m_lat, current_time)
    
    trace.execution_record = exec_record
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.EXECUTION_COMPLETED, "ExecutionAdapter", current_time, {"status": exec_record.status})
    
    # 6. Verification
    if exec_record.status == "COMPLETED" and sim_attempt:
        history.append(sim_attempt)
        
    outcome = verifier.verify(exec_record, sim_attempt, current_time)
    trace.outcome = outcome
    logger.log(mandate.mandate_id, obligation.obligation_id, RecoveryEventType.OUTCOME_VERIFIED, "Verifier", current_time, {"success": outcome.success, "recovered_amount": outcome.recovered_amount})
    
    if outcome.success:
        t["obligation"] = obligation.model_copy(update={"status": ObligationStatus.SUCCESS})
    else:
        trace.budget_remaining -= 1
        if trace.budget_remaining <= 0:
            t["obligation"] = obligation.model_copy(update={"status": ObligationStatus.FAILED_EXHAUSTED})
        
    return {"status": "completed"}
