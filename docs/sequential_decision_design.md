# Sequential Decision Design for Recovery Scheduling

## 1. Problem Formulation
REVIVE's recovery scheduling is not a single-step candidate ranking problem. It is a finite-horizon sequential decision problem under partial observability. When a payment fails, the system has a limited retry budget (e.g., 3 retries) and must choose a sequence of retry times. The process terminates either when a retry succeeds (absorbing state with positive reward) or when the retry budget is exhausted (absorbing state with zero reward).

## 2. State Representation
The sequential state must encapsulate all information necessary to make the next decision, bounded by legitimate observability at decision time:
- **Mandate Context**: `customer_id`, `merchant_id`, `amount`, `currency`
- **Current Time**: Wall-clock time of the decision
- **Remaining Retry Budget**: `max_retries - current_attempts`
- **History**: All previously executed actions and their observed outcomes (success, failure network codes)
- **Current Obligation**: Tracks the lifecycle of the active failure cycle

*Constraint*: The state must **never** expose latent simulator variables (e.g., `time_of_day_preference`, `technical_failure_propensity`) or future ground-truth outcomes.

## 3. Action Space
The action space is dynamic and defined by the `CandidateUniverse`.
- **Action**: A `CandidateAction` consisting of a specific `scheduled_time` to execute a retry attempt.
- **Constraints**: Candidate actions are pre-filtered by the `DeterministicPolicyEngine` to ensure they comply with `min_hours_between_retries` and `allowed_execution_windows`.
- **Cost**: Currently, the action cost is $0.0. Every action consumes exactly 1 unit of the retry budget.

## 4. Transition Assumptions
- The transition probability $P(success | state, action)$ is estimated using the existing point-in-time calibrated logistic regression model (`HierarchicalPredictor`).
- If an action fails, the system transitions to a new state where `remaining_budget` is decremented by 1, the `current_time` advances to the action's `scheduled_time`, and the action is appended to `history` as a failure.
- If an action succeeds, the system transitions to a terminal state.

## 5. Reward / Objective
The objective is to maximize the expected recovered revenue over the full trajectory.
- **Immediate Reward**: $P(success | action) \times amount - action\_cost$
- If the action cost remains $0.0$, the EV formula scales the probability by a constant `amount`. By itself, this adds no value to a one-step candidate ranker. However, in a multi-step sequence, maximizing cumulative probability across a budget of $N$ retries becomes highly relevant.

## 6. Finite-Horizon Value Function
We define the value of a state $V(state, b)$ where $b$ is the remaining budget:

$$V(state, b) = \max_{a \in A_{valid}} \left[ P(success|a) \cdot amount + (1 - P(success|a)) \cdot V(state_{a, fail}, b - 1) \right]$$

- Terminal conditions: $V(state, 0) = 0$
- $A_{valid}$ are policy-compliant candidates generated from the new state's `current_time`.

## 7. Policy Constraints and Observability Boundary
The planner strictly utilizes the `DeterministicPolicyEngine` to filter candidates at every hypothetical future step. The planner enforces a strict observability boundary by using simulated failures to advance the hypothetical state during tree search, never inspecting the `OutcomeEngine` or latent objects.

## 8. Why this is Preferable to Greedy Ranking
A greedy one-step ranker (like the previous `MLProbabilityStrategy`) selects the absolute highest probability candidate for attempt 1. This can lead to early exhaustion of the best candidate or budget, ignoring the option value of waiting for a better candidate later in the sequence. A sequential planner explicitly optimizes the use of the limited retry budget across the entire sequence, acknowledging that a slightly suboptimal early retry might leave room for a highly optimal late retry.

## 9. Limitations & Production Off-Policy Challenge
- **Simulator Determinism**: The tree search simulates deterministic failures to evaluate deep branches. In reality, failure codes might vary, slightly altering the feature space for the next prediction.
- **Off-Policy Limitation**: In production, the system only observes the outcome of the single action it actually executes (bandit feedback). The supervised ML model cannot safely explore counterfactuals without accumulating selection bias. 

## 10. Why this is not yet Reinforcement Learning
This implementation uses Dynamic Programming / finite-horizon tree search with a learned transition model (Model-Based Planning). It is not Reinforcement Learning because it does not actively balance exploration vs. exploitation (e.g., UCB, Thompson Sampling), nor does it learn a policy or value function directly from delayed rewards (e.g., Q-learning or Policy Gradients). It simply plans greedily over a synthetic transition model.
