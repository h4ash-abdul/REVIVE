import random
import uuid
_uuid_rng = random.Random(42)
def deterministic_uuid4():
    return uuid.UUID(int=_uuid_rng.getrandbits(128))
uuid.uuid4 = deterministic_uuid4
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
from src.decision.ml_strategies import MLProbabilityStrategy
from src.decision.scorer import CandidateScoringService
from src.features.builder import PointInTimeFeatureBuilder
from src.models.hierarchical import HierarchicalPredictor
from src.evaluation.benchmark import BenchmarkRunner
from src.evaluation.bootstrap import PairedBootstrapAnalyzer
from src.domain.models import CohortSnapshot

def run_experiment():
    print("==================================================")
    print("CLEAN BENCHMARK: SMART VS ML PROBABILITY")
    print("==================================================")
    
    os.makedirs("data/evaluation/phase8", exist_ok=True)
    
    # 1. Simulator Config
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
    
    # 2. Generate Cohort
    print("Generating simulation cohort...")
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
    
    # 3. Policy & Models
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
    
    strat_smart = SmartHistoricalHeuristicStrategy(policy_engine, snapshot.initial_history)
    strat_smart.global_mandates = snapshot.mandates
    
    strat_ml_prob = MLProbabilityStrategy(policy_engine, scorer)
    strat_ml_prob.global_mandates = snapshot.mandates
    
    # 4. Run Benchmark 
    # Use strategy-independent OutcomeEngine RNG (now fixed inside BenchmarkRunner)
    outcome_engine = OutcomeEngine(random.Random(seed))
    
    print("Running Smart Historical Heuristic...")
    runner_smart = BenchmarkRunner(snapshot, policy_engine, outcome_engine, current_time, latents_c, latents_m)
    runner_smart.base_seed = seed
    res_smart = runner_smart.run_strategy("SmartHeuristic", strat_smart)
    
    print("Running ML Probability Strategy...")
    runner_ml = BenchmarkRunner(snapshot, policy_engine, outcome_engine, current_time, latents_c, latents_m)
    runner_ml.base_seed = seed
    res_ml_prob = runner_ml.run_strategy("MLProbability", strat_ml_prob)
    
    all_results = res_smart + res_ml_prob
    
    # Export raw mandate results
    df = pd.DataFrame([r.model_dump() for r in all_results])
    df.to_csv("data/evaluation/phase8/clean_smart_vs_ml_results.csv", index=False)
    
    df_s = df[df['strategy'] == 'SmartHeuristic'].set_index('mandate_id')
    df_m = df[df['strategy'] == 'MLProbability'].set_index('mandate_id')
    
    # 5. Metrics
    s_rev = df_s['recovered_amount'].sum()
    m_rev = df_m['recovered_amount'].sum()
    
    print(f"Smart Heuristic Revenue: Rs.{s_rev:,.2f}")
    print(f"ML Probability Revenue: Rs.{m_rev:,.2f}")
    print(f"ML vs Smart Diff: Rs.{m_rev - s_rev:,.2f}")
    if s_rev > 0:
        print(f"ML Lift: {((m_rev - s_rev)/s_rev)*100:.2f}%")
        
    df_paired = df_s[['initial_amount', 'recovered_boolean']].join(df_m[['recovered_boolean']], lsuffix='_smart', rsuffix='_ml')
    
    shared_rec = ((df_paired['recovered_boolean_smart'] == True) & (df_paired['recovered_boolean_ml'] == True)).sum()
    shared_fail = ((df_paired['recovered_boolean_smart'] == False) & (df_paired['recovered_boolean_ml'] == False)).sum()
    smart_only = ((df_paired['recovered_boolean_smart'] == True) & (df_paired['recovered_boolean_ml'] == False)).sum()
    ml_only = ((df_paired['recovered_boolean_smart'] == False) & (df_paired['recovered_boolean_ml'] == True)).sum()
    
    df_paired.to_csv("data/evaluation/phase8/clean_smart_vs_ml_paired.csv")
    
    print(f"Shared recoveries: {shared_rec}")
    print(f"Shared failures: {shared_fail}")
    print(f"Smart-only recoveries: {smart_only}")
    print(f"ML-only recoveries: {ml_only}")
    
    # Add amount_at_risk for bootstrap analyzer
    df['amount_at_risk'] = df['initial_amount']
    analyzer = PairedBootstrapAnalyzer(seed=42, replicates=1000)
    boot_stats = analyzer.analyze(df, "SmartHeuristic", "MLProbability")
    
    with open("data/evaluation/phase8/clean_smart_vs_ml_summary.json", "w") as f:
        json.dump({
            "smart_revenue": float(s_rev),
            "ml_revenue": float(m_rev),
            "diff": float(m_rev - s_rev),
            "lift": float((m_rev - s_rev)/s_rev) if s_rev > 0 else 0.0,
            "shared_recoveries": int(shared_rec),
            "shared_failures": int(shared_fail),
            "smart_only_recoveries": int(smart_only),
            "ml_only_recoveries": int(ml_only),
            "bootstrap": boot_stats
        }, f, indent=2)

if __name__ == "__main__":
    run_experiment()
