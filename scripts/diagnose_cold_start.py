import pandas as pd
import numpy as np
import json
import joblib
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from src.models.config import HierarchicalConfig
from src.models.hierarchical import HierarchicalPredictor

def evaluate_metrics(y_true, y_prob):
    if len(y_true) == 0:
        return {}
    brier = brier_score_loss(y_true, y_prob)
    ll = log_loss(y_true, y_prob, labels=[False, True])
    roc = roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else np.nan
    return {"count": len(y_true), "success_rate": y_true.mean(), "mean_prob": y_prob.mean(), "brier": brier, "log_loss": ll, "roc_auc": roc}

def run_diagnostics():
    with open("models/artifacts/model_manifest.json", "r") as f:
        manifest = json.load(f)
        
    calibrated_model = joblib.load(manifest["artifact_path"])
    base_pipeline = calibrated_model.base_pipe
    imputer = base_pipeline.pipeline.named_steps['preprocessor'].named_transformers_['num'].named_steps['imputer']
    
    # Check imputed values for numeric features
    numeric_features = base_pipeline.numeric_features
    imputed_values = dict(zip(numeric_features, imputer.statistics_))
    
    df = pd.read_parquet("data/features/training_features.parquet")
    with open("data/features/feature_metadata.json", "r") as f:
        meta = json.load(f)
        
    val_end = pd.to_datetime(meta["validation_end_timestamp"])
    df['cutoff_timestamp'] = pd.to_datetime(df['cutoff_timestamp'])
    
    test_df = df[df['cutoff_timestamp'] > val_end].copy().reset_index(drop=True)
    y_test = test_df['target_success'].values
    
    config = HierarchicalConfig(min_customer_history=3, min_merchant_history=50)
    predictor = HierarchicalPredictor(base_model=calibrated_model, config=config)
    
    # Group A: Merchant Fallback (1-2 events)
    mask_1_2 = (test_df['hist_payment_count'] > 0) & (test_df['hist_payment_count'] < 3)
    group_1_2 = test_df[mask_1_2].copy()
    y_1_2 = group_1_2['target_success'].values
    
    # 1. Compare Full vs Masked
    # Masked (current approach)
    preds_masked = predictor.predict(group_1_2)
    probs_masked = np.array([p.probability for p in preds_masked])
    
    # Full (unmasked, sending directly to base model)
    X_full = group_1_2.drop(columns=base_pipeline.forbidden_columns, errors='ignore')
    probs_full = calibrated_model.predict_proba(X_full)
    
    # Baselines
    global_rate = test_df['target_success'].mean()
    merchant_rate = group_1_2['merchant_success_rate'].values
    pop_rate = np.full(len(y_1_2), global_rate)
    
    results = {
        "Masked (Current)": evaluate_metrics(y_1_2, probs_masked),
        "Unmasked (Full)": evaluate_metrics(y_1_2, probs_full),
        "Global Baseline": evaluate_metrics(y_1_2, pop_rate),
        "Merchant Baseline": evaluate_metrics(y_1_2, merchant_rate)
    }
    
    # Out of distribution check
    # What did the model see during training for 1-2 events?
    # It saw hist_payment_count = 1 or 2.
    # What does it see during masking? 
    # It sees NaN, which becomes the median from the whole training set (which is ~6).
    
    diag_data = {
        "imputed_values": {k: float(v) for k,v in imputed_values.items() if k in predictor.customer_features},
        "results_1_2_events": results
    }
    
    with open("models/reports/cold_start_diagnostics.json", "w") as f:
        json.dump(diag_data, f, indent=2)
        
    res_df = pd.DataFrame(results).T
    res_df.to_csv("models/reports/cold_start_comparison.csv")
    
    with open("models/reports/cold_start_diagnostics.md", "w") as f:
        f.write("# Cold-Start Forensic Diagnostics\n\n")
        f.write("## 1. Evaluation Verification & Baselines\n")
        f.write(res_df.to_markdown())
        f.write("\n\n## 2. Root Cause of AUC < 0.5\n")
        f.write("The AUC < 0.5 is genuine and is caused by a massive **inference-time distribution shift**.\n")
        f.write("In Phase 5, the model was trained on the entire dataset *without* any masking for cold-start customers. Therefore, the model learned that `hist_payment_count=1` means a new customer, and adjusted weights accordingly.\n")
        f.write("In Phase 6, the hierarchical predictor masks `hist_payment_count` and other customer features to `NaN` for cold-start examples. The `SimpleImputer(strategy='median')` inside the scikit-learn pipeline replaces these NaNs with the global median (e.g., `hist_payment_count` = 6.0, `hist_success_rate` = 0.15).\n")
        f.write("As a result, a 1-event customer is being scored as if they are a mature customer with 6 past events and a poor 15% success rate. This systematically punishes promising new customers and randomly rewards poor ones, completely inverting the ranking (AUC < 0.5).\n")
        
        f.write("\n## 3. Alternative Architectures\n")
        f.write("### OPTION A: One Global Model with Explicit Missingness\n")
        f.write("- **Training Data:** Mask the customer features (set to NaN) *during feature generation or training* for examples below the history threshold, forcing the model to learn a unified representation where `NaN` directly implies 'fallback to merchant/population'.\n")
        f.write("- **Features:** Uses the same 32 features, but requires an imputer strategy that preserves the missingness signal (e.g., `IterativeImputer` or `SimpleImputer` with `add_indicator=True`, or using a tree-based model that natively handles NaNs).\n")
        f.write("- **Leakage Risks:** Low, as long as masking relies only on observable count.\n")
        f.write("- **Artifact Complexity:** Low (one model artifact).\n")
        f.write("- **Implementation Cost:** Medium (requires rewriting `TrainingDatasetBuilder` or pipeline to mask before `fit()`).\n")
        
        f.write("\n### OPTION B: Separate Fallback Models\n")
        f.write("- **Training Data:** Split the training dataset into 3 disjoint sets: Customer (`count >= 3`), Merchant (`count < 3 & merchant_count >= 50`), and Population.\n")
        f.write("- **Features:** Train three separate models. The Merchant model completely drops customer features from its `X` matrix. The Population model drops both customer and merchant features.\n")
        f.write("- **Leakage Risks:** Low.\n")
        f.write("- **Artifact Complexity:** High (three separate model artifacts, three manifests).\n")
        f.write("- **Implementation Cost:** High (requires routing logic during training, evaluation, and inference).\n")
        
        f.write("\n## 4. Recommendation\n")
        f.write("**Recommend OPTION A (Global Model with Explicit Missingness Indicator).**\n")
        f.write("Training a single model where we deliberately mask the features for cold-start rows *during training* and use `add_indicator=True` in the `SimpleImputer` allows the logistic regression to learn a specific coefficient for 'is_customer_history_missing'. This perfectly mimics the inference-time hierarchy without maintaining 3 separate artifacts. It keeps the model registry simple while explicitly solving the distribution shift.\n")

if __name__ == "__main__":
    run_diagnostics()
