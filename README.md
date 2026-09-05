# REVIVE
## Adaptive AI Revenue Recovery Agent

Turn failed recurring payments into recoverable revenue with prediction, policy and auditable execution.

### What it solves
When a recurring payment (e-mandate) fails, companies typically use static rule-based retries (e.g., T+1, T+3, T+5), causing 
significant revenue loss from badly timed retries, or high network penalties from blind retries.

REVIVE replaces static schedules with a calibrated ML probability policy that executes retries at the exact optimal time for each mandate while adhering strictly to a deterministic business policy framework to ensure safe operations.

### Architecture
- **Predictor**: Point-in-time calibrated machine learning models.
- **Policy Engine**: Deterministic rules engine enforcing retry limits, cooldown periods, and stopping conditions.
- **Auditor**: Append-only log tracing exactly why the agent decided to act or wait.
- **Simulator**: Robust synthetic environment for safe agent evaluation.
- **Frontend**: Operational React console to investigate and trigger recovery workflows.
- **Backend**: FastAPI providing the operational endpoints.

### Evaluation Evidence
The trained ML policy achieved a 100% win rate against a baseline of No Recovery, and tied identically with a hand-tuned Smart Historical Heuristic at ₹50,192.12 on a locked Phase 13A benchmark cohort (1000 customers).
In a capacity-constrained environment (100 slots for 417 eligible mandates), Expected Value (EV) prioritization recovered ₹21,422.74, a 16.43% improvement over strict Probability (P) based prioritization (₹18,400.37).

### Setup

1. Install Python dependencies (uv is recommended):
   `ash
   uv sync
   `

2. Install Frontend dependencies:
   `ash
   cd frontend
   npm install
   `

### Run commands

Start the backend:
`ash
uv run uvicorn src.api.main:app
`

Start the frontend:
`ash
cd frontend
npm run dev
`

*Note: The previous Streamlit interface (uv run streamlit run ui/app.py) is preserved as a legacy fallback.*

### Demo walkthrough

1. Open the React frontend (usually http://localhost:5173).
2. Read the Overview page.
3. Navigate to **Recovery Queue**.
4. Select a demo case (e.g. Case A).
5. Inspect the failed payment, AI prediction, and policy constraints.
6. Click **TRIGGER RECOVERY** to watch the state pipeline execute and verify the outcome.
7. Observe the Audit Timeline update with the executed actions.
8. Explore the **Exceptions** page to understand when the agent correctly refuses to act.

### Limitations
- The system is currently powered entirely by a robust synthetic simulator (data/demo/cases.json). No real customer banking data is stored or processed.
