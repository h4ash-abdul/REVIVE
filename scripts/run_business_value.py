import random
import uuid
_uuid_rng = random.Random(42)
def deterministic_uuid4():
    return uuid.UUID(int=_uuid_rng.getrandbits(128))
uuid.uuid4 = deterministic_uuid4

import argparse
import pandas as pd
import json
import joblib
from datetime import datetime, timezone
import hashlib

from src.configs.models import SimulatorConfig, NoiseLevel, Scenario, PolicyConfig
from src.simulation.generator import DataGenerator
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.decision.policy import DeterministicPolicyEngine
from src.decision.ml_strategies import MLProbabilityStrategy
from src.decision.baselines import SmartHistoricalHeuristicStrategy
from src.decision.scorer import CandidateScoringService
from src.features.builder import PointInTimeFeatureBuilder
from src.models.hierarchical import HierarchicalPredictor
from src.evaluation.benchmark import BenchmarkRunner
from src.evaluation.bootstrap import PairedBootstrapAnalyzer
from src.domain.models import CohortSnapshot, StrategyResult, CandidateAction, PredictionMode
from src.domain.interfaces import RecoveryStrategy
from src.decision.generator import CandidateGenerator as StandardCandidateGenerator

class NoRecoveryStrategy(RecoveryStrategy):
    def __init__(self):
        self.version = "1.0"
    def evaluate(self, mandate, history, current_time, current_obligation=None, candidate_universe=None) -> StrategyResult:
        return StrategyResult(
            strategy_name="NoRecovery",
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=None,
            retry_plan=[],
            selected_time=None,
            candidate_actions=candidate_universe or [],
            explanation="No action taken",
            prediction_mode=PredictionMode.DEFAULT,
            policy_decisions=[],
            stopping_reason="No Recovery Baseline"
        )

def run_business_value():
    print("==================================================")
    print("BUSINESS VALUE EVIDENCE")
    print("==================================================")
    
    sim_config = SimulatorConfig(
        simulator_version="v2.1",
        seed=42,
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
        snapshot_id=uuid.uuid4(),
        experiment_id=uuid.uuid4(),
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
    scorer = CandidateScoringService(feature_builder, predictor)
    
    # We will do Experiment A: No-Recovery Baseline
    # We will use NoRecovery, SmartHeuristic, MLProbability
    strat_no = NoRecoveryStrategy()
    strat_smart = SmartHistoricalHeuristicStrategy(policy_engine, snapshot.initial_history)
    strat_smart.global_mandates = snapshot.mandates
    strat_ml_prob = MLProbabilityStrategy(policy_engine, scorer)
    strat_ml_prob.global_mandates = snapshot.mandates
    
    outcome_engine = OutcomeEngine(random.Random(42))
    
    # Run Baseline
    print("Running No Recovery Baseline...")
    runner_no = BenchmarkRunner(snapshot, policy_engine, outcome_engine, current_time, latents_c, latents_m)
    runner_no.base_seed = 42
    res_no = runner_no.run_strategy("NoRecovery", strat_no)
    
    # Experiment A Analysis
    df_no = pd.DataFrame([r.model_dump() for r in res_no])
    df_no['amount_at_risk'] = df_no['initial_amount']
    df_no.to_csv("data/evaluation/business_value/no_recovery_comparison.csv", index=False)
    
    rev_no = df_no['recovered_amount'].sum()
    res_smart = runner_no.run_strategy("SmartHeuristic", strat_smart)
    df_smart = pd.DataFrame([r.model_dump() for r in res_smart])
    df_smart['amount_at_risk'] = df_smart['initial_amount']
    df_smart.to_csv("data/evaluation/business_value/smart_heuristic_comparison.csv", index=False)
    rev_smart = df_smart['recovered_amount'].sum()
    print(f"Smart Heuristic Revenue: Rs.{rev_smart:,.2f}")
    
    df_exp_a = pd.concat([df_no, df_smart])
    analyzer_a = PairedBootstrapAnalyzer(seed=42, replicates=1000)
    stats_a = analyzer_a.analyze(df_exp_a, "NoRecovery", "SmartHeuristic")

    rate_no = df_no['recovered_boolean'].mean()
    print(f"No Recovery Revenue: Rs.{rev_no:,.2f}")
    
    # ----------------------------------------------------
    # Experiment B: Cross-Mandate Economic Prioritization
    # ----------------------------------------------------
    print("Running Experiment B: Cross-Mandate Allocation...")
    # First, collect the top action and probability for each mandate using MLProbability
    candidate_generator = StandardCandidateGenerator(days_ahead=30, hours_of_day=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    failed_mandates = []
    for m in snapshot.mandates:
        history = [e for e in snapshot.initial_history if e.mandate_id == m.mandate_id]
        if not any(e.status == 'success' for e in history): # AttemptStatus.SUCCESS
            failed_mandates.append(m)
    print(f"Total failed mandates for capacity allocation: {len(failed_mandates)}")
    
    mandate_data = []
    
    for mandate in failed_mandates:
        history = [e for e in snapshot.initial_history if e.mandate_id == mandate.mandate_id]
        if history:
            last_attempt = sorted(history, key=lambda e: e.timestamp)[-1]
            if last_attempt.timestamp > current_time:
                eval_time = last_attempt.timestamp
            else:
                eval_time = current_time
        else:
            eval_time = current_time
            
        universe = candidate_generator.generate(mandate, eval_time)
        decisions = policy_engine.pre_filter(universe, mandate, history, None)
        valid_candidates = [c for c, d in zip(universe, decisions) if d.is_allowed]
        if not valid_candidates:
            continue
        res = strat_ml_prob.evaluate(mandate, history, eval_time, None, valid_candidates)
        
        if res.selected_action:
            preds = scorer.score_candidates([res.selected_action], mandate, history, snapshot.mandates, current_time)
            prob = preds[res.selected_action.candidate_id].probability
            
            # Create a localized runner for this single execution to ensure exact same OutcomeEngine logic
            runner_single = BenchmarkRunner(snapshot, policy_engine, outcome_engine, current_time, latents_c, latents_m)
            runner_single.base_seed = 42
            
            # We can't just pass the strategy because we only want to run it if selected.
            # Instead of modifying BenchmarkRunner, we can mock the strategy to just return the selected action!
            class MockSingleActionStrategy(RecoveryStrategy):
                def __init__(self, res):
                    self.res = res
                    self.version = "1.0"
                def evaluate(self, mandate, history, current_time, current_obligation=None, candidate_universe=None):
                    if not candidate_universe:
                        return self.res
                    target = self.res.selected_action
                    if not target:
                        return self.res
                    matched = next((c for c in candidate_universe if c.scheduled_time == target.scheduled_time and c.amount == target.amount), None)
                    if matched:
                        from src.domain.models import StrategyResult, PredictionMode
                        return StrategyResult(
                            strategy_name="Mock", strategy_version="1.0", mandate_id=mandate.mandate_id,
                            selected_action=matched, retry_plan=[matched], selected_time=matched.scheduled_time, candidate_actions=candidate_universe,
                            explanation="Matched", prediction_mode=PredictionMode.DEFAULT, policy_decisions=[], stopping_reason=None
                        )
                    print(f"FAILED TO MATCH: target={target.scheduled_time} {target.amount}")
                    print(f"UNIVERSE LENGTH: {len(candidate_universe)}")
                    print(f"FIRST 5: {[ (c.scheduled_time, c.amount) for c in candidate_universe[:5] ]}")
                    return self.res
                    target = self.res.selected_action
                    matched = next((c for c in candidate_universe if c.scheduled_time == target.scheduled_time and c.amount == target.amount), None)
                    if matched:
                        from src.domain.models import StrategyResult, PredictionMode
                        return StrategyResult(
                            strategy_name="Mock", strategy_version="1.0", mandate_id=mandate.mandate_id,
                            selected_action=matched, retry_plan=[matched], selected_time=matched.scheduled_time, candidate_actions=candidate_universe,
                            explanation="Matched", prediction_mode=PredictionMode.DEFAULT, policy_decisions=[], stopping_reason=None
                        )
                    return self.res

            
            mandate_data.append({
                "mandate": mandate,
                "mandate_id": mandate.mandate_id,
                "amount": mandate.amount,
                "probability": prob,
                "expected_value": prob * mandate.amount,
                "mock_strategy": MockSingleActionStrategy(res)
            })
            
    # Sort by Probability (Strategy P)
    mandate_data_p = sorted(mandate_data, key=lambda x: x["probability"], reverse=True)
    
    # Sort by EV (Strategy EV)
    mandate_data_ev = sorted(mandate_data, key=lambda x: x["expected_value"], reverse=True)
    
    CAPACITY = 100
    selected_p = mandate_data_p[:CAPACITY]
    selected_ev = mandate_data_ev[:CAPACITY]
    
    def evaluate_batch(selected_batch, strategy_name):
        results = []
        selected_ids = {item["mandate_id"] for item in selected_batch}
        for item in mandate_data:
            snapshot_single = snapshot.model_copy(update={'mandates': [item["mandate"]]})
            runner_single = BenchmarkRunner(snapshot_single, policy_engine, outcome_engine, current_time, latents_c, latents_m)
            runner_single.base_seed = 42
            
            if item["mandate_id"] in selected_ids:
                r = runner_single.run_strategy(strategy_name, strat_ml_prob)[0]
            else:
                r = runner_single.run_strategy(strategy_name, strat_no)[0]
            results.append(r)
        return results

    res_p = evaluate_batch(selected_p, "P_Prioritization")
    res_ev = evaluate_batch(selected_ev, "EV_Prioritization")
    
    df_p = pd.DataFrame([r.model_dump() for r in res_p])
    df_ev = pd.DataFrame([r.model_dump() for r in res_ev])
    
    df_cross = pd.concat([df_p, df_ev])
    df_cross['amount_at_risk'] = df_cross['initial_amount']
    df_cross.to_csv("data/evaluation/business_value/cross_mandate_ev.csv", index=False)
    
    rev_p = df_p['recovered_amount'].sum()
    rev_ev = df_ev['recovered_amount'].sum()
    
    print(f"P-based Revenue: Rs.{rev_p:,.2f}")
    print(f"EV-based Revenue: Rs.{rev_ev:,.2f}")
    
    # Bootstrap Experiment B
    analyzer_b = PairedBootstrapAnalyzer(seed=42, replicates=1000)
    
    stats_b = analyzer_b.analyze(df_cross, "P_Prioritization", "EV_Prioritization")
    
    with open("data/evaluation/business_value/business_value_summary.json", "w") as f:
        json.dump({
            "no_recovery_revenue": float(rev_no),
            "no_recovery_rate": float(rate_no),
            "p_based_revenue": float(rev_p),
            "ev_based_revenue": float(rev_ev),
            "ev_vs_p_diff": float(rev_ev - rev_p),
            "bootstrap_ev_vs_p": stats_b,
        "bootstrap_smart_vs_no": stats_a
        }, f, indent=2)

if __name__ == '__main__':
    run_business_value()

