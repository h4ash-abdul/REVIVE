import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domain.models import Mandate, MandateStatus, PaymentAttempt, AttemptStatus, CandidateAction, ActionType
from src.features.builder import PointInTimeFeatureBuilder

@pytest.fixture
def base_data():
    m_id = uuid4()
    cust_id = uuid4()
    merch_id = uuid4()
    
    mandate = Mandate(
        mandate_id=m_id,
        customer_id=cust_id,
        merchant_id=merch_id,
        amount=100.0,
        status=MandateStatus.ACTIVE,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )
    
    t1 = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    fail_attempt = PaymentAttempt(
        attempt_id=uuid4(),
        mandate_id=m_id,
        timestamp=t1,
        amount=100.0,
        status=AttemptStatus.FAILED,
        network_return_code="CODE_116_BAL"
    )
    
    return mandate, [fail_attempt], t1

def test_leakage_future_success(base_data):
    mandate, history, t1 = base_data
    builder = PointInTimeFeatureBuilder()
    
    cutoff = t1 + timedelta(seconds=1)
    candidate = CandidateAction(candidate_id=uuid4(), mandate_id=mandate.mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=cutoff + timedelta(hours=24), amount=100.0, source="test")
    
    vec_before = builder.build(mandate, candidate, history, [mandate], cutoff)
    
    # Add future success
    future_success = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=cutoff + timedelta(hours=1), amount=100.0, status=AttemptStatus.SUCCESS
    )
    history_with_future = history + [future_success]
    
    vec_after = builder.build(mandate, candidate, history_with_future, [mandate], cutoff)
    
    assert vec_before.hist_success_count == vec_after.hist_success_count
    assert vec_before.hist_payment_count == vec_after.hist_payment_count
    assert vec_before.model_dump(exclude={'generated_at'}) == vec_after.model_dump(exclude={'generated_at'})

def test_leakage_future_failures(base_data):
    mandate, history, t1 = base_data
    builder = PointInTimeFeatureBuilder()
    
    cutoff = t1 + timedelta(seconds=1)
    candidate = CandidateAction(candidate_id=uuid4(), mandate_id=mandate.mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=cutoff + timedelta(hours=24), amount=100.0, source="test")
    
    vec_before = builder.build(mandate, candidate, history, [mandate], cutoff)
    
    # Add future failure
    future_fail = PaymentAttempt(
        attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=cutoff + timedelta(hours=1), amount=100.0, status=AttemptStatus.FAILED
    )
    
    vec_after = builder.build(mandate, candidate, history + [future_fail], [mandate], cutoff)
    assert vec_before.hist_failure_count == vec_after.hist_failure_count
    assert vec_before.model_dump(exclude={'generated_at'}) == vec_after.model_dump(exclude={'generated_at'})

def test_leakage_remove_future_events(base_data):
    mandate, history, t1 = base_data
    builder = PointInTimeFeatureBuilder()
    
    cutoff = t1 + timedelta(seconds=1)
    candidate = CandidateAction(candidate_id=uuid4(), mandate_id=mandate.mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=cutoff + timedelta(hours=24), amount=100.0, source="test")
    
    future_fail = PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=cutoff + timedelta(hours=1), amount=100.0, status=AttemptStatus.FAILED)
    
    vec_with_future = builder.build(mandate, candidate, history + [future_fail], [mandate], cutoff)
    vec_without_future = builder.build(mandate, candidate, history, [mandate], cutoff)
    
    assert vec_with_future.model_dump(exclude={'generated_at'}) == vec_without_future.model_dump(exclude={'generated_at'})

def test_architecture_no_latent_imports():
    import ast
    import os
    
    features_dir = "src/features"
    for root, _, files in os.walk(features_dir):
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), 'r') as f:
                    tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            assert "latent" not in node.module, f"Latent state leaked in {file}"

def test_historical_aggregates_before_cutoff(base_data):
    mandate, history, t1 = base_data
    builder = PointInTimeFeatureBuilder()
    
    # The history has one failure at t1 (12:00)
    cutoff = t1
    candidate = CandidateAction(candidate_id=uuid4(), mandate_id=mandate.mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=cutoff + timedelta(hours=24), amount=100.0, source="test")
    
    # If cutoff is EXACTLY t1, the event at t1 must NOT be included in history (strictly earlier rule)
    vec = builder.build(mandate, candidate, history, [mandate], cutoff)
    
    assert vec.hist_payment_count == 0
    assert vec.hist_failure_count == 0
    
    # If cutoff is t1 + 1s, it should be included
    cutoff2 = t1 + timedelta(seconds=1)
    vec2 = builder.build(mandate, candidate, history, [mandate], cutoff2)
    
    assert vec2.hist_payment_count == 1
    assert vec2.hist_failure_count == 1
