import pytest
import random
from uuid import uuid4
from datetime import datetime, timezone

from src.domain.models import Mandate, PaymentObligation, CandidateAction, PolicyDecision, PaymentAttempt, AttemptStatus, ObligationStatus
from src.domain.audit import ExecutionStatus, RecoveryEventType, ExecutionRecord
from src.execution.adapter import SimulatedExecutionAdapter, OutcomeVerifier, PolicyViolationError
from src.audit.trail import AuditLogger
from src.simulation.outcome_engine.engine import OutcomeEngine

def test_execution_adapter_enforces_policy():
    mandate = Mandate(mandate_id=uuid4(), customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, currency="INR", created_at=datetime.now(timezone.utc), is_active=True, status="active")
    obligation = PaymentObligation(obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=datetime.now(timezone.utc), amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=uuid4(), retry_attempt_ids=[])
    
    action = CandidateAction(candidate_id=uuid4(), mandate_id=mandate.mandate_id, action_type="payment_retry", scheduled_time=datetime.now(timezone.utc), amount=100.0, source="test")
    
    # 1. Matching ID but rejected
    decision = PolicyDecision(decision_id=uuid4(), candidate_id=action.candidate_id, policy_version="1", checkpoint="final_validation", is_allowed=False, reason="Too soon")
    engine = OutcomeEngine(random.Random(42))
    adapter = SimulatedExecutionAdapter(engine)
    
    from src.simulation.latent.models import CustomerLatentState, MerchantLatentState, Archetype
    c_lat = CustomerLatentState(customer_id=mandate.customer_id, archetype=Archetype.SALARY_CYCLE_REGULAR, primary_income_day=1, time_of_day_preference=10, true_payday_offset=0, base_liquidity_probability=0.5, drift_level="moderate", timing_noise_std_dev=1.0, base_success_rate=0.5, technical_failure_propensity=0.1, price_sensitivity=1.0)
    m_lat = MerchantLatentState(merchant_id=mandate.merchant_id, category="sub", expected_ticket_size=100.0, base_success_rate=0.5, technical_failure_propensity=0.1, industry_risk_modifier=1.0, avg_mandate_amount=100.0, historical_retry_schedule=[])
    
    record, simulated = adapter.execute(action, decision, obligation, mandate, c_lat, m_lat, datetime.now(timezone.utc))
    assert record.status == ExecutionStatus.REJECTED
    assert simulated is None
    
    # 2. Action ID mismatch
    decision2 = PolicyDecision(decision_id=uuid4(), candidate_id=uuid4(), policy_version="1", checkpoint="final_validation", is_allowed=True, reason="OK")
    with pytest.raises(PolicyViolationError):
        adapter.execute(action, decision2, obligation, mandate, c_lat, m_lat, datetime.now(timezone.utc))
        
    # 3. Success
    decision3 = PolicyDecision(decision_id=uuid4(), candidate_id=action.candidate_id, policy_version="1", checkpoint="final_validation", is_allowed=True, reason="OK")
    record3, simulated3 = adapter.execute(action, decision3, obligation, mandate, c_lat, m_lat, datetime.now(timezone.utc))
    assert record3.status == ExecutionStatus.COMPLETED
    assert simulated3 is not None
    assert record3.simulated_attempt_id == simulated3.attempt_id

def test_outcome_verifier():
    mandate = Mandate(mandate_id=uuid4(), customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, currency="INR", created_at=datetime.now(timezone.utc), is_active=True, status="active")
    obligation = PaymentObligation(obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=datetime.now(timezone.utc), amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=uuid4(), retry_attempt_ids=[])
    
    record = ExecutionRecord(execution_id=uuid4(), mandate_id=mandate.mandate_id, obligation_id=obligation.obligation_id, action_id=uuid4(), requested_at=datetime.now(timezone.utc), executed_at=datetime.now(timezone.utc), status=ExecutionStatus.COMPLETED, failure_reason=None, simulated_attempt_id=uuid4())
    simulated_attempt = PaymentAttempt(attempt_id=record.simulated_attempt_id, mandate_id=mandate.mandate_id, timestamp=datetime.now(timezone.utc), amount=100.0, status=AttemptStatus.SUCCESS, network_return_code="approved")
    
    verifier = OutcomeVerifier()
    outcome = verifier.verify(record, simulated_attempt, datetime.now(timezone.utc))
    
    assert outcome.success is True
    assert outcome.recovered_amount == 100.0
    assert outcome.obligation_id == obligation.obligation_id

def test_audit_logger():
    logger = AuditLogger()
    m_id = uuid4()
    o_id = uuid4()
    
    logger.log(m_id, o_id, RecoveryEventType.PAYMENT_FAILED, "system", datetime(2025,1,1,10, tzinfo=timezone.utc), {"reason": "funds"})
    logger.log(m_id, o_id, RecoveryEventType.POLICY_PRECHECK, "policy", datetime(2025,1,1,11, tzinfo=timezone.utc), {"passed": True})
    
    events = logger.get_events(m_id, o_id)
    assert len(events) == 2
    assert events[0].event_type == RecoveryEventType.PAYMENT_FAILED
    assert events[1].event_type == RecoveryEventType.POLICY_PRECHECK
    
    events2 = logger.get_events(uuid4(), o_id)
    assert len(events2) == 0
