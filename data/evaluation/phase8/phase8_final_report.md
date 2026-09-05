# Phase 8 Final Report: REVIVE Decision-Policy Experiment

## 1. Methodology
- **Cohort Size**: 1000 customers, 2000 mandates
- **Seed**: 42 (Simulator), 42 (Bootstrap)
- **Candidate Universe**: 30-day lookahead, strictly identical across strategies.
- **Strategies**: Smart Historical Heuristic, ML Probability, ML Expected Value (cost=₹0.0).
- **Metric**: Total Recovered Revenue (INR/₹)

## 2. Overall Strategy Performance

| Strategy | Revenue at Risk | Recovered Revenue | Recovery Rate | Avg Attempts | Budget Exhausted Rate | Policy Violations |
|----------|-----------------|-------------------|---------------|--------------|-----------------------|-------------------|
| SmartHeuristic | ₹128,368.32 | ₹49,908.03 | 39.3% | 1.78 | 43.6% | 368302 |
| MLProbability | ₹128,368.32 | ₹49,331.88 | 38.6% | 1.81 | 46.5% | 374224 |
| MLExpectedValue | ₹128,368.32 | ₹47,526.23 | 39.3% | 1.82 | 47.2% | 374959 |

## 3. Primary Comparison: MLExpectedValue vs SmartHeuristic
- **Observed Revenue Difference**: ₹-2,381.80
- **Observed Percentage Lift**: -4.77%
- **Median Bootstrap Difference**: ₹-2,444.88
- **90% Confidence Interval**: [₹-8,876.41, ₹3,838.73]
- **Probability Challenger Wins**: 26.1%

### Recovery Rate Paired Counts
- **Shared Recoveries**: 121
- **Shared Failures**: 210
- **Smart-only Recoveries**: 43
- **REVIVE-only Recoveries**: 43
- **Net Recovery Rate Difference**: 0.00%

## 4. EV Ablation: MLExpectedValue vs MLProbability
- **Observed Revenue Difference**: ₹-1,805.65
- **Observed Percentage Lift**: -3.66%
- **Median Bootstrap Difference**: ₹-1,726.85
- **90% Confidence Interval**: [₹-7,327.15, ₹4,167.78]

## 5. Result Classification
**CASE C: REVIVE does not outperform Smart.**

## 6. Interpretation
The experiment was conducted with strict adherence to candidate universe identicality and outcome independence. 
