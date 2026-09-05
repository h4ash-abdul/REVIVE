# REVIVE End-to-End Recovery Flow

## 1. System Flow
REVIVE has been productized into an end-to-end recovery agent demo. The system follows a strict state machine:
`PAYMENT_FAILED` → `FAILURE_CLASSIFIED` → `FEATURES_COMPUTED` → `PREDICTION_CREATED` → `CANDIDATES_GENERATED` → `POLICY_PRECHECK` → `ACTION_SELECTED` → `EXECUTION_REQUESTED` → `EXECUTION_COMPLETED` → `OUTCOME_VERIFIED`.

## 2. Execution Boundary
The execution layer (`SimulatedExecutionAdapter`) represents a strict boundary. It accepts ONLY a valid `PolicyDecision` combined with a `CandidateAction`. If the policy is rejected or if the candidate action does not match the approved decision, execution fails with a `PolicyViolationError`. 
In this demo, the execution adapter interacts with the synthetic `OutcomeEngine` to simulate network payment results.

## 3. Verification Boundary
The `OutcomeVerifier` determines the actual result of an execution attempt. Critically, the outcome verification is attached to the *current* `PaymentObligation`. A new obligation for a mandate starts fresh; historical successes from previous billing cycles do not prematurely mark the new obligation as successful.

## 4. Audit Design
The `AuditLogger` is an append-only ledger that records every transition state with a timestamp, actor, and JSON details. The entire chronology of a recovery decision is packaged into a `RecoveryTrace`.

## 5. API Flow
The FastAPI backend (`src/api/main.py`) provides:
- `GET /cases`: Lists the available deterministic scenarios.
- `GET /cases/{key}/trace`: Retrieves the full `RecoveryTrace` (including audit events, decisions, and outcomes).
- `POST /cases/{key}/trigger`: Executes the end-to-end recovery pipeline for that specific case.

## 6. Demo Cases
The demo dataset contains deterministic edge cases selected from a simulated 500-customer cohort:
- **A**: Insufficient funds with high confidence recovery.
- **B**: Technical failure / Do Not Honor.
- **C**: Mandate Revoked/Expired.
- **D**: Unknown Failure.
- **E**: Policy Restricted (Too many attempts).
- **F**: Will Succeed on Retry.
- **G**: Will Exhaust Budget.

## 7. Observable vs Latent Data
The `SimulatedExecutionAdapter` receives latent state variables (Customer and Merchant latents) purely to pass them to the `OutcomeEngine` for execution. The `PolicyEngine`, `HierarchicalPredictor`, and `AuditLogger` operate *exclusively* on observable data (features, history, mandate details) to maintain realism. No latent states are exposed in the UI.

## 8. Simulation Disclaimer
This system uses a simulated environment (`OutcomeEngine`) to mimic Razorpay API interactions. No real banking data, balance checks, or production transactions are performed.

## 9. Current Limitations & Future Path
- The current Execution layer integrates with a synthetic generator.
- Future production integration will require swapping `SimulatedExecutionAdapter` with a `RazorpayExecutionAdapter` and `OutcomeVerifier` with a webhook-driven asynchronous verifier.
