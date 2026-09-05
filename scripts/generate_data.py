import argparse
import pandas as pd
from datetime import datetime, timezone
import json
import os
import uuid

from src.configs.models import SimulatorConfig, NoiseLevel, Scenario
from src.simulation.generator import DataGenerator

def run_cli():
    parser = argparse.ArgumentParser(description="REVIVE: Synthetic Data Generator")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--merchants", type=int, default=20, help="Number of merchants")
    parser.add_argument("--days", type=int, default=365, help="Simulation duration in days")
    parser.add_argument("--mandates", type=int, default=2, help="Mandates per customer")
    parser.add_argument("--noise", type=str, choices=["low", "medium", "high"], default="medium", help="Global noise level")
    parser.add_argument("--drift", type=float, default=0.05, help="Behavioral drift probability")
    
    args = parser.parse_args()
    
    print(f"Initializing REVIVE simulation with seed {args.seed}...")
    
    config = SimulatorConfig(
        simulator_version="v2.1",
        seed=args.seed,
        noise_level=NoiseLevel(args.noise),
        scenario=Scenario.STRONG_TEMPORAL_SIGNAL,
        customer_archetypes_distribution={
            "salary_cycle_regular": 0.4,
            "irregular_gig": 0.2,
            "chronic_low_balance": 0.15,
            "thin_history": 0.15,
            "technical_decline_prone": 0.1
        },
        behavioral_drift_rate=args.drift,
        enable_technical_declines=True
    )
    
    generator = DataGenerator(config)
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    generator.run(start_date, args.days, args.customers, args.merchants, args.mandates)
    
    events_df = pd.DataFrame([e.model_dump() for e in generator.observable_events])
    mandates_df = pd.DataFrame([m.model_dump() for m in generator.observable_mandates])
    
    dataset_version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    manifest = {
        "dataset_version": dataset_version,
        "simulator_version": config.simulator_version,
        "seed": config.seed,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_count": len(generator.observable_customers),
        "merchant_count": len(generator.observable_merchants),
        "mandate_count": len(generator.observable_mandates),
        "event_count": len(events_df),
        "archetype_distribution": config.customer_archetypes_distribution,
        "noise_configuration": config.noise_level.value,
        "drift_configuration": config.behavioral_drift_rate,
        "scenario_configuration": config.scenario.value
    }
    
    print("\n==================================================")
    print("REVIVE DATA QUALITY REPORT")
    print("==================================================")
    print(f"Dataset Version: {dataset_version}")
    print(f"Total Customers: {manifest['customer_count']}")
    print(f"Total Merchants: {manifest['merchant_count']}")
    print(f"Total Mandates: {manifest['mandate_count']}")
    print(f"Total Payment Events: {manifest['event_count']}")
    
    if len(events_df) > 0:
        success_rate = (events_df['status'] == 'success').mean() * 100
        print(f"Overall Success Rate: {success_rate:.1f}%")
        
        failures = events_df[events_df['status'] != 'success']
        print("\nFailure Distribution (Raw Network Codes):")
        print(failures['network_return_code'].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")
        
        print("\nAmount Distribution:")
        print(events_df['amount'].describe().round(2))
        
        print("\nMandate Lifecycle Distribution:")
        print(mandates_df['status'].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")
        
        print("\nEvents per Mandate (Average):", round(len(events_df) / len(mandates_df), 2))
    
    print("\n--------------------------------------------------")
    print("SIMULATOR DIAGNOSTICS (Latent State Only - DO NOT USE FOR ML)")
    print("--------------------------------------------------")
    latent_df = pd.DataFrame([l.model_dump() for l in generator.latent_customers.values()])
    print("Customer Archetypes Generated:")
    print(latent_df['archetype'].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")
    
    obs_dir = "data/generated/observable"
    lat_dir = "data/generated/latent"
    os.makedirs(obs_dir, exist_ok=True)
    os.makedirs(lat_dir, exist_ok=True)
    
    events_df.to_parquet(f"{obs_dir}/payment_events_{dataset_version}.parquet")
    with open(f"data/generated/manifest_{dataset_version}.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"\nManifest and datasets saved.")

if __name__ == "__main__":
    run_cli()
