import streamlit as st
import requests
import time

API_URL = "http://localhost:8000"

st.set_page_config(page_title="REVIVE Investigator", layout="wide", initial_sidebar_state="expanded")

def fetch_cases():
    try:
        r = requests.get(f"{API_URL}/cases")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Failed to fetch cases: {e}")
        return []

def fetch_trace(key: str):
    try:
        r = requests.get(f"{API_URL}/cases/{key}/trace")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Failed to fetch trace: {e}")
        return None

def trigger_recovery(key: str):
    try:
        r = requests.post(f"{API_URL}/cases/{key}/trigger")
        r.raise_for_status()
        st.success("Recovery executed successfully.")
        return True
    except requests.exceptions.HTTPError as e:
        try:
            err_msg = e.response.json()["detail"]
            st.error(f"Execution Refused: {err_msg}")
        except:
            st.error(f"Failed to trigger recovery: {e}")
        return False
    except Exception as e:
        st.error(f"Failed to trigger recovery: {e}")
        return False

def reset_case(key: str):
    try:
        r = requests.post(f"{API_URL}/cases/{key}/reset")
        r.raise_for_status()
        st.success(f"Case {key} reset successfully.")
        return True
    except Exception as e:
        st.error(f"Failed to reset case: {e}")
        return False

# CSS Tweaks
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #4CAF50;
    }
    .metric-title {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-probabilistic { background-color: #2b1d52; color: #bca0f5; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
    .badge-deterministic { background-color: #1d3952; color: #9fc6eb; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
    .badge-controlled { background-color: #3d3b19; color: #ebd89f; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# -----------------
# SIDEBAR
# -----------------
st.sidebar.title("REVIVE")
st.sidebar.caption("Adaptive AI Revenue Recovery Agent")
st.sidebar.divider()

cases = fetch_cases()

if not cases:
    st.info("No cases available. Ensure the API is running and cases are generated.")
    st.stop()

st.sidebar.subheader("Recovery Queue")

if st.sidebar.button("🏠 View Dashboard", use_container_width=True):
    st.session_state.selected_case = None

st.sidebar.divider()

for c in cases:
    label = f"Case {c['scenario_key']} - {c['title']}"
    # Adding a visual hint about probability
    prob = f"{c['initial_probability']*100:.0f}%" if c['initial_probability'] else "0%"
    label += f" | {prob}"
    
    if st.sidebar.button(label, key=c['scenario_key'], use_container_width=True):
        st.session_state.selected_case = c['scenario_key']

# -----------------
# MAIN AREA
# -----------------
current_key = st.session_state.get('selected_case', None)

if current_key is None:
    # -----------------
    # LANDING PAGE
    # -----------------
    st.title("REVIVE Dashboard")
    st.subheader("Turn failed recurring payments into recoverable revenue with prediction, policy and auditable execution.")
    st.caption("Demo environment — simulated payment outcomes.")
    
    st.divider()
    
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.markdown("""
        ### System Flow
        REVIVE operates on a strict, auditable state machine:
        
        1. **PAYMENT FAILED**: A mandate charge fails.
        2. **PREDICT (Probabilistic)**: A calibrated ML model evaluates recovery probability across candidate actions.
        3. **DECIDE (Deterministic)**: A hardcoded policy engine checks rules (retry windows, frequency caps).
        4. **EXECUTE (Controlled)**: The chosen action is executed against the payment gateway.
        5. **VERIFY**: The outcome is confirmed.
        6. **AUDIT**: Every step is chronologically logged.
        """)
        
    with col2:
        st.markdown("""
        ### System Evidence
        **Phase 8 Clean Benchmark** (ML Expected Value vs Smart Historical Heuristic)
        
        - **Recovered Revenue:** ₹49,495.05 vs ₹49,495.05 (0.00% Lift)
        - **Shared Recoveries:** 167
        - **Shared Failures:** 250
        - **ML-only:** 0 | **Smart-only:** 0
        
        *On the current synthetic benchmark, the calibrated ML policy reproduced the exact same decisions as the historical heuristic. REVIVE evaluates whether adaptive decisioning actually adds value rather than assuming AI always improves outcomes.*
        
        ### Limitations
        - **Synthetic Simulator:** Results depend entirely on synthetic distributions.
        - **No Live Execution:** Demonstrates architecture, but connects to no live payment gateway (no real Razorpay API).
        - **Stationary Environment:** The strong heuristic ties ML because the underlying synthetic simulator behavior is stationary.
        """)
        
    st.info("👈 Select a case from the Recovery Queue in the sidebar to begin an investigation.")

else:
    # -----------------
    # CASE DETAILS
    # -----------------
    st.header(f"Case Investigation: {current_key}")
    
    trace = fetch_trace(current_key)
    if not trace:
        st.stop()
        
    # Current Obligation State Header
    st.markdown("### RECOVERY STATUS")
    c_stat1, c_stat2, c_stat3 = st.columns(3)
    c_stat1.metric("Obligation Status", trace.get('obligation_status', 'ACTIVE_RECOVERY').replace('_', ' '))
    c_stat2.metric("Retry Budget Remaining", f"{trace['budget_remaining']} attempts")
    c_stat3.metric("Failure Code", trace['failure_code'])
    st.divider()
    
    colA, colB = st.columns([2, 1])
    
    with colA:
        # A. PAYMENT
        st.markdown("### A. PAYMENT")
        c1, c2 = st.columns(2)
        c1.metric("Amount", f"₹{trace['amount']}")
        c2.metric("Failure Category", trace['failure_category'].replace('_', ' ').title())
        
        st.divider()
        
        # B & C. PREDICTION & DECISION
        c_pred, c_dec = st.columns(2)
        
        with c_pred:
            st.markdown("### B. AI PREDICTION <span class='badge-probabilistic'>PROBABILISTIC</span>", unsafe_allow_html=True)
            if trace.get('strategy_result'):
                sr = trace['strategy_result']
                st.write(f"**Prediction Mode:** `{sr['prediction_mode']}`")
                
                if sr.get('selected_action'):
                    # Find probability
                    prob = 0.0
                    for c in cases:
                        if c['scenario_key'] == current_key:
                            prob = c['initial_probability']
                            break
                    st.metric("Max Recovery Probability", f"{prob*100:.1f}%")
                else:
                    st.write("No viable candidates predicted.")
            else:
                st.info("Prediction pending execution...")
                
        with c_dec:
            st.markdown("### C. DECISION <span class='badge-deterministic'>DETERMINISTIC POLICY</span>", unsafe_allow_html=True)
            st.write(f"**Budget Remaining:** {trace['budget_remaining']} attempts")
            
            if trace.get('strategy_result'):
                sr = trace['strategy_result']
                if sr.get('selected_action'):
                    act = sr['selected_action']
                    st.success(f"**Recommended Action:** Retry at {act['scheduled_time']}")
                    
                    # Generate deterministic explanation
                    prob = 0.0
                    for c in cases:
                        if c['scenario_key'] == current_key:
                            prob = c['initial_probability']
                            break
                    
                    expl = f"REVIVE recommends retrying at {act['scheduled_time'][:16].replace('T', ' ')} UTC.\n\n"
                    expl += f"Predicted recovery probability: {prob*100:.1f}%.\n\n"
                    expl += f"The selected candidate ranked highest among {len(sr.get('candidate_actions', []))} policy-valid retry options.\n\n"
                    expl += f"Policy check: ALLOWED.\n\n"
                    expl += f"Retry budget remaining: {trace['budget_remaining']}."
                    
                    st.write(f"_{expl}_")
                else:
                    st.warning("**Decision:** Do Not Retry")
                    st.write("No candidates passed both policy filters and probability thresholds.")
            else:
                st.info("Decision pending execution...")
                
        st.divider()
        
        # D & E. EXECUTION & OUTCOME
        c_exec, c_out = st.columns(2)
        
        with c_exec:
            st.markdown("### D. EXECUTION <span class='badge-controlled'>CONTROLLED</span>", unsafe_allow_html=True)
            if trace.get('execution_record'):
                ex = trace['execution_record']
                st.write(f"**Status:** `{ex['status']}`")
                st.write(f"**Requested At:** {ex['requested_at']}")
                if ex.get('failure_reason'):
                    st.error(ex['failure_reason'])
            else:
                st.info("Execution pending...")
                
        with c_out:
            st.markdown("### E. OUTCOME")
            if trace.get('outcome'):
                out = trace['outcome']
                if out['success']:
                    st.success(f"**RECOVERED:** ₹{out['recovered_amount']}")
                else:
                    st.error(f"**FAILED:** {out['network_return_code']}")
            else:
                st.info("Outcome pending...")
                
        st.divider()
        
        # ACTION BUTTONS
        c_act1, c_act2, _ = st.columns([1, 1, 2])
        with c_act1:
            if st.button("▶ TRIGGER RECOVERY", type="primary", use_container_width=True):
                with st.spinner("Analyzing and Executing..."):
                    time.sleep(0.5) # Slight delay for UX
                    trigger_recovery(current_key)
                st.rerun()
        with c_act2:
            if st.button("↺ Reset Case", use_container_width=True):
                reset_case(current_key)
                st.rerun()

    with colB:
        # F. AUDIT TIMELINE
        st.markdown("### F. AUDIT TIMELINE")
        st.caption("Chronological ledger of state transitions.")
        
        events = trace.get('audit_trail', [])
        if not events:
            st.write("No events recorded yet.")
        else:
            for i, event in enumerate(reversed(events)):
                # Visual styling based on event type
                icon = "📝"
                if "FAILED" in event['event_type']: icon = "❌"
                elif "SUCCESS" in event['event_type'] or event['event_type'] == 'OUTCOME_VERIFIED': icon = "✅"
                elif "POLICY" in event['event_type']: icon = "🛡️"
                elif "PREDICTION" in event['event_type']: icon = "🧠"
                elif "EXECUTION" in event['event_type']: icon = "⚙️"
                
                with st.expander(f"{icon} {event['event_type'].replace('_', ' ').title()}", expanded=(i==0)):
                    st.write(f"**Actor:** {event['actor']}")
                    st.write(f"**Time:** {str(event['timestamp'])[:19].replace('T', ' ')}")
                    if event.get('details'):
                        st.markdown("**Details:**")
                        for k, v in event['details'].items():
                            st.write(f"- _{k.replace('_', ' ').capitalize()}_: {v}")
