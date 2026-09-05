import argparse
import pandas as pd
import json
import joblib
import uuid
from datetime import datetime, timezone
from src.models.evaluation import ModelEvaluator
from src.models.prediction import Prediction

def evaluate():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-version", type=str, default="v1.1")
    args = parser.parse_args()
    
    # 1. Load Artifacts
    with open(f"models/artifacts/model_manifest_{args.model_version}.json", "r") as f:
        manifest_data = json.load(f)
        
    pipeline = joblib.load(manifest_data["artifact_path"])
    
    # 2. Load Data
    df = pd.read_parquet("data/features/training_features.parquet")
    with open("data/features/feature_metadata.json", "r") as f:
        meta = json.load(f)
        
    train_end = pd.to_datetime(meta["train_end_timestamp"])
    val_end = pd.to_datetime(meta["validation_end_timestamp"])
    
    df['cutoff_timestamp'] = pd.to_datetime(df['cutoff_timestamp'])
    
    val_df = df[(df['cutoff_timestamp'] > train_end) & (df['cutoff_timestamp'] <= val_end)].copy()
    test_df = df[df['cutoff_timestamp'] > val_end].copy()
    
    # 3. Generate Predictions
    results_metrics = {}
    
    for split_name, split_df in [("validation", val_df), ("test", test_df)]:
        if split_df.empty:
            continue
            
        print(f"Evaluating {split_name} split ({len(split_df)} examples)...")
        y_true = split_df['target_success']
        X = split_df.drop(columns=pipeline.forbidden_columns, errors='ignore')
        
        y_prob = pipeline.predict_proba(X)
        
        # Calculate Metrics
        metrics = ModelEvaluator.evaluate(y_true, y_prob)
        results_metrics[split_name] = metrics
        
        # Calculate and Plot Calibration (only test is strictly needed for report, but generating for both)
        calib_df = ModelEvaluator.calculate_calibration(y_true, y_prob)
        calib_df.to_csv(f"models/reports/calibration_{split_name}.csv", index=False)
        ModelEvaluator.plot_calibration(calib_df, f"models/reports/calibration_{split_name}.png")
        
        if split_name == "test":
            # Generate predictions output for test
            preds = []
            for i, idx in enumerate(split_df.index):
                p = Prediction(
                    prediction_id=uuid.uuid4(),
                    candidate_id=split_df.loc[idx, 'candidate_id'],
                    probability=float(y_prob.iloc[i]),
                    model_version=args.model_version,
                    feature_version=manifest_data["feature_version"],
                    prediction_timestamp=datetime.now(timezone.utc),
                    prediction_mode=split_df.loc[idx, 'prediction_mode']
                )
                preds.append(p.model_dump())
            
            pd.DataFrame(preds).to_parquet("models/artifacts/predictions.parquet")
            
    # 4. Extract Coefficients
    coefs = pipeline.get_coefficients()
    coef_df = pd.DataFrame(list(coefs.items()), columns=["Feature", "Coefficient"])
    coef_df["Magnitude"] = coef_df["Coefficient"].abs()
    coef_df = coef_df.sort_values(by="Magnitude", ascending=False)
    coef_df.to_csv("models/reports/coefficients.csv", index=False)
    
    # 5. Update Manifest
    manifest_data["metrics"] = results_metrics
    with open(f"models/artifacts/model_manifest_{args.model_version}.json", "w") as f:
        json.dump(manifest_data, f, indent=2)
        
    # 6. Sanity Review Print
    print("\n==================================================")
    print("MODEL EVALUATION SANITY REVIEW")
    print("==================================================")
    
    print(f"Validation Examples: {len(val_df)}")
    if not val_df.empty:
        val_pos = val_df['target_success'].sum()
        print(f"  Pos/Neg Balance: {val_pos} / {len(val_df) - val_pos} ({val_pos/len(val_df)*100:.1f}%)")
        print(f"  ROC-AUC: {results_metrics['validation']['roc_auc']:.4f}")
        print(f"  PR-AUC: {results_metrics['validation']['pr_auc']:.4f}")
        print(f"  Brier Score: {results_metrics['validation']['brier_score']:.4f}")
        print(f"  Log Loss: {results_metrics['validation']['log_loss']:.4f}")
        
    print(f"\nTest Examples: {len(test_df)}")
    if not test_df.empty:
        test_pos = test_df['target_success'].sum()
        print(f"  Pos/Neg Balance: {test_pos} / {len(test_df) - test_pos} ({test_pos/len(test_df)*100:.1f}%)")
        print(f"  ROC-AUC: {results_metrics['test']['roc_auc']:.4f}")
        print(f"  PR-AUC: {results_metrics['test']['pr_auc']:.4f}")
        print(f"  Brier Score: {results_metrics['test']['brier_score']:.4f}")
        print(f"  Log Loss: {results_metrics['test']['log_loss']:.4f}")

if __name__ == "__main__":
    evaluate()
