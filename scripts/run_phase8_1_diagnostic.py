import pandas as pd
import json
import os
import joblib
import random
from uuid import uuid4
from datetime import datetime, timezone
from collections import defaultdict

from src.configs.models import SimulatorConfig, NoiseLevel, Scenario, PolicyConfig
from src.simulation.generator import DataGenerator
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.decision.policy import DeterministicPolicyEngine
from src.decision.baselines import SmartHistoricalHeuristicStrategy
from src.decision.ml_strategies import MLProbabilityStrategy, MLExpectedValueStrategy
from src.decision.scorer import CandidateScoringService
from src.features.builder import PointInTimeFeatureBuilder
from src.features.classifier import RuleBasedFailureClassifier
from src.models.hierarchical import HierarchicalPredictor
from src.evaluation.benchmark import BenchmarkRunner, BenchmarkUniverse
from src.domain.models import CohortSnapshot, AttemptStatus, PaymentObligation, ObligationStatus, PaymentAttempt

def get_failure_category(classifier, history, mandate):
    if not history: return "unknown"
    cat = classifier.classify(history[-1], mandate)
    return cat.category.value

def run_diagnostics():
    print("Running Diagnostics...")
    os.makedirs("data/evaluation/phase8", exist_ok=True)
    
    seed = 42
    sim_config = SimulatorConfig(
        simulator_version="v2.1",
        seed=seed,
        noise_level=NoiseLevel.MEDIUM,
        scenario=Scenario.STRONG_TEMPORAL_SIGNAL,
        time_period_days=60,
        customer_archetypes_distribution={
            "salary_cycle_regular": 0.4,
            "irregular_gig": 0.2,
            "chronic_low_balance": 0.15,
            "thin_history": 0.15,
            "technical_decline_prone": 0.1
        }
    )
    
    generator = DataGenerator(sim_config)
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    generator.run(start_date, 60, 1000, 50, 2)
    
    snapshot = CohortSnapshot(
        snapshot_id=uuid4(),
        experiment_id=uuid4(),
        customers=generator.observable_customers,
        merchants=generator.observable_merchants,
        mandates=list(generator.observable_mandates),
        initial_history=generator.observable_events
    )
    latents_c = generator.latent_customers
    latents_m = generator.latent_merchants
    
    current_time = datetime(2025, 3, 2, tzinfo=timezone.utc)
    
    policy_config = PolicyConfig(
        policy_version="v1.0",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    policy_engine = DeterministicPolicyEngine(policy_config)
    
    with open("models/artifacts/model_manifest_v1.1.json", "r") as f:
        manifest = json.load(f)
    pipeline = joblib.load(manifest["artifact_path"])
    predictor = HierarchicalPredictor(base_model=pipeline)
    feature_builder = PointInTimeFeatureBuilder()
    classifier = RuleBasedFailureClassifier()
    scorer = CandidateScoringService(feature_builder, predictor)
    
    strat_smart = SmartHistoricalHeuristicStrategy(policy_engine, snapshot.initial_history)
    strat_smart.global_mandates = snapshot.mandates
    strat_ml_prob = MLProbabilityStrategy(policy_engine, scorer)
    strat_ml_prob.global_mandates = snapshot.mandates
    strat_ml_ev = MLExpectedValueStrategy(policy_engine, scorer, action_cost=0.0)
    strat_ml_ev.global_mandates = snapshot.mandates
    
    # We will override _evaluate_mandate to collect data
    class DiagnosticRunner(BenchmarkRunner):
        def _evaluate_mandate(self, universe: BenchmarkUniverse, mandate):
            # Normal evaluation but track traces
            attempt_count = 0
            policy_violations = 0
            stop_reason = "Unknown"
            current_t = self.current_time
            initial_history = universe.get_history(mandate.mandate_id)
            last_attempt = initial_history[-1] if initial_history else None
            
            obligation = PaymentObligation(
                obligation_id=uuid4(), mandate_id=mandate.mandate_id,
                due_time=last_attempt.timestamp if last_attempt else current_t,
                amount=mandate.amount, status=ObligationStatus.ACTIVE_RECOVERY,
                original_attempt_id=last_attempt.attempt_id if last_attempt else None,
                retry_attempt_ids=[]
            )
            
            from src.decision.generator import CandidateGenerator
            gen = CandidateGenerator(days_ahead=30, hours_of_day=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
            
            trace = []
            
            while True:
                history = universe.get_history(mandate.mandate_id)
                raw_candidates = gen.generate(mandate, current_t)
                decisions = universe.policy.pre_filter(raw_candidates, mandate, history, obligation)
                valid_cands = [next(c for c in raw_candidates if c.candidate_id == d.candidate_id) for d in decisions if d.is_allowed]
                
                if not valid_cands:
                    break
                    
                strategy_res = universe.strategy.evaluate(mandate, history, current_t, obligation, valid_cands)
                
                if not strategy_res.retry_plan:
                    break
                
                next_action = strategy_res.retry_plan[0]
                
                final_check = universe.policy.final_validate([next_action], mandate, history, obligation)
                if not final_check[0].is_allowed:
                    break
                
                attempt_count += 1
                current_t = next_action.scheduled_time
                
                # We need to know true probability from scorer for analysis
                # But we will do that outside for step 1
                
                c_latent = universe.latent_customers[mandate.customer_id]
                m_latent = universe.latent_merchants[mandate.merchant_id]
                status, code = universe.outcome_engine.execute_payment_attempt(
                    c_latent, m_latent, next_action.amount, current_t, True
                )
                
                attempt = PaymentAttempt(
                    attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_t,
                    amount=next_action.amount, status=status, network_return_code=code
                )
                universe.add_attempt(attempt)
                obligation.retry_attempt_ids.append(attempt.attempt_id)
                
                trace.append({
                    "step": attempt_count,
                    "candidate_id": next_action.candidate_id,
                    "scheduled_time": next_action.scheduled_time,
                    "status": status.value,
                    "prediction_mode": strategy_res.prediction_mode.value if strategy_res.prediction_mode else None
                })
                
                if attempt.status == AttemptStatus.SUCCESS:
                    break
            
            from src.domain.models import MandateResult
            mr = MandateResult(
                mandate_id=mandate.mandate_id, strategy="x", initial_amount=mandate.amount,
                recovered_amount=mandate.amount if any(e.status==AttemptStatus.SUCCESS for e in universe.get_history(mandate.mandate_id)) else 0.0,
                recovered_boolean=any(e.status==AttemptStatus.SUCCESS for e in universe.get_history(mandate.mandate_id)),
                attempt_count=attempt_count, retry_budget_exhausted=(attempt_count >= 3),
                stop_reason=stop_reason, policy_violation_count=policy_violations, execution_error_count=0
            )
            mr._trace = trace
            return mr

    engine1 = OutcomeEngine(random.Random(seed))
    runner_smart = DiagnosticRunner(snapshot, policy_engine, engine1, current_time, latents_c, latents_m)
    res_smart = runner_smart.run_strategy("SmartHeuristic", strat_smart)
    
    engine2 = OutcomeEngine(random.Random(seed))
    runner_ml_prob = DiagnosticRunner(snapshot, policy_engine, engine2, current_time, latents_c, latents_m)
    res_ml_prob = runner_ml_prob.run_strategy("MLProbability", strat_ml_prob)
    
    engine3 = OutcomeEngine(random.Random(seed))
    runner_ml_ev = DiagnosticRunner(snapshot, policy_engine, engine3, current_time, latents_c, latents_m)
    res_ml_ev = runner_ml_ev.run_strategy("MLExpectedValue", strat_ml_ev)
    
    # 1. Decision Disagreement (Step 1 only)
    # Re-run step 1 logic for all mandates to extract precise probabilities and ground-truth
    disagreements = []
    selected_calib = []
    
    from src.decision.generator import CandidateGenerator
    gen = CandidateGenerator(days_ahead=30, hours_of_day=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    
    for mandate in snapshot.mandates:
        history = [e for e in snapshot.initial_history if e.mandate_id == mandate.mandate_id]
        if history and any(e.status == AttemptStatus.SUCCESS for e in history):
            continue
            
        # Common valid candidates
        raw = gen.generate(mandate, current_time)
        obligation = PaymentObligation(
            obligation_id=uuid4(), mandate_id=mandate.mandate_id,
            due_time=history[-1].timestamp if history else current_time,
            amount=mandate.amount, status=ObligationStatus.ACTIVE_RECOVERY,
            original_attempt_id=history[-1].attempt_id if history else None, retry_attempt_ids=[]
        )
        decisions = policy_engine.pre_filter(raw, mandate, history, obligation)
        valid = [next(c for c in raw if c.candidate_id == d.candidate_id) for d in decisions if d.is_allowed]
        
        if not valid: continue
        
        # ML Scores
        preds_dict = scorer.score_candidates(valid, mandate, history, snapshot.mandates, current_time)
        
        # Strategy selections
        res_s = strat_smart.evaluate(mandate, history, current_time, obligation, valid)
        res_p = strat_ml_prob.evaluate(mandate, history, current_time, obligation, valid)
        res_e = strat_ml_ev.evaluate(mandate, history, current_time, obligation, valid)
        
        cand_s = res_s.retry_plan[0] if res_s.retry_plan else None
        cand_p = res_p.retry_plan[0] if res_p.retry_plan else None
        cand_e = res_e.retry_plan[0] if res_e.retry_plan else None
        
        if not (cand_s and cand_p and cand_e): continue
        
        pred_s = preds_dict[cand_s.candidate_id]
        pred_p = preds_dict[cand_p.candidate_id]
        pred_e = preds_dict[cand_e.candidate_id]
        
        ev_s = pred_s.probability * cand_s.amount
        ev_p = pred_p.probability * cand_p.amount
        ev_e = pred_e.probability * cand_e.amount
        
        # Get simulated outcomes using RNG (we need a new isolated RNG per candidate to be fair)
        c_latent = latents_c[mandate.customer_id]
        m_latent = latents_m[mandate.merchant_id]
        
        def sim_outcome(cand):
            rng = random.Random(f"{mandate.mandate_id}_{cand.candidate_id}")
            e = OutcomeEngine(rng)
            s, _ = e.execute_payment_attempt(c_latent, m_latent, cand.amount, cand.scheduled_time, True)
            return 1 if s == AttemptStatus.SUCCESS else 0
            
        out_s = sim_outcome(cand_s)
        out_p = sim_outcome(cand_p)
        out_e = sim_outcome(cand_e)
        
        disagreements.append({
            "mandate_id": str(mandate.mandate_id),
            "amount": mandate.amount,
            "prediction_mode": pred_e.prediction_mode,
            "failure_type": get_failure_category(classifier, history, mandate),
            "smart_candidate": str(cand_s.scheduled_time),
            "ml_probability_candidate": str(cand_p.scheduled_time),
            "ml_ev_candidate": str(cand_e.scheduled_time),
            "smart_predicted_probability": pred_s.probability,
            "ml_probability_predicted_probability": pred_p.probability,
            "ml_ev_predicted_probability": pred_e.probability,
            "smart_EV": ev_s,
            "ml_probability_EV": ev_p,
            "ml_EV": ev_e,
            "smart_outcome": out_s,
            "ml_probability_outcome": out_p,
            "ml_ev_outcome": out_e,
            "agree_s_p": cand_s.candidate_id == cand_p.candidate_id,
            "agree_s_e": cand_s.candidate_id == cand_e.candidate_id,
            "agree_p_e": cand_p.candidate_id == cand_e.candidate_id,
            "all_agree": (cand_s.candidate_id == cand_p.candidate_id) and (cand_p.candidate_id == cand_e.candidate_id)
        })
        
        # Add to selected calibration
        selected_calib.append({"strategy": "SmartHeuristic", "prob": pred_s.probability, "outcome": out_s, "amount": mandate.amount})
        selected_calib.append({"strategy": "MLProbability", "prob": pred_p.probability, "outcome": out_p, "amount": mandate.amount})
        selected_calib.append({"strategy": "MLExpectedValue", "prob": pred_e.probability, "outcome": out_e, "amount": mandate.amount})
        
    df_disagree = pd.DataFrame(disagreements)
    df_disagree.to_csv("data/evaluation/phase8/decision_disagreement.csv", index=False)
    
    df_calib = pd.DataFrame(selected_calib)
    df_calib.to_csv("data/evaluation/phase8/selected_calibration.csv", index=False)
    
    # Analyze df_results for amounts, modes, etc.
    df_results = pd.read_parquet("data/evaluation/phase8/final_mandate_results.parquet")
    
    # 2. Amount Segments
    def bucket_amount(a):
        if a <= 500: return "0-500"
        elif a <= 1000: return "500-1000"
        elif a <= 5000: return "1000-5000"
        return "5000+"
    df_results["amount_bucket"] = df_results["initial_amount"].apply(bucket_amount)
    
    # We also need prediction mode & failure type for df_results. We'll join from df_disagree.
    df_results = df_results.merge(df_disagree[["mandate_id", "prediction_mode", "failure_type"]], on="mandate_id", how="left")
    
    def summarize(group):
        res = []
        for g, df_g in df_results.groupby(group):
            row = {group: g, "mandate_count": df_g["mandate_id"].nunique()}
            for strat in ["SmartHeuristic", "MLProbability", "MLExpectedValue"]:
                s_df = df_g[df_g["strategy"] == strat]
                row[f"{strat}_recovered"] = s_df["recovered_amount"].sum()
                row[f"{strat}_recovery_rate"] = s_df["recovered_boolean"].mean()
                row[f"{strat}_attempts"] = s_df["attempt_count"].mean()
            res.append(row)
        return pd.DataFrame(res)
        
    df_amount = summarize("amount_bucket")
    df_amount.to_csv("data/evaluation/phase8/amount_analysis.csv", index=False)
    
    df_mode = summarize("prediction_mode")
    df_mode.to_csv("data/evaluation/phase8/prediction_mode_analysis.csv", index=False)
    
    df_fail = summarize("failure_type")
    df_fail.to_csv("data/evaluation/phase8/failure_type_analysis.csv", index=False)
    
    # 7. Sequential Analysis
    seq_data = []
    for r in res_smart:
        tr = getattr(r, "_trace", [])
        if len(tr) > 1:
            seq_data.append({"strategy": "SmartHeuristic", "mandate_id": r.mandate_id, "steps": len(tr), "recovered": r.recovered_boolean})
    for r in res_ml_prob:
        tr = getattr(r, "_trace", [])
        if len(tr) > 1:
            seq_data.append({"strategy": "MLProbability", "mandate_id": r.mandate_id, "steps": len(tr), "recovered": r.recovered_boolean})
    for r in res_ml_ev:
        tr = getattr(r, "_trace", [])
        if len(tr) > 1:
            seq_data.append({"strategy": "MLExpectedValue", "mandate_id": r.mandate_id, "steps": len(tr), "recovered": r.recovered_boolean})
    
    pd.DataFrame(seq_data).to_csv("data/evaluation/phase8/sequential_analysis.csv", index=False)
    
    print("Done generating diagnostics data.")

if __name__ == "__main__":
    run_diagnostics()
