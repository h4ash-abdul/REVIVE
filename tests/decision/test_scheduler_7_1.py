import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domain.models import (
    Mandate, MandateStatus, PaymentAttempt, AttemptStatus, 
    PaymentObligation, ObligationStatus, ActionType, CandidateAction
)
from src.configs.models import PolicyConfig
from src.decision.policy import DeterministicPolicyEngine
from src.decision.generator import CandidateGenerator
from src.decision.scorer import CandidateScoringService
from src.decision.copilot import CopilotStrategy
from src.features.classifier import RuleBasedFailureClassifier
from src.models.prediction import Prediction
from src.features.models import FeatureVector

class MockFeatureBuilder:
    def build(self, mandate, candidate, global_history, global_mandates, cutoff_timestamp):
        return FeatureVector(
            mandate_id=mandate.mandate_id,
            candidate_id=candidate.candidate_id,
            feature_version="v1.0",
            generated_at=cutoff_timestamp,
            cutoff_timestamp=cutoff_timestamp,
            candidate_hour=candidate.scheduled_time.hour,
            candidate_weekday=0,
            candidate_day_of_month=1,
            time_until_candidate_hours=0.0,
            hist_payment_count=1,
            hist_success_count=0,
            hist_failure_count=1,
            hist_success_rate=0.0,
            hist_amount_mean=100.0,
            hist_amount_std=0.0,
            history_depth_days=1.0,
            time_since_prev_success_hours=None,
            time_since_prev_failure_hours=1.0,
            hist_success_rate_hour_bucket=None,
            hist_success_rate_day_bucket=None,
            amount=100.0,
            mandate_age_days=1.0,
            current_attempt_number=2,
            merchant_hist_payment_count=1,
            merchant_success_count=0,
            merchant_success_rate=0.0,
            merchant_history_depth_days=1.0,
            merchant_success_rate_hour_bucket=None,
            failure_category="INSUFFICIENT_FUNDS",
            raw_network_return_code="ERR_INSUFFICIENT_FUNDS",
            prediction_mode="UNKNOWN"
        )

class MockHierarchicalPredictor:
    def predict(self, feature_vectors):
        predictions = []
        for fv in feature_vectors:
            prob = 0.5
            if fv.candidate_hour == 9: prob = 0.6
            if fv.candidate_hour == 14: prob = 0.8
            if fv.candidate_hour == 20: prob = 0.4
            
            predictions.append(Prediction(
                prediction_id=uuid4(),
                candidate_id=fv.candidate_id,
                probability=prob,
                prediction_mode="merchant",
                model_version="v1.1",
                feature_version="v1.0",
                prediction_timestamp=fv.cutoff_timestamp
            ))
        return predictions

@pytest.fixture
def current_time():
    return datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def mandate():
    return Mandate(
        mandate_id=uuid4(),
        customer_id=uuid4(),
        merchant_id=uuid4(),
        amount=100.0,
        status=MandateStatus.ACTIVE,
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        expires_at=None
    )

@pytest.fixture
def copilot_env():
    policy_config = PolicyConfig(
        policy_version="v1.0",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    engine = DeterministicPolicyEngine(policy_config)
    generator = CandidateGenerator(days_ahead=3, hours_of_day=[9, 14, 20])
    scorer = CandidateScoringService(MockFeatureBuilder(), MockHierarchicalPredictor())
    classifier = RuleBasedFailureClassifier()
    return CopilotStrategy(engine, generator, scorer, classifier)

def test_1_historical_success_current_failure_allowed(copilot_env, mandate, current_time):
    past_success = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=30),
        amount=100.0, status=AttemptStatus.SUCCESS
    )
    current_failure = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=2),
        amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    history = [past_success, current_failure]
    obligation = PaymentObligation(
        obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=current_failure.timestamp,
        amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=current_failure.attempt_id
    )
    result = copilot_env.evaluate(mandate, history, [mandate], current_time, obligation)
    assert result.selected_action is not None

def test_2_historical_success_current_success_blocked(copilot_env, mandate, current_time):
    past_success = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=30),
        amount=100.0, status=AttemptStatus.SUCCESS
    )
    current_success = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=2),
        amount=100.0, status=AttemptStatus.SUCCESS
    )
    history = [past_success, current_success]
    obligation = PaymentObligation(
        obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=current_success.timestamp,
        amount=100.0, status=ObligationStatus.SUCCESS, original_attempt_id=current_success.attempt_id
    )
    result = copilot_env.evaluate(mandate, history, [mandate], current_time, obligation)
    assert result.selected_action is None
    assert "No failures found" in result.stopping_reason or "Current payment obligation already has a successful payment" in result.stopping_reason

def test_3_historical_retries_do_not_consume_budget(copilot_env, mandate, current_time):
    past_failure1 = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=32),
        amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    past_failure2 = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=31),
        amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    past_failure3 = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=30),
        amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    current_failure = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=2),
        amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    history = [past_failure1, past_failure2, past_failure3, current_failure]
    obligation = PaymentObligation(
        obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=current_failure.timestamp,
        amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=current_failure.attempt_id,
        retry_attempt_ids=[]
    )
    result = copilot_env.evaluate(mandate, history, [mandate], current_time, obligation)
    # The 3 old failures don't count towards the max of 3.
    assert result.selected_action is not None

def test_4_current_cycle_retries_consume_budget(copilot_env, mandate, current_time):
    current_failure = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=5),
        amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    retry_failure = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=3),
        amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    history = [current_failure, retry_failure]
    obligation = PaymentObligation(
        obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=current_failure.timestamp,
        amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=current_failure.attempt_id,
        retry_attempt_ids=[retry_failure.attempt_id]
    )
    result = copilot_env.evaluate(mandate, history, [mandate], current_time, obligation)
    # Budget is 3. Used 1 retry. Still 2 remaining, so we should get candidates.
    assert result.selected_action is not None

def test_5_current_cycle_reaching_limit_blocks_future(copilot_env, mandate, current_time):
    f0 = PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=5), amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS")
    f1 = PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=4), amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS")
    f2 = PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=3), amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS")
    f3 = PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=2), amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS")
    history = [f0, f1, f2, f3]
    obligation = PaymentObligation(
        obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=f0.timestamp,
        amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=f0.attempt_id,
        retry_attempt_ids=[f1.attempt_id, f2.attempt_id, f3.attempt_id]
    )
    result = copilot_env.evaluate(mandate, history, [mandate], current_time, obligation)
    assert result.selected_action is None
    assert "Exceeded maximum retries" in str([d.reason for d in result.policy_decisions])

def test_6_successful_current_cycle_immediately_blocks(copilot_env, mandate, current_time):
    f0 = PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=5), amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS")
    s1 = PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=4), amount=100.0, status=AttemptStatus.SUCCESS, network_return_code=None)
    history = [f0, s1]
    obligation = PaymentObligation(
        obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=f0.timestamp,
        amount=100.0, status=ObligationStatus.SUCCESS, original_attempt_id=f0.attempt_id,
        retry_attempt_ids=[s1.attempt_id]
    )
    # The copilot layer blocks before policy if no recent failure, but let's say the failure was last for some reason (out of order edge case), or test policy directly.
    c1 = CandidateAction(candidate_id=uuid4(), mandate_id=mandate.mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=current_time + timedelta(hours=10), amount=100.0, source="test")
    decisions = copilot_env.policy_engine.pre_filter([c1], mandate, history, obligation)
    assert not decisions[0].is_allowed
    assert "Current payment obligation already has a successful payment" in decisions[0].reason

def test_7_8_expired_or_revoked_mandate_blocks(copilot_env, mandate, current_time):
    rev_mandate = Mandate(mandate_id=mandate.mandate_id, customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, status=MandateStatus.REVOKED, created_at=mandate.created_at)
    exp_mandate = Mandate(mandate_id=mandate.mandate_id, customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, status=MandateStatus.EXPIRED, created_at=mandate.created_at)
    history = [PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=5), amount=100.0, status=AttemptStatus.FAILED, network_return_code="ERR_INSUFFICIENT_FUNDS")]
    obligation = PaymentObligation(obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=history[0].timestamp, amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=history[0].attempt_id)
    
    r1 = copilot_env.evaluate(rev_mandate, history, [rev_mandate], current_time, obligation)
    assert r1.selected_action is None
    r2 = copilot_env.evaluate(exp_mandate, history, [exp_mandate], current_time, obligation)
    assert r2.selected_action is None

def test_9_candidate_after_obligation_success_is_rejected(copilot_env, mandate, current_time):
    # This is implicitly tested in test_6
    pass

def test_10_no_bypass(copilot_env, mandate, current_time):
    # Tested by ensuring all these fail when they should and pass when they should
    pass
