import pandas as pd
from typing import List, Dict, Any
from src.domain.models import MandateResult

class MetricEngine:
    @staticmethod
    def calculate_metrics(results: List[MandateResult], baseline_strategy: str = "ImmediateRetryStrategy") -> Dict[str, Dict[str, Any]]:
        if not results:
            return {}
            
        df = pd.DataFrame([r.model_dump() for r in results])
        strategies = df['strategy'].unique()
        
        metrics = {}
        for strat in strategies:
            strat_df = df[df['strategy'] == strat]
            
            # BUSINESS
            total_revenue_at_risk = float(strat_df['initial_amount'].sum())
            total_recovered = float(strat_df['recovered_amount'].sum())
            recovery_rate = float(total_recovered / total_revenue_at_risk if total_revenue_at_risk > 0 else 0)
            
            # EFFICIENCY
            total_attempts = int(strat_df['attempt_count'].sum())
            recovered_df = strat_df[strat_df['recovered_boolean'] == True]
            avg_attempts_per_recovered = float(recovered_df['attempt_count'].mean()) if not recovered_df.empty else 0.0
            median_attempts_per_recovered = float(recovered_df['attempt_count'].median()) if not recovered_df.empty else 0.0
            avg_attempts_per_mandate = float(strat_df['attempt_count'].mean()) if not strat_df.empty else 0.0
            budget_exhaustion_rate = float(strat_df['retry_budget_exhausted'].mean())
            
            # SAFETY
            policy_violations = int(strat_df['policy_violation_count'].sum())
            
            # RELIABILITY
            exec_errors = int(strat_df['execution_error_count'].sum())
            
            metrics[strat] = {
                "BUSINESS": {
                    "total_revenue_at_risk": total_revenue_at_risk,
                    "total_recovered_revenue": total_recovered,
                    "recovery_rate": recovery_rate,
                    "incremental_recovered_revenue_vs_Immediate": 0.0, # calculated later
                    "lift_vs_Immediate": 0.0, # calculated later
                    "incremental_recovered_revenue_vs_Smart": 0.0,
                    "lift_vs_Smart": 0.0
                },
                "EFFICIENCY": {
                    "total_payment_attempts": total_attempts,
                    "average_attempts_per_recovered_mandate": avg_attempts_per_recovered,
                    "median_attempts_per_recovered_mandate": median_attempts_per_recovered,
                    "average_attempts_per_mandate": avg_attempts_per_mandate,
                    "retry_budget_exhaustion_rate": budget_exhaustion_rate
                },
                "SAFETY": {
                    "policy_violations": policy_violations,
                    "invalid_executions": 0, # Placeholder
                    "retry_after_success_attempts": 0, # Impossible by runner design, but could track
                    "budget_violations": 0,
                    "duplicate_execution_attempts": 0
                },
                "RELIABILITY": {
                    "execution_failures": exec_errors,
                    "simulator_errors": 0,
                    "incomplete_mandate_simulations": 0
                }
            }
            
        # Calculate comparative lifts
        imm_metrics = metrics.get(baseline_strategy, {}).get("BUSINESS", {})
        imm_recovered = imm_metrics.get("total_recovered_revenue", 0)
        
        smart_metrics = metrics.get("SmartHistoricalHeuristicStrategy", {}).get("BUSINESS", {})
        smart_recovered = smart_metrics.get("total_recovered_revenue", 0)
        
        for strat in strategies:
            strat_rec = metrics[strat]["BUSINESS"]["total_recovered_revenue"]
            
            # Vs Immediate
            metrics[strat]["BUSINESS"]["incremental_recovered_revenue_vs_Immediate"] = strat_rec - imm_recovered
            metrics[strat]["BUSINESS"]["lift_vs_Immediate"] = (strat_rec / imm_recovered - 1) if imm_recovered > 0 else 0
            
            # Vs Smart (if it exists and is not itself)
            if "SmartHistoricalHeuristicStrategy" in metrics:
                metrics[strat]["BUSINESS"]["incremental_recovered_revenue_vs_Smart"] = strat_rec - smart_recovered
                metrics[strat]["BUSINESS"]["lift_vs_Smart"] = (strat_rec / smart_recovered - 1) if smart_recovered > 0 else 0
                
        return metrics
