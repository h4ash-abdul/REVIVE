import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, log_loss, brier_score_loss
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, Tuple

class ModelEvaluator:
    @staticmethod
    def evaluate(y_true: pd.Series, y_prob: pd.Series) -> Dict[str, float]:
        """
        Calculates rank and probability quality metrics. 
        Threshold-free evaluation is used because this is a probability-ranking model.
        Accuracy is NOT used, as it requires choosing an arbitrary threshold which destroys
        the continuous ranking capability essential for the scheduler.
        """
        # Ensure we have both classes before evaluating discrimination
        if len(y_true.unique()) > 1:
            roc_auc = roc_auc_score(y_true, y_prob)
            pr_auc = average_precision_score(y_true, y_prob)
            ll = log_loss(y_true, y_prob)
        else:
            roc_auc = float('nan')
            pr_auc = float('nan')
            ll = float('nan')
            
        brier = brier_score_loss(y_true, y_prob)
        
        return {
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            "log_loss": float(ll),
            "brier_score": float(brier)
        }

    @staticmethod
    def calculate_calibration(y_true: pd.Series, y_prob: pd.Series, n_bins: int = 10) -> pd.DataFrame:
        """
        Creates a calibration table by binning predicted probabilities.
        """
        df = pd.DataFrame({'y_true': y_true, 'y_prob': y_prob})
        
        # Determine bin edges based on percentiles to ensure equal-sized buckets where possible
        # or just use uniform binning. We will use uniform quantile binning if possible, 
        # else fallback to uniform space binning.
        try:
            df['bin'] = pd.qcut(df['y_prob'], q=n_bins, duplicates='drop')
        except ValueError:
            # Fallback to absolute bins
            df['bin'] = pd.cut(df['y_prob'], bins=np.linspace(0, 1, n_bins + 1))
            
        calibration = df.groupby('bin', observed=False).agg(
            mean_predicted_prob=('y_prob', 'mean'),
            observed_success_rate=('y_true', 'mean'),
            count=('y_true', 'count')
        ).reset_index()
        
        # Convert bin to string for easy serialization
        calibration['bin'] = calibration['bin'].astype(str)
        return calibration

    @staticmethod
    def plot_calibration(calibration_df: pd.DataFrame, out_path: str):
        """
        Plots a calibration curve.
        """
        plt.figure(figsize=(8, 8))
        
        # Only plot bins with actual samples
        valid_bins = calibration_df[calibration_df['count'] > 0]
        
        plt.plot(valid_bins['mean_predicted_prob'], valid_bins['observed_success_rate'], 
                 marker='o', linewidth=2, label='Model')
        
        # Perfect calibration line
        plt.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfect Calibration')
        
        plt.xlabel('Mean Predicted Probability')
        plt.ylabel('Observed Success Rate')
        plt.title('Reliability Curve (Calibration)')
        plt.legend()
        plt.grid(True)
        
        plt.savefig(out_path)
        plt.close()
