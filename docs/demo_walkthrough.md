# REVIVE: Adaptive AI Revenue Recovery Agent
**Demo Walkthrough & Script**

This document serves as the guide for demonstrating the REVIVE system.

## How to Run

You need two terminal windows. Run these from the root of the project:

**Terminal 1 (Backend API):**
```bash
uv run uvicorn src.api.main:app
```

**Terminal 2 (Frontend UI):**
```bash
uv run streamlit run ui/app.py
```

## Recommended 2–5 Minute Demo Flow

### 1. The Landing Page (30s)
- **Action:** Open the Streamlit UI. Do not select a case yet.
- **Talking Points:**
  - Introduce **REVIVE** as an *Adaptive AI Revenue Recovery Agent*.
  - Explain the core principle: "Prediction is probabilistic. Policy is deterministic. Execution is auditable."
  - Briefly walk through the system flow from Failed Payment → Predict → Decide → Execute → Verify → Audit.
  - Show the **Evaluation Evidence** panel: Point out that on our clean synthetic benchmark, the ML policy reproduced the exact same decisions as the strong historical heuristic (₹49,495 recovered, 0% lift). Emphasize that REVIVE's value is in providing a rigorous framework to *evaluate* AI, rather than blindly assuming AI always wins.
  - Emphasize that the demo runs in a simulated environment—no live bank connections or real Razorpay executions occur.

### 2. The High-Probability Recovery Case (90s)
- **Action:** Select "Case A - Insufficient funds - High Confidence" (or Case F - "Will Succeed on Retry") from the sidebar.
- **Talking Points:**
  - **A. PAYMENT:** Point out the failure reason (`ERR_INSUFFICIENT_FUNDS`). This is a financial failure.
  - **B. AI PREDICTION:** Show the *Probabilistic* ML prediction. For example, it might predict a 70%+ chance of recovery.
  - **C. DECISION:** Show the *Deterministic* Policy check. Even though the ML likes it, it must pass the policy engine (e.g. Budget Remaining > 0, within allowed retry windows). Show the human-readable explanation of why this action was selected.
  - **Action:** Click **"▶ TRIGGER RECOVERY"**.
  - **D. EXECUTION & E. OUTCOME:** Show how the action moves to "Controlled" execution and the outcome is verified independently. Point out the successful recovery amount and the updated Obligation Status (e.g., `SUCCESS`).
  - **F. AUDIT TIMELINE:** Expand the chronological events. Show that every actor (Bank, Revive, Generator, PolicyEngine, MLPredictor) logged its exact inputs and outputs. This ensures total traceability.

### 3. The Negative Cases (60s)
- **Action:** Select "Case C - Mandate Revoked/Expired".
- **Talking Points:**
  - Demonstrate that because the mandate is revoked, the deterministic policy engine rejects all recovery attempts, regardless of any ML probabilities.
  - **Action:** Click "Trigger Recovery".
  - Show the clean error state (e.g. "Execution Refused: No policy-valid candidates generated").
- **Action:** Select "Case E - Policy Restricted (Too many attempts)".
- **Talking Points:**
  - Point out that the budget is exhausted. The UI correctly surfaces this state and refuses execution.

### 4. Reset & Determinism (30s)
- **Action:** Go back to the High-Probability case you just executed. Click **"↺ Reset Case"**.
- **Talking Points:**
  - Show that the case instantly reverts to its initial failed state, erasing the in-memory execution trace.
  - Explain that the underlying simulator, model, and benchmark artifacts remain completely untouched. The demo is fully deterministic and repeatable.

## What Claims Are Supported?
- **Supported:** REVIVE successfully separates probabilistic ML prediction from deterministic business policy.
- **Supported:** REVIVE maintains a strict, append-only chronological audit trail of all automated decisions.
- **Supported:** The simulator cleanly isolates RNG streams, ensuring fair evaluation of policies.

## Current Limitations (Do Not Claim)
- **Not Supported:** Guaranteed recovery or generic "ML Lift" (our benchmark shows 0% lift over the strong baseline).
- **Not Supported:** Live Razorpay API integration or real money movement.
- **Not Supported:** Access to live bank balances, true paydays, or external data scraping.
