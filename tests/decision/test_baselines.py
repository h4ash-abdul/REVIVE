import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domain.models import (
    PolicyCheckpoint,
    Mandate, MandateStatus, PaymentAttempt, AttemptStatus, PredictionMode,
    PaymentObligation, ObligationStatus
)
from src.configs.models import PolicyConfig
from src.decision.policy import DeterministicPolicyEngine
from src.decision.baselines import (
    ImmediateRetryStrategy,
    FixedScheduleStrategy,
    SmartHistoricalHeuristicStrategy
)

@pytest.fixture
def policy_config():
    return PolicyConfig(
        policy_version="v1",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )

@pytest.fixture
def policy_engine(policy_config):
    return DeterministicPolicyEngine(policy_config)

@pytest.fixture
def mandate():
    return Mandate(
        mandate_id=uuid4(),
        customer_id=uuid4(),
        merchant_id=uuid4(),
        amount=100.0,
        status=MandateStatus.ACTIVE,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        expires_at=datetime(2025, 12, 31, tzinfo=timezone.utc)
    )

@pytest.fixture
def current_time():
    return datetime(2025, 2, 1, 12, 0, tzinfo=timezone.utc)


def test_immediate_retry_selects_earliest_valid(policy_engine, mandate, current_time):
    strat = ImmediateRetryStrategy(policy_engine)
    
    # History with a failure 2 hours ago. Policy requires 24h between retries.
    history = [
        PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=mandate.mandate_id,
            timestamp=current_time - timedelta(hours=2),
            amount=100.0,
            status=AttemptStatus.FAILED
        )
    ]
    
    res = strat.evaluate(mandate, history, current_time)
    
    assert len(res.retry_plan) > 0
    # Must schedule at least 24 hours after the last attempt (current_time - 2 + 24 = current_time + 22)
    # The linear search checks offsets from current_time in hours. Offset 22 is exact, so current_time + 22.
    assert res.retry_plan[0].scheduled_time == current_time + timedelta(hours=22)


def test_immediate_retry_stops_on_success(policy_engine, mandate, current_time):
    strat = ImmediateRetryStrategy(policy_engine)
    
    a1 = PaymentAttempt(
        attempt_id=uuid4(),
        mandate_id=mandate.mandate_id,
        timestamp=current_time - timedelta(hours=48),
        amount=100.0,
        status=AttemptStatus.SUCCESS
    )
    history = [a1]
    
    obligation = PaymentObligation(
        obligation_id=uuid4(),
        mandate_id=mandate.mandate_id,
        due_time=current_time - timedelta(hours=48),
        amount=100.0,
        status=ObligationStatus.SUCCESS,
        original_attempt_id=a1.attempt_id
    )
    
    res = strat.evaluate(mandate, history, current_time, obligation)
    
    assert len(res.retry_plan) == 0
    assert "successful payment" in res.stopping_reason


def test_fixed_schedule(policy_engine, mandate, current_time):
    strat = FixedScheduleStrategy(policy_engine, offsets_hours=[12, 48, 72])
    
    # Failure 20 hours ago -> 12h offset from current time is 32h since failure (Valid > 24h)
    history = [
        PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=mandate.mandate_id,
            timestamp=current_time - timedelta(hours=20),
            amount=100.0,
            status=AttemptStatus.FAILED
        )
    ]
    
    res = strat.evaluate(mandate, history, current_time)
    
    assert len(res.retry_plan) == 2 # Budget is 3, 1 used in history, so only 2 slots left
    assert res.retry_plan[0].scheduled_time == current_time + timedelta(hours=12)


def test_fixed_schedule_rejects_invalid(policy_engine, mandate, current_time):
    strat = FixedScheduleStrategy(policy_engine, offsets_hours=[2, 4])
    
    # Failure 2 hours ago. None of the offsets will satisfy the 24h policy.
    history = [
        PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=mandate.mandate_id,
            timestamp=current_time - timedelta(hours=2),
            amount=100.0,
            status=AttemptStatus.FAILED
        )
    ]
    
    res = strat.evaluate(mandate, history, current_time)
    
    assert len(res.retry_plan) == 0
    assert "hours between retries" in res.stopping_reason


def test_smart_heuristic_customer_history(policy_engine, mandate, current_time):
    # Customer has many successes at 10 AM
    history = [
        PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=mandate.mandate_id,
            timestamp=datetime(2025, 1, d, 10, 0, tzinfo=timezone.utc),
            amount=100.0,
            status=AttemptStatus.SUCCESS
        ) for d in range(1, 10)
    ]
    
    strat = SmartHistoricalHeuristicStrategy(policy_engine, global_history=history, min_customer_history=5)
    res = strat.evaluate(mandate, history, current_time)
    
    assert res.prediction_mode == PredictionMode.CUSTOMER
    assert res.selected_action is not None
    assert res.selected_action.scheduled_time.hour == 10
    # verify multi-retry plan (3 steps)
    assert len(res.retry_plan) == 3


def test_smart_heuristic_fallback_merchant(policy_engine, mandate, current_time):
    # NO customer history
    history = []
    
    # Other mandates on the SAME merchant have successes at 14:00
    other_mandate_id = uuid4()
    
    global_hist = []
    for d in range(1, 55):
        attempt = PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=other_mandate_id,
            timestamp=datetime(2025, 1, (d % 27) + 1, 14, 0, tzinfo=timezone.utc),
            amount=100.0,
            status=AttemptStatus.SUCCESS
        )
        # Monkeypatch a hidden `_merchant_id` to mock the backward-compatible test fallback
        object.__setattr__(attempt, '_merchant_id', mandate.merchant_id)
        global_hist.append(attempt)
        
    strat = SmartHistoricalHeuristicStrategy(
        policy_engine, 
        global_history=global_hist, 
        min_customer_history=5, 
        min_merchant_history=50
    )
    res = strat.evaluate(mandate, history, current_time)
    
    assert res.prediction_mode == PredictionMode.MERCHANT
    assert len(res.retry_plan) == 3
    assert res.retry_plan[0].scheduled_time.hour == 14
    assert res.retry_plan[1].scheduled_time.hour == 14


def test_smart_heuristic_fallback_population(policy_engine, mandate, current_time):
    # Customer has NO history
    history = []
    
    # Global population has success at 15:00
    global_hist = [
        PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=uuid4(),
            timestamp=datetime(2025, 1, (d % 27) + 1, 15, 0, tzinfo=timezone.utc),
            amount=100.0,
            status=AttemptStatus.SUCCESS
        ) for d in range(1, 105)
    ]
    
    strat = SmartHistoricalHeuristicStrategy(
        policy_engine, 
        global_history=global_hist, 
        min_customer_history=5, 
        min_merchant_history=50,
        min_population_history=100
    )
    res = strat.evaluate(mandate, history, current_time)
    
    assert res.prediction_mode == PredictionMode.POPULATION
    assert len(res.retry_plan) == 3
    assert res.retry_plan[0].scheduled_time.hour == 15
    
def test_smart_heuristic_fallback_default(policy_engine, mandate, current_time):
    history = []
    global_hist = []
    strat = SmartHistoricalHeuristicStrategy(
        policy_engine, 
        global_history=global_hist, 
        min_customer_history=5, 
        min_merchant_history=50,
        min_population_history=100
    )
    res = strat.evaluate(mandate, history, current_time)
    
    assert res.prediction_mode == PredictionMode.DEFAULT
    assert len(res.retry_plan) == 3
    assert res.retry_plan[0].scheduled_time.hour == 12

def test_revoked_mandate_produces_no_retries(policy_engine, current_time):
    mandate = Mandate(
        mandate_id=uuid4(),
        customer_id=uuid4(),
        merchant_id=uuid4(),
        amount=100.0,
        status=MandateStatus.REVOKED,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    strat = ImmediateRetryStrategy(policy_engine)
    res = strat.evaluate(mandate, [], current_time)
    
    assert len(res.retry_plan) == 0
    assert "revoked" in res.stopping_reason.lower()



def test_final_validate_is_called_in_baselines(policy_engine, mandate, current_time):
    strat = ImmediateRetryStrategy(policy_engine)
    
    history = []
    obligation = PaymentObligation(
        obligation_id=uuid4(),
        mandate_id=mandate.mandate_id,
        due_time=current_time,
        amount=100.0,
        status=ObligationStatus.ACTIVE_RECOVERY,
        original_attempt_id=uuid4()
    )
    
    res = strat.evaluate(mandate, history, current_time, obligation)
    
    assert res.selected_action is not None
    final_decisions = [d for d in res.policy_decisions if d.checkpoint == PolicyCheckpoint.FINAL_VALIDATION]
    assert len(final_decisions) > 0
    assert final_decisions[0].candidate_id == res.selected_action.candidate_id
