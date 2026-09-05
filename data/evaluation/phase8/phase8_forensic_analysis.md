# Phase 8.1 Forensic Analysis

## 1. Decision Disagreement
- **Smart vs ML Probability**: 92.0% disagreement
- **Smart vs ML EV**: 92.0% disagreement
- **ML Probability vs ML EV**: **0.0% disagreement** (100% agreement)

## 2. EV Failure Analysis: Why ML-EV < ML Probability
The mathematical formulation for ML EV is `EV = P(success) * amount - action_cost`. 
Since `action_cost` was set to 0.0, the formula simplifies to `P(success) * amount`. 
Crucially, when scoring the candidate universe for a *single* failed mandate, the `amount` is a constant across all candidate retry times. Scaling a list of probabilities by a positive constant does not change their relative ordering. Therefore, `argmax(P * amount)` is mathematically identical to `argmax(P)`.

**Conclusion**: ML Probability and ML EV executed the exact same actions. The observed difference in final recovered revenue (-₹1,805.65) was a ghost effect caused by experimental design flaw: the `OutcomeEngine` RNG state was shared sequentially across the benchmark runner, causing identical actions to yield different outcomes due to random state drift.

## 3. Heuristic Quality & Synthetic Circularity
The synthetic `DataGenerator` uses strong, static temporal preferences (`time_of_day_preference`). The `SmartHistoricalHeuristic` looks at past successes and extracts the exact historical successful hour. In a highly stationary synthetic environment, the heuristic is effectively a cheat code that directly reads the latent generating function.
The ML model learns this via logistic regression, but the heuristic perfectly memorizes it. Thus, the current experiment primarily measures the prediction of a known synthetic signal rather than true incremental decision value.

## 4. Sequential Decision Flaw
The ML model optimizes for the highest absolute probability in a vacuum (greedy selection). It does not consider the sequence of 3 retries, option value, or budget exhaustion. 

## 5. Production Decision Problem
In simulation, counterfactual outcomes are available (we can simulate any candidate). In production, we only observe the outcome of the chosen action (bandit feedback). This causes severe off-policy evaluation limitations and selection bias, which point-in-time supervised learning cannot easily overcome without explicit exploration.

## 6. Final Recommendation
**C. Reformulate as sequential decision optimization**

The evidence proves that point-in-time single-candidate ranking with a degenerate EV formula adds no value. The true problem is a sequential resource allocation problem under partial observability. REVIVE's next technical milestone must abandon single-step supervised ranking and implement a sequential policy (e.g., reinforcement learning or contextual bandits) that optimizes the entire 3-retry sequence while actively managing off-policy exploration.
