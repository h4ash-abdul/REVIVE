# REVIVE Architecture

## Domain Model
The core domain model represents the state of recurring payment mandates and their associated obligations.

### Key Entities:
* `Mandate`: A recurring payment authorization (Active, Revoked, Expired, Completed).
* `PaymentAttempt`: A historical atomic attempt to charge a mandate. Includes a `network_return_code`.
* `PaymentObligation`: Represents a single recurring billing cycle's recovery state. Resolves the ambiguity of "historical mandate success" vs "current cycle success".
  * Tracks `due_time`, `amount`, and current recovery `status` (`pending`, `active_recovery`, `success`, `failed_exhausted`).
  * Links the `original_attempt_id` that triggered the recovery to all subsequent `retry_attempt_ids`.

## Policy Engine
The `DeterministicPolicyEngine` is a stateless rule evaluator that enforces the business constraints defined in `PolicyConfig`.

* **Pre-Filter (`pre_filter`)**: Evaluates a list of candidate actions before ML scoring. Checks retry budgets, minimum spacing, execution windows, and stops if the *current obligation* has already succeeded. It strictly scopes retry budgets to the current obligation's retry count.
* **Final Validation (`final_validate`)**: A safety double-check invoked just prior to execution. Re-evaluates the selected action against the same rules.

## Intelligent Scheduler (Phase 7)
* `CandidateGenerator`: Deterministically produces time-based retry slots.
* `CandidateScoringService`: Uses the `PointInTimeFeatureBuilder` and hierarchical `HierarchicalPredictor` (ML model) to predict the probability of success for candidate slots.
* `CopilotStrategy`: Orchestrates the flow: Generate -> Pre-Filter -> Score -> Rank -> Final-Validate -> Act. Emits a rich `StrategyResult` tracking alternatives and decision provenance.
