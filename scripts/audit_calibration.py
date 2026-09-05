import pandas as pd
import numpy as np
import json
import joblib
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
import matplotlib.pyplot as plt
from src.models.calibrated import CalibratedWrapper

def expected_calibration_error(y_true, y_prob, n_bins=10):
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy='uniform')
    
    # Calculate counts manually for weighting
    bins = np.linspace(0., 1., n_bins + 1)
    binids = np.searchsorted(bins[1:-1], y_prob)
    
    bin_sums = np.bincount(binids, weights=y_prob, minlength=len(bins))
    bin_true = np.bincount(binids, weights=y_true, minlength=len(bins))
    bin_total = np.bincount(binids, minlength=len(bins))
    
    nonzero = bin_total != 0
    prob_pred = bin_sums[nonzero] / bin_total[nonzero]
    prob_true = bin_true[nonzero] / bin_total[nonzero]
    
    ece = np.sum(np.abs(prob_pred - prob_true) * (bin_total[nonzero] / len(y_true)))
    return ece

def generate_calibration_table(y_true, y_prob, n_bins=10):
    bins = np.linspace(0., 1., n_bins + 1)
    binids = np.digitize(y_prob, bins) - 1
    
    # Clip binids to be within 0 to n_bins-1 (for 1.0)
    binids = np.clip(binids, 0, n_bins - 1)
    
    data = []
    for i in range(n_bins):
        mask = binids == i
        count = np.sum(mask)
        mean_prob = np.mean(y_prob[mask]) if count > 0 else 0.0
        obs_rate = np.mean(y_true[mask]) if count > 0 else 0.0
        gap = abs(mean_prob - obs_rate) if count > 0 else 0.0
        
        data.append({
            "bin": f"{bins[i]:.1f}-{bins[i+1]:.1f}",
            "count": count,
            "mean_predicted_prob": mean_prob,
            "observed_success_rate": obs_rate,
            "absolute_gap": gap
        })
    return pd.DataFrame(data)

def plot_calib(table, title, path):
    valid = table[table['count'] > 0]
    plt.figure(figsize=(8,8))
    plt.plot(valid['mean_predicted_prob'], valid['observed_success_rate'], marker='o', label='Model')
    plt.plot([0,1], [0,1], linestyle='--', color='gray', label='Perfect')
    plt.xlabel('Mean Predicted Probability')
    plt.ylabel('Observed Success Rate')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(path)
    plt.close()

def audit():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-version", type=str, default="v1.1")
    args = parser.parse_args()
    
    print("Loading data and pipeline...")
    with open(f"models/artifacts/model_manifest_{args.model_version}.json", "r") as f:
        manifest = json.load(f)
        
    pipeline = joblib.load(manifest["artifact_path"])
    
    df = pd.read_parquet("data/features/training_features.parquet")
    with open("data/features/feature_metadata.json", "r") as f:
        meta = json.load(f)
        
    train_end = pd.to_datetime(meta["train_end_timestamp"])
    val_end = pd.to_datetime(meta["validation_end_timestamp"])
    df['cutoff_timestamp'] = pd.to_datetime(df['cutoff_timestamp'])
    
    val_df = df[(df['cutoff_timestamp'] > train_end) & (df['cutoff_timestamp'] <= val_end)].copy()
    test_df = df[df['cutoff_timestamp'] > val_end].copy()
    
    y_val = val_df['target_success']
    X_val = val_df.drop(columns=pipeline.forbidden_columns, errors='ignore')
    
    y_test = test_df['target_success']
    X_test = test_df.drop(columns=pipeline.forbidden_columns, errors='ignore')
    
    # RAW
    prob_val_raw = pipeline.predict_proba(X_val)
    prob_test_raw = pipeline.predict_proba(X_test)
    
    # SIGMOID CALIBRATION (Fit on Val)
    # Platt scaling: LogisticRegression on predicted probabilities
    from sklearn.linear_model import LogisticRegression
    calib_sig = LogisticRegression()
    # Reshape for sklearn
    val_preds_2d = prob_val_raw.to_numpy().reshape(-1, 1)
    test_preds_2d = prob_test_raw.to_numpy().reshape(-1, 1)
    calib_sig.fit(val_preds_2d, y_val)
    prob_test_sig = calib_sig.predict_proba(test_preds_2d)[:, 1]
    
    # ISOTONIC CALIBRATION (Fit on Val)
    from sklearn.isotonic import IsotonicRegression
    calib_iso = IsotonicRegression(out_of_bounds='clip')
    calib_iso.fit(prob_val_raw, y_val)
    prob_test_iso = calib_iso.predict(prob_test_raw)
    
    # Evaluate on Test
    def eval_model(y_prob):
        return {
            "brier_score": brier_score_loss(y_test, y_prob),
            "log_loss": log_loss(y_test, y_prob),
            "ece": expected_calibration_error(y_test, y_prob),
            "roc_auc": roc_auc_score(y_test, y_prob)
        }
        
    metrics_raw = eval_model(prob_test_raw)
    metrics_sig = eval_model(prob_test_sig)
    metrics_iso = eval_model(prob_test_iso)
    
    print("\nMetrics on Held-Out Test Set:")
    print(f"RAW     -> Brier: {metrics_raw['brier_score']:.4f}, LogLoss: {metrics_raw['log_loss']:.4f}, ECE: {metrics_raw['ece']:.4f}, ROC-AUC: {metrics_raw['roc_auc']:.4f}")
    print(f"SIGMOID -> Brier: {metrics_sig['brier_score']:.4f}, LogLoss: {metrics_sig['log_loss']:.4f}, ECE: {metrics_sig['ece']:.4f}, ROC-AUC: {metrics_sig['roc_auc']:.4f}")
    print(f"ISOTONIC-> Brier: {metrics_iso['brier_score']:.4f}, LogLoss: {metrics_iso['log_loss']:.4f}, ECE: {metrics_iso['ece']:.4f}, ROC-AUC: {metrics_iso['roc_auc']:.4f}")
    
    comparison = {
        "raw": metrics_raw,
        "sigmoid": metrics_sig,
        "isotonic": metrics_iso
    }
    
    # Pick Best based on ECE and Brier
    best_method = "raw"
    best_brier = metrics_raw["brier_score"]
    
    if metrics_sig["brier_score"] < best_brier and metrics_sig["brier_score"] < metrics_iso["brier_score"]:
        best_method = "sigmoid"
        best_brier = metrics_sig["brier_score"]
    elif metrics_iso["brier_score"] < best_brier:
        best_method = "isotonic"
        
    print(f"\nAdopted Calibration Method: {best_method.upper()}")
    
    # Generate tables
    table_raw = generate_calibration_table(y_test, prob_test_raw)
    table_raw.to_csv("models/reports/calibration_raw.csv", index=False)
    plot_calib(table_raw, "Raw Reliability Curve", "models/reports/calibration_raw.png")
    
    if best_method != "raw":
        prob_best = prob_test_sig if best_method == "sigmoid" else prob_test_iso
        
        table_calib = generate_calibration_table(y_test, prob_best)
        table_calib.to_csv("models/reports/calibration_calibrated.csv", index=False)
        plot_calib(table_calib, f"Calibrated Reliability ({best_method.capitalize()})", "models/reports/calibration_calibrated.png")
        
        wrapper = CalibratedWrapper(pipeline, calib_sig if best_method == "sigmoid" else calib_iso, best_method)
        joblib.dump(wrapper, f"models/artifacts/model_calibrated_{args.model_version}.pkl")
        
        manifest["artifact_path"] = f"models/artifacts/model_calibrated_{args.model_version}.pkl"
        manifest["calibration_method"] = best_method
        manifest["metrics"]["test"]["brier_score"] = comparison[best_method]["brier_score"]
        manifest["metrics"]["test"]["log_loss"] = comparison[best_method]["log_loss"]
        manifest["metrics"]["test"]["ece"] = comparison[best_method]["ece"]
        manifest["metrics"]["test"]["roc_auc"] = comparison[best_method]["roc_auc"]
        
        with open(f"models/artifacts/model_manifest_{args.model_version}.json", "w") as f:
            json.dump(manifest, f, indent=2)
    else:
        # Just write empty or identical to calibrated if not adopted
        table_raw.to_csv("models/reports/calibration_calibrated.csv", index=False)
        plot_calib(table_raw, "Raw Reliability Curve", "models/reports/calibration_calibrated.png")
        manifest["calibration_method"] = "none"
        manifest["metrics"]["test"]["ece"] = comparison["raw"]["ece"]
        with open(f"models/artifacts/model_manifest_{args.model_version}.json", "w") as f:
            json.dump(manifest, f, indent=2)

    with open("models/reports/calibration_comparison.json", "w") as f:
        json.dump(comparison, f, indent=2)

if __name__ == "__main__":
    audit()
