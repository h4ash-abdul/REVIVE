# Pre-Registered Experiment: Phase 8 (REVIVE Policy Validation)

## Objective
The primary objective of this experiment is to evaluate the causal impact of the REVIVE ML-driven expected value (EV) strategy against the Smart Historical Heuristic baseline, holding all candidate universes, temporal constraints, retry budgets, and policy validations strictly constant.

A secondary objective is to perform an ablation study comparing the EV-weighted ML strategy against a pure Probability-ranked ML strategy to measure the economic impact of cost-and-amount weighting.

## Primary Metric
**Observed Revenue Difference**: Total recovered revenue (INR/₹) by REVIVE minus Total recovered revenue by the Smart Historical Heuristic.

## Statistical Methodology
- **Method**: Paired Bootstrap over mandate-level outcomes (with replacement).
- **Replicates**: 1,000
- **Seed**: 42 (Bootstrap RNG)
- **Unit of Observation**: Individual mandate-level paired outcomes (matched by `mandate_id`).

## Candidate Fairness Guarantee
All strategies receive the **identical candidate universe** constructed using a 30-day lookahead and pre-filtered by the strict `DeterministicPolicyEngine`.
- **Smart Historical Heuristic**: Determines its optimal historical hour, then snaps deterministically to the closest valid candidate in the pre-filtered universe.
- **ML Probability Strategy**: Scores the valid universe and selects the candidate maximizing $P(\text{success})$.
- **ML Expected Value Strategy**: Scores the valid universe and selects the candidate maximizing $E[V]$.

## EV Formula
$$E[V] = \left( P(\text{success}) \times \text{amount} \right) - \text{action\_cost}$$
For this initial benchmarking experiment, `action_cost` is fixed at ₹0.0 to isolate the effect of amount-weighting vs pure probability ranking.

## Cohort Definition
The experiment will be run against a generated synthetic cohort of 1,000 customers and 2,000 mandates, utilizing seed 42 for data generation and latent outcome processing.

## Interpretation Rules
The outcome of the primary comparison will be classified into one of three categories:

- **CASE A (Material Outperformance)**: The 5th percentile of the bootstrap revenue difference is strictly greater than ₹0, and the observed lift > 0%.
- **CASE B (Modest/Uncertain Outperformance)**: The observed lift > 0%, but the 5th percentile of the bootstrap revenue difference crosses or includes ₹0.
- **CASE C (No Outperformance)**: The observed lift is ≤ 0%.

Results will be reported unconditionally in `data/evaluation/phase8/phase8_final_report.md`.
