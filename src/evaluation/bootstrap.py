import numpy as np
import pandas as pd
from typing import Dict, List, Any
import random

class PairedBootstrapAnalyzer:
    def __init__(self, seed: int = 42, replicates: int = 1000):
        self.seed = seed
        self.replicates = replicates
        self.rng = np.random.default_rng(seed)
        
    def analyze(self, df_results: pd.DataFrame, strat_a: str, strat_b: str) -> Dict[str, Any]:
        """
        strat_a is the baseline (e.g., Smart)
        strat_b is the challenger (e.g., REVIVE)
        """
        # Ensure we only have the two strategies
        df_a = df_results[df_results['strategy'] == strat_a].set_index('mandate_id')
        df_b = df_results[df_results['strategy'] == strat_b].set_index('mandate_id')
        
        # Inner join to ensure strict pairing
        merged = df_a.join(df_b, lsuffix='_a', rsuffix='_b', how='inner')
        mandate_ids = merged.index.values
        n = len(mandate_ids)
        
        rev_a_all = merged['recovered_amount_a'].values
        rev_b_all = merged['recovered_amount_b'].values
        
        # Observed metrics
        obs_rev_a = np.sum(rev_a_all)
        obs_rev_b = np.sum(rev_b_all)
        obs_diff = obs_rev_b - obs_rev_a
        obs_lift = obs_diff / obs_rev_a if obs_rev_a > 0 else 0
        
        # Recovery Rate Paired Analysis
        rec_a = merged['recovered_boolean_a'].values
        rec_b = merged['recovered_boolean_b'].values
        
        shared_recoveries = np.sum(rec_a & rec_b)
        shared_failures = np.sum(~rec_a & ~rec_b)
        a_only = np.sum(rec_a & ~rec_b)
        b_only = np.sum(~rec_a & rec_b)
        obs_rate_diff = np.mean(rec_b) - np.mean(rec_a)
        
        # Bootstrap
        boot_diffs = np.zeros(self.replicates)
        boot_lifts = np.zeros(self.replicates)
        
        for i in range(self.replicates):
            indices = self.rng.choice(n, size=n, replace=True)
            samp_a = rev_a_all[indices]
            samp_b = rev_b_all[indices]
            
            sum_a = np.sum(samp_a)
            sum_b = np.sum(samp_b)
            
            boot_diffs[i] = sum_b - sum_a
            boot_lifts[i] = (sum_b - sum_a) / sum_a if sum_a > 0 else 0
            
        p_b_greater = np.mean(boot_diffs > 0)
        
        return {
            "comparison": f"{strat_b} vs {strat_a}",
            "n_mandates": n,
            "observed": {
                f"recovered_revenue_{strat_a}": float(obs_rev_a),
                f"recovered_revenue_{strat_b}": float(obs_rev_b),
                "revenue_difference": float(obs_diff),
                "percentage_lift": float(obs_lift),
                "recovery_rate_difference": float(obs_rate_diff)
            },
            "bootstrap": {
                "replicates": self.replicates,
                "median_difference": float(np.median(boot_diffs)),
                "p05_difference": float(np.percentile(boot_diffs, 5)),
                "p95_difference": float(np.percentile(boot_diffs, 95)),
                "p025_difference": float(np.percentile(boot_diffs, 2.5)),
                "p975_difference": float(np.percentile(boot_diffs, 97.5)),
                "prob_challenger_wins": float(p_b_greater)
            },
            "recovery_paired_counts": {
                "shared_recoveries": int(shared_recoveries),
                "shared_failures": int(shared_failures),
                f"{strat_a}_only_recoveries": int(a_only),
                f"{strat_b}_only_recoveries": int(b_only)
            }
        }
