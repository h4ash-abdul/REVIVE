import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pandas as pd

from src.domain.models import (
    Mandate, MandateStatus, PaymentAttempt, AttemptStatus, CandidateAction, ActionType
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
        # We just return a dummy FeatureVector
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
            raw_network_return_code="R01",
            prediction_mode="UNKNOWN"
        )

class MockHierarchicalPredictor:
    def predict(self, feature_vectors):
        predictions = []
        for fv in feature_vectors:
            # Fake deterministic probability based on candidate hour for testing ranking
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
def history(mandate, current_time):
    return [
        PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=mandate.mandate_id,
            timestamp=current_time - timedelta(days=1),
            amount=100.0,
            status=AttemptStatus.FAILED,
            network_return_code="ERR_INSUFFICIENT_FUNDS"
        )
    ]

def test_generator_bounds(mandate, current_time):
    generator = CandidateGenerator(days_ahead=2, hours_of_day=[9, 14, 20])
    candidates = generator.generate(mandate, current_time)
    
    # current_time is 10:00. Today's 9:00 is in the past! It must be excluded.
    # Expected: Today 14:00, 20:00. Tomorrow 9:00, 14:00, 20:00. Next day 9:00, 14:00, 20:00. (8 candidates total)
    assert len(candidates) == 8
    
    for c in candidates:
        assert c.scheduled_time > current_time
        assert c.action_type == ActionType.PAYMENT_RETRY

def test_copilot_scheduler_selection(mandate, history, current_time):
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
    
    copilot = CopilotStrategy(engine, generator, scorer, classifier)
    
    result = copilot.evaluate(mandate, history, [mandate], current_time)
    
    # History has failure at 10:00 yesterday (24 hrs ago).
    # Current time is 10:00 today.
    # Candidates today: 14:00, 20:00. (both valid since > 24h since last failure)
    # 14:00 gives prob=0.8. 20:00 gives prob=0.4.
    # Tomorrow gives 9:00 (prob=0.6). But wait, policy limits to one attempt if they are spaced by 24h.
    # Pre-filter will only allow 14:00 today and reject the rest? 
    # Wait, DeterministicPolicyEngine pre_filter loops through candidates and sequentially checks spacing.
    # If 14:00 today is allowed, then 20:00 today is rejected (<24h). 9:00 tomorrow is rejected (19h). 14:00 tomorrow is allowed!
    # So valid candidates might be 14:00 today, 14:00 tomorrow, 14:00 next day.
    # All of these have hour=14 -> prob=0.8.
    
    assert result.selected_action is not None
    # Highest prob is 0.8 which comes from 14:00 hour.
    assert result.selected_action.scheduled_time.hour == 14
    
    # Ensure trace contains policy info
    assert len(result.policy_decisions) > 0
    assert result.prediction_mode == "merchant"

def test_revoked_mandate(mandate, history, current_time):
    revoked_mandate = Mandate(
        mandate_id=mandate.mandate_id,
        customer_id=mandate.customer_id,
        merchant_id=mandate.merchant_id,
        amount=mandate.amount,
        status=MandateStatus.REVOKED,
        created_at=mandate.created_at,
        expires_at=None
    )
    
    policy_config = PolicyConfig(
        policy_version="v1.0",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    copilot = CopilotStrategy(
        DeterministicPolicyEngine(policy_config),
        CandidateGenerator(),
        CandidateScoringService(MockFeatureBuilder(), MockHierarchicalPredictor()),
        RuleBasedFailureClassifier()
    )
    
    result = copilot.evaluate(revoked_mandate, history, [revoked_mandate], current_time)
    
    # Must stop entirely
    assert result.selected_action is None
    assert "No policy-compliant" in result.stopping_reason or "not retryable" in result.stopping_reason or "Mandate is not ACTIVE" in result.stopping_reason
    
def test_ambiguous_failure(mandate, current_time):
    history = [
        PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=mandate.mandate_id,
            timestamp=current_time - timedelta(days=1),
            amount=100.0,
            status=AttemptStatus.FAILED,
            network_return_code="UNKNOWN_WEIRD_ERROR_999" # Not recognized, so ambiguous
        )
    ]
    
    policy_config = PolicyConfig(
        policy_version="v1.0",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    copilot = CopilotStrategy(
        DeterministicPolicyEngine(policy_config),
        CandidateGenerator(),
        CandidateScoringService(MockFeatureBuilder(), MockHierarchicalPredictor()),
        RuleBasedFailureClassifier()
    )
    
    result = copilot.evaluate(mandate, history, [mandate], current_time)
    
    assert result.selected_action is None
    assert "not retryable" in result.stopping_reason
