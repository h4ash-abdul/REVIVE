import argparse
import pandas as pd
import json
import os
import random
from uuid import uuid4
from datetime import datetime, timezone

from src.configs.models import SimulatorConfig, NoiseLevel, Scenario, PolicyConfig
from src.simulation.generator import DataGenerator
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.decision.policy import DeterministicPolicyEngine
from src.decision.baselines import ImmediateRetryStrategy, FixedScheduleStrategy, SmartHistoricalHeuristicStrategy
from src.evaluation.benchmark import BenchmarkRunner
from src.evaluation.metrics import MetricEngine
from src.domain.models import CohortSnapshot, ExperimentRun

def run_benchmark():
    parser = argparse.ArgumentParser(description="REVIVE: Benchmark Runner")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--mandates", type=int, default=2000)
    args = parser.parse_args()
    
    print(f"Initializing benchmark with seed {args.seed}...")
    
    # 1. Generate Cohort (This generates the starting state)
    sim_config = SimulatorConfig(
        simulator_version="v2.1",
        seed=args.seed,
        noise_level=NoiseLevel.MEDIUM,
        scenario=Scenario.STRONG_TEMPORAL_SIGNAL,
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
    generator.run(start_date, 365, args.customers, 20, int(args.mandates/args.customers))
    
    snapshot = CohortSnapshot(
        snapshot_id=uuid4(),
        experiment_id=uuid4(),
        customers=generator.observable_customers,
        merchants=generator.observable_merchants,
        mandates=list(generator.observable_mandates),
        initial_history=generator.observable_events
    )
    
    # 2. Initialize Engines
    policy_config = PolicyConfig(
        policy_version="v1.0",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    policy_engine = DeterministicPolicyEngine(policy_config)
    
    rng = random.Random(args.seed)
    outcome_engine = OutcomeEngine(rng)
    
    runner = BenchmarkRunner(
        snapshot=snapshot,
        policy=policy_engine,
        outcome_engine=outcome_engine,
        current_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        latent_customers=generator.latent_customers,
        latent_merchants=generator.latent_merchants
    )
    
    # 3. Setup Strategies
    imm_strat = ImmediateRetryStrategy(policy_engine)
    fixed_strat = FixedScheduleStrategy(policy_engine, [24, 48, 72])
    
    smart_strat = SmartHistoricalHeuristicStrategy(
        policy_engine, 
        global_history=snapshot.initial_history,
        min_customer_history=5,
        min_merchant_history=50,
        min_population_history=100
    )
    # Give it the global mandates mapping so it can perform merchant mapping
    smart_strat.global_mandates = snapshot.mandates
    
    strategies = {
        "ImmediateRetryStrategy": imm_strat,
        "FixedScheduleStrategy": fixed_strat,
        "SmartHistoricalHeuristicStrategy": smart_strat
    }
    
    experiment = ExperimentRun(
        experiment_id=snapshot.experiment_id,
        dataset_version="sim-bench-v1",
        simulator_version=sim_config.simulator_version,
        policy_version=policy_config.policy_version,
        strategy_versions={k: v.version for k, v in strategies.items()},
        seed=args.seed,
        cohort_snapshot_id=snapshot.snapshot_id,
        configuration={"policy": policy_config.model_dump(), "simulator": sim_config.model_dump()}
    )
    
    # 4. Run Strategies
    all_results = []
    for name, strat in strategies.items():
        print(f"Running strategy: {name}")
        results = runner.run_strategy(name, strat)
        all_results.extend(results)
        
    # 5. Metrics & Output
    metrics = MetricEngine.calculate_metrics(all_results)
    
    out_dir = f"data/evaluation/benchmark_seed_{args.seed}"
    os.makedirs(out_dir, exist_ok=True)
    
    df = pd.DataFrame([r.model_dump() for r in all_results])
    df.to_parquet(f"{out_dir}/benchmark_results.parquet")
    df.to_csv(f"{out_dir}/benchmark_results.csv", index=False)
    
    summary = {
        "experiment": experiment.model_dump(mode='json'),
        "metrics": metrics
    }
    with open(f"{out_dir}/benchmark_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    print("\n==================================================")
    print(f"BENCHMARK SUMMARY (SEED {args.seed})")
    print("==================================================")
    for strat_name, strat_metrics in metrics.items():
        print(f"\n{strat_name}")
        b = strat_metrics["BUSINESS"]
        e = strat_metrics["EFFICIENCY"]
        print(f"  Recovery Rate: {b['recovery_rate']*100:.1f}%")
        print(f"  Recovered Revenue: ${b['total_recovered_revenue']:.2f} / ${b['total_revenue_at_risk']:.2f}")
        print(f"  Lift vs Immediate: {b['lift_vs_Immediate']*100:.2f}%")
        print(f"  Avg Attempts per Recovered: {e['average_attempts_per_recovered_mandate']:.2f}")

if __name__ == "__main__":
    run_benchmark()
