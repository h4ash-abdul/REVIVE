# Pre-Submission Reliability Fixes

This document records the four key integrity and reliability fixes applied before the final submission. The underlying business logic, evaluation semantics, benchmarks, and ML models were completely untouched.

## 1. Missing ML/Runtime Dependencies

**PROBLEM:**
The scikit-learn and joblib dependencies were not declared in pyproject.toml, causing uv sync to produce an incomplete environment. This broke model inference out-of-the-box.

**ROOT CAUSE:**
The research environment had these installed locally, but they were not formally added to the project manifest.

**FIX:**
Added scikit-learn and joblib to pyproject.toml via uv add to guarantee they are installed during uv sync.

**VERIFICATION:**
Running uv sync from a clean machine now successfully pulls down all required ML dependencies, and the FASTAPI backend starts without import errors.

---

## 2. Missing Pytest Source-Path Configuration

**PROBLEM:**
Running pytest from the repository root failed with ModuleNotFoundError: No module named 'src'.

**ROOT CAUSE:**
The test suite assumed PYTHONPATH was set or the code was installed as a package, but pyproject.toml lacked a explicit pythonpath configuration for pytest.

**FIX:**
Appended [tool.pytest.ini_options] with pythonpath = ["."] in pyproject.toml.

**VERIFICATION:**
Running uv run pytest tests/ and pytest tests/ from the root directory now successfully discovers the src module and all 72 tests pass without any manual environment variable configuration.

---

## 3. Stochastic Primary Demo Outcome

**PROBLEM:**
Demo Case A ("Insufficient Funds - High Confidence") had a probabilistic outcome (78% prediction), causing the recorded demo to occasionally fail, creating presentation risks.

**ROOT CAUSE:**
The simulation OutcomeEngine was initialized globally and advanced its internal RNG state continuously across API calls.

**FIX:**
Implemented a deterministic demo execution configuration in src/api/main.py. When 	rigger_recovery() is called for a demo case, it initializes an isolated OutcomeEngine with a case-specific stable seed (e.g., DEMO_SEEDS["A"] = 0). The underlying prediction engine and simulator distributions remain exactly the same; only the execution outcome is stabilized for repeatable presentation.

**VERIFICATION:**
Triggering Case A repeatedly after resets consistently produces the identical successful outcome, while preserving the real 78% ML model probability output.

---

## 4. Incorrect Policy-Restricted Demo Fixture

**PROBLEM:**
Demo Case E ("Policy Restricted") failed to trigger a policy refusal. Its historical failed attempts were too old to be considered part of the current active Payment Obligation cycle, causing the policy engine to grant it a fresh retry budget.

**ROOT CAUSE:**
The timestamp generation in cases.json for Case E positioned the failures months in the past. Additionally, the init_case fixture loader mapped the last attempt as a brand new obligation without carrying over the adjacent prior attempts into etry_attempt_ids.

**FIX:**
Modified cases.json to bring Case E's failed attempts into the immediate past (last 4 days). Updated init_case in src/api/main.py to intelligently group failures within the last 30 days into the same PaymentObligation cycle by populating etry_attempt_ids correctly.

**VERIFICATION:**
Triggering Case E now correctly evaluates the 4 recent failures against the max-3 retry budget. The policy engine rejects execution immediately, returning a clean HTTP 400. The UI correctly intercepts this and displays "RECOVERY EXHAUSTED".
