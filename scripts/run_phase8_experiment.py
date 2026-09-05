import argparse
import pandas as pd
import json
import os
import joblib
import random
from uuid import uuid4
from datetime import datetime, timezone

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
from src.evaluation.benchmark import BenchmarkRunner
from src.evaluation.metrics import MetricEngine
from src.evaluation.bootstrap import PairedBootstrapAnalyzer
from src.domain.models import CohortSnapshot

def run_experiment():
    print("==================================================")
    print("PHASE 8: PRE-REGISTERED EXPERIMENT (REVIVE VS SMART)")
    print("==================================================")
    
    os.makedirs("data/evaluation/phase8", exist_ok=True)
    
    # 1. Setup Data & Simulator
    seed = 42
    sim_config = SimulatorConfig(
        simulator_version="v2.1",
        seed=seed,
        num_customers=1000,
        num_merchants=50,
        num_mandates=2000,
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
    
    # 2. Setup Copilot Environment
    policy_config = PolicyConfig(
        policy_version="v1.0",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    policy_engine = DeterministicPolicyEngine(policy_config)
    
    print("Loading calibrated ML model (v1.1)...")
    with open("models/artifacts/model_manifest_v1.1.json", "r") as f:
        manifest = json.load(f)
    pipeline = joblib.load(manifest["artifact_path"])
    predictor = HierarchicalPredictor(base_model=pipeline)
    feature_builder = PointInTimeFeatureBuilder()
    classifier = RuleBasedFailureClassifier()
    scorer = CandidateScoringService(feature_builder, predictor)
    
    # 3. Initialize Strategies
    strat_smart = SmartHistoricalHeuristicStrategy(
        policy=policy_engine, 
        global_history=snapshot.initial_history
    )
    # Inject global mandates for merchant/population lookups
    strat_smart.global_mandates = snapshot.mandates
    
    strat_ml_prob = MLProbabilityStrategy(policy_engine, scorer)
    strat_ml_prob.global_mandates = snapshot.mandates
    strat_ml_ev = MLExpectedValueStrategy(policy_engine, scorer, action_cost=0.0)
    strat_ml_ev.global_mandates = snapshot.mandates
    
    # 4. Run Benchmark 
    outcome_engine = OutcomeEngine(random.Random(seed))
    runner = BenchmarkRunner(snapshot, policy_engine, outcome_engine, current_time, latents_c, latents_m)
    
    print("Running Smart Historical Heuristic...")
    res_smart = runner.run_strategy("SmartHeuristic", strat_smart)
    
    print("Running ML Probability Strategy...")
    res_ml_prob = runner.run_strategy("MLProbability", strat_ml_prob)
    
    print("Running ML Expected Value Strategy...")
    res_ml_ev = runner.run_strategy("MLExpectedValue", strat_ml_ev)
    
    # 5. Extract Results
    all_results = res_smart + res_ml_prob + res_ml_ev
    df_results = pd.DataFrame([r.model_dump() for r in all_results])
    # amount_at_risk is initial_amount in MandateResult
    df_results['amount_at_risk'] = df_results['initial_amount']
    df_results['budget_exhausted'] = df_results['retry_budget_exhausted']
    
    df_results.to_parquet("data/evaluation/phase8/final_mandate_results.parquet")
    
    # 6. Bootstrap Analysis
    print("Running Bootstrap Analysis...")
    analyzer = PairedBootstrapAnalyzer(seed=42, replicates=1000)
    
    # Primary: EV vs Smart
    boot_primary = analyzer.analyze(df_results, strat_a="SmartHeuristic", strat_b="MLExpectedValue")
    
    # Secondary: EV vs Prob
    boot_secondary = analyzer.analyze(df_results, strat_a="MLProbability", strat_b="MLExpectedValue")
    
    with open("data/evaluation/phase8/bootstrap_summary.json", "w") as f:
        json.dump({
            "primary_comparison": boot_primary,
            "ev_ablation": boot_secondary
        }, f, indent=2)
        
    # Strategy Summary
    summary_list = []
    for s_name in ["SmartHeuristic", "MLProbability", "MLExpectedValue"]:
        df_s = df_results[df_results["strategy"] == s_name]
        total_rec = df_s["recovered_amount"].sum()
        total_risk = df_s["amount_at_risk"].sum()
        attempts = df_s["attempt_count"].sum()
        summary_list.append({
            "strategy": s_name,
            "total_revenue_at_risk": total_risk,
            "recovered_revenue": total_rec,
            "recovery_rate": df_s["recovered_boolean"].mean(),
            "average_attempts": attempts / len(df_s) if len(df_s) > 0 else 0,
            "budget_exhausted_rate": df_s["budget_exhausted"].mean(),
            "policy_violations": df_s["policy_violation_count"].sum()
        })
        
    df_summary = pd.DataFrame(summary_list)
    df_summary.to_csv("data/evaluation/phase8/strategy_summary.csv", index=False)
    
    # Classification
    p05 = boot_primary["bootstrap"]["p05_difference"]
    lift = boot_primary["observed"]["percentage_lift"]
    
    if p05 > 0 and lift > 0:
        classification = "CASE A: REVIVE materially and robustly outperforms Smart."
    elif lift > 0:
        classification = "CASE B: REVIVE wins but the improvement is modest or the bootstrap interval crosses zero."
    else:
        classification = "CASE C: REVIVE does not outperform Smart."
        
    # Write Final Report
    report = f"""# Phase 8 Final Report: REVIVE Decision-Policy Experiment

## 1. Methodology
- **Cohort Size**: {1000} customers, {2000} mandates
- **Seed**: {sim_config.seed} (Simulator), 42 (Bootstrap)
- **Candidate Universe**: 30-day lookahead, strictly identical across strategies.
- **Strategies**: Smart Historical Heuristic, ML Probability, ML Expected Value (cost=₹0.0).
- **Metric**: Total Recovered Revenue (INR/₹)

## 2. Overall Strategy Performance

| Strategy | Revenue at Risk | Recovered Revenue | Recovery Rate | Avg Attempts | Budget Exhausted Rate | Policy Violations |
|----------|-----------------|-------------------|---------------|--------------|-----------------------|-------------------|
"""
    for s in summary_list:
        report += f"| {s['strategy']} | ₹{s['total_revenue_at_risk']:,.2f} | ₹{s['recovered_revenue']:,.2f} | {s['recovery_rate']:.1%} | {s['average_attempts']:.2f} | {s['budget_exhausted_rate']:.1%} | {s['policy_violations']} |\n"

    report += f"""
## 3. Primary Comparison: MLExpectedValue vs SmartHeuristic
- **Observed Revenue Difference**: ₹{boot_primary['observed']['revenue_difference']:,.2f}
- **Observed Percentage Lift**: {boot_primary['observed']['percentage_lift']:.2%}
- **Median Bootstrap Difference**: ₹{boot_primary['bootstrap']['median_difference']:,.2f}
- **90% Confidence Interval**: [₹{boot_primary['bootstrap']['p05_difference']:,.2f}, ₹{boot_primary['bootstrap']['p95_difference']:,.2f}]
- **Probability Challenger Wins**: {boot_primary['bootstrap']['prob_challenger_wins']:.1%}

### Recovery Rate Paired Counts
- **Shared Recoveries**: {boot_primary['recovery_paired_counts']['shared_recoveries']}
- **Shared Failures**: {boot_primary['recovery_paired_counts']['shared_failures']}
- **Smart-only Recoveries**: {boot_primary['recovery_paired_counts']['SmartHeuristic_only_recoveries']}
- **REVIVE-only Recoveries**: {boot_primary['recovery_paired_counts']['MLExpectedValue_only_recoveries']}
- **Net Recovery Rate Difference**: {boot_primary['observed']['recovery_rate_difference']:.2%}

## 4. EV Ablation: MLExpectedValue vs MLProbability
- **Observed Revenue Difference**: ₹{boot_secondary['observed']['revenue_difference']:,.2f}
- **Observed Percentage Lift**: {boot_secondary['observed']['percentage_lift']:.2%}
- **Median Bootstrap Difference**: ₹{boot_secondary['bootstrap']['median_difference']:,.2f}
- **90% Confidence Interval**: [₹{boot_secondary['bootstrap']['p05_difference']:,.2f}, ₹{boot_secondary['bootstrap']['p95_difference']:,.2f}]

## 5. Result Classification
**{classification}**

## 6. Interpretation
The experiment was conducted with strict adherence to candidate universe identicality and outcome independence. 
"""
    with open("data/evaluation/phase8/phase8_final_report.md", "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nExperiment complete. Result: {classification}")
    print("Report written to data/evaluation/phase8/phase8_final_report.md")

if __name__ == "__main__":
    run_experiment()
