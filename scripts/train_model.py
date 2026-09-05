import argparse
import pandas as pd
import json
import joblib
from datetime import datetime, timezone
from src.models.pipeline import RecoveryPredictionPipeline
from src.models.registry.manifest import ModelManifest

def train():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-version", type=str, default="v1.1")
    args = parser.parse_args()
    
    # 1. Load Data
    print("Loading feature dataset...")
    df = pd.read_parquet("data/features/training_features.parquet")
    with open("data/features/feature_metadata.json", "r") as f:
        meta = json.load(f)
        
    train_end = pd.to_datetime(meta["train_end_timestamp"])
    val_end = pd.to_datetime(meta["validation_end_timestamp"])
    
    # Ensure cutoff_timestamp is datetime timezone aware
    df['cutoff_timestamp'] = pd.to_datetime(df['cutoff_timestamp'])
    
    # 2. Strict Temporal Split
    train_df = df[df['cutoff_timestamp'] <= train_end].copy()
    
    print(f"Training on {len(train_df)} examples...")
    
    # 3. Target and Features
    y_train = train_df['target_success']
    pipeline = RecoveryPredictionPipeline(random_state=args.seed)
    X_train = train_df.drop(columns=pipeline.forbidden_columns, errors='ignore')
    
    try:
        pipeline.fit(X_train, y_train)
    except ValueError as e:
        print(f"FAILED: Leakage check triggered: {e}")
        return
        
    # 5. Save Artifacts
    artifact_path = f"models/artifacts/model_{args.model_version}.pkl"
    joblib.dump(pipeline, artifact_path)
    
    # 6. Save Manifest
    manifest = ModelManifest(
        model_version=args.model_version,
        model_type="LogisticRegression",
        feature_version=meta["feature_version"],
        dataset_version="auto", # Ideally passed in, but placeholder for now
        training_window={"start": str(train_df['cutoff_timestamp'].min()), "end": str(train_end)},
        validation_window={"start": str(train_end), "end": str(val_end)},
        test_window={"start": str(val_end), "end": "latest"},
        parameters={"random_state": args.seed, "max_iter": 1000, "class_weight": "balanced"},
        seed=args.seed,
        metrics={}, # Will be populated by evaluate_model.py
        artifact_path=artifact_path,
        training_timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    with open(f"models/artifacts/model_manifest_{args.model_version}.json", "w") as f:
        json.dump(manifest.model_dump(), f, indent=2)
        
    print(f"Successfully trained {args.model_version}. Artifacts saved to models/artifacts/.")

if __name__ == "__main__":
    train()
