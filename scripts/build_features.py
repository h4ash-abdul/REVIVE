import argparse
import json
import os
import pandas as pd
from datetime import datetime, timezone
from uuid import uuid4

from src.configs.models import SimulatorConfig, NoiseLevel, Scenario
from src.simulation.generator import DataGenerator
from src.domain.models import CohortSnapshot
from src.features.dataset import TrainingDatasetBuilder

def build_features():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=1000)
    args = parser.parse_args()
    
    # 1. Generate standard observable dataset (like Phase 2)
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
        },
        behavioral_drift_rate=0.05,
        enable_technical_declines=True
    )
    generator = DataGenerator(sim_config)
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    generator.run(start_date, 365, args.customers, 20, 2)
    
    snapshot = CohortSnapshot(
        snapshot_id=uuid4(),
        experiment_id=uuid4(),
        customers=generator.observable_customers,
        merchants=generator.observable_merchants,
        mandates=list(generator.observable_mandates),
        initial_history=generator.observable_events
    )
    
    # 2. Build Features
    builder = TrainingDatasetBuilder()
    features, metadata = builder.build_from_snapshot(snapshot)
    
    # 3. Output
    out_dir = "data/features"
    os.makedirs(out_dir, exist_ok=True)
    
    df = pd.DataFrame([f.model_dump() for f in features])
    df.to_parquet(f"{out_dir}/training_features.parquet")
    
    with open(f"{out_dir}/feature_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("\n==================================================")
    print("FEATURE ENGINEERING REPORT")
    print("==================================================")
    print(f"Total Features per Row: {len(df.columns)}")
    print(f"Total Training Examples: {metadata.get('total_examples', 0)}")
    print(f"Train/Val/Test Split: {metadata.get('train_size', 0)} / {metadata.get('validation_size', 0)} / {metadata.get('test_size', 0)}")
    print(f"Train End Timestamp: {metadata.get('train_end_timestamp', 'N/A')}")
    print(f"Val End Timestamp: {metadata.get('validation_end_timestamp', 'N/A')}")
    
    # Find a mandate with multiple examples
    if not df.empty:
        counts = df['mandate_id'].value_counts()
        multi_mandates = counts[counts > 1].index
        if len(multi_mandates) > 0:
            target_m = multi_mandates[0]
            example_rows = df[df['mandate_id'] == target_m].head(2)
            
            print("\n--------------------------------------------------")
            print(f"EXAMPLE ROWS (Mandate {target_m})")
            print("--------------------------------------------------")
            # Show candidate dependent features
            cols_to_show = ['cutoff_timestamp', 'candidate_hour', 'time_until_candidate_hours', 'hist_payment_count', 'hist_success_count', 'target_success']
            print(example_rows[cols_to_show].to_string())
            
if __name__ == "__main__":
    build_features()
