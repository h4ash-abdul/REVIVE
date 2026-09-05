import argparse
import pandas as pd
import json
import joblib
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from src.models.config import HierarchicalConfig
from src.models.hierarchical import HierarchicalPredictor

def evaluate():
    print("Loading test dataset and calibrated model...")
    with open("models/artifacts/model_manifest.json", "r") as f:
        manifest = json.load(f)
        
    calibrated_model = joblib.load(manifest["artifact_path"])
    
    df = pd.read_parquet("data/features/training_features.parquet")
    with open("data/features/feature_metadata.json", "r") as f:
        meta = json.load(f)
        
    val_end = pd.to_datetime(meta["validation_end_timestamp"])
    df['cutoff_timestamp'] = pd.to_datetime(df['cutoff_timestamp'])
    
    # Strictly evaluate on held-out test
    test_df = df[df['cutoff_timestamp'] > val_end].copy().reset_index(drop=True)
    y_test = test_df['target_success'].values
    
    # Configure and Initialize Predictor
    config = HierarchicalConfig(
        min_customer_history=3,
        min_merchant_history=50
    )
    predictor = HierarchicalPredictor(base_model=calibrated_model, config=config)
    
    print("Generating hierarchical predictions...")
    preds = predictor.predict(test_df)
    
    # Evaluate
    # Segments: 
    # - 0 events
    # - 1-2 events
    # - customer mode (>= 3)
    # - merchant fallback
    # - population fallback
    
    test_df['pred_prob'] = [p.probability for p in preds]
    test_df['pred_mode'] = [p.prediction_mode for p in preds]
    test_df['y_true'] = y_test
    
    def get_segment(row):
        c = row['hist_payment_count']
        if row['pred_mode'] == 'customer':
            return '3+ Events (Customer Mode)'
        elif row['pred_mode'] == 'merchant':
            if c == 0:
                return '0 Events (Merchant Fallback)'
            else:
                return '1-2 Events (Merchant Fallback)'
        else:
            if c == 0:
                return '0 Events (Population Fallback)'
            else:
                return '1-2 Events (Population Fallback)'
                
    test_df['segment'] = test_df.apply(get_segment, axis=1)
    
    results = []
    
    for segment in test_df['segment'].unique():
        sub = test_df[test_df['segment'] == segment]
        if len(sub) == 0:
            continue
            
        y_true_sub = sub['y_true']
        y_prob_sub = sub['pred_prob']
        
        brier = brier_score_loss(y_true_sub, y_prob_sub)
        ll = log_loss(y_true_sub, y_prob_sub, labels=[False, True])
        
        if len(y_true_sub.unique()) > 1:
            roc = roc_auc_score(y_true_sub, y_prob_sub)
        else:
            roc = float('nan')
            
        results.append({
            "segment": segment,
            "count": len(sub),
            "success_rate": y_true_sub.mean(),
            "brier_score": brier,
            "log_loss": ll,
            "roc_auc": roc
        })
        
    res_df = pd.DataFrame(results).sort_values(by="success_rate", ascending=False)
    
    print("\n==================================================")
    print("COLD-START EVALUATION REPORT")
    print("==================================================")
    print(res_df.to_string(index=False))
    
    res_df.to_csv("models/reports/cold_start_report.csv", index=False)
    
    with open("models/reports/cold_start_report.json", "w") as f:
        json.dump(res_df.to_dict(orient="records"), f, indent=2)
        
    with open("models/reports/cold_start_report.md", "w") as f:
        f.write("# Cold-Start Hierarchical Prediction Performance\n\n")
        f.write("This report details prediction performance across different levels of historical depth and prediction modes.\n\n")
        f.write(res_df.to_markdown(index=False))

if __name__ == "__main__":
    evaluate()
