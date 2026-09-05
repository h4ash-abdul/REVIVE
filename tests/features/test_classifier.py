import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.models import (
    PaymentAttempt, Mandate, MandateStatus, AttemptStatus,
    FailureCategory, ConfidenceLevel
)
from src.features.classifier import RuleBasedFailureClassifier

@pytest.fixture
def classifier():
    return RuleBasedFailureClassifier()

@pytest.fixture
def base_mandate():
    return Mandate(
        mandate_id=uuid4(),
        customer_id=uuid4(),
        merchant_id=uuid4(),
        amount=100.0,
        status=MandateStatus.ACTIVE,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        expires_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )

@pytest.fixture
def base_attempt(base_mandate):
    return PaymentAttempt(
        attempt_id=uuid4(),
        mandate_id=base_mandate.mandate_id,
        timestamp=datetime(2025, 2, 1, tzinfo=timezone.utc),
        amount=100.0,
        status=AttemptStatus.FAILED,
        network_return_code="ERR_INSUFFICIENT_FUNDS"
    )

def test_nsf_classification(classifier, base_attempt, base_mandate):
    res = classifier.classify(base_attempt, base_mandate)
    assert res.category == FailureCategory.INSUFFICIENT_FUNDS
    assert res.retryable is True
    assert res.confidence == ConfidenceLevel.HIGH

def test_tech_classification(classifier, base_attempt, base_mandate):
    attempt = base_attempt.model_copy(update={"network_return_code": "ERR_GATEWAY"})
    res = classifier.classify(attempt, base_mandate)
    assert res.category == FailureCategory.TECHNICAL_FAILURE
    assert res.retryable is True
    assert res.confidence == ConfidenceLevel.HIGH

def test_risk_classification(classifier, base_attempt, base_mandate):
    attempt = base_attempt.model_copy(update={"network_return_code": "POLICY_DECLINE_102"})
    res = classifier.classify(attempt, base_mandate)
    assert res.category == FailureCategory.RISK_OR_POLICY_DECLINE
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.HIGH

def test_ambiguous_classification(classifier, base_attempt, base_mandate):
    attempt = base_attempt.model_copy(update={"network_return_code": "E0099_UNKNOWN"})
    res = classifier.classify(attempt, base_mandate)
    assert res.category == FailureCategory.UNKNOWN_OR_AMBIGUOUS
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.MEDIUM

def test_unknown_unmapped_code(classifier, base_attempt, base_mandate):
    attempt = base_attempt.model_copy(update={"network_return_code": "WEIRD_BANK_ERROR"})
    res = classifier.classify(attempt, base_mandate)
    assert res.category == FailureCategory.UNKNOWN_OR_AMBIGUOUS
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.LOW

def test_missing_return_code(classifier, base_attempt, base_mandate):
    attempt = base_attempt.model_copy(update={"network_return_code": None})
    res = classifier.classify(attempt, base_mandate)
    assert res.category == FailureCategory.UNKNOWN_OR_AMBIGUOUS
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.LOW

def test_mandate_revoked(classifier, base_attempt, base_mandate):
    mandate = base_mandate.model_copy(update={"status": MandateStatus.REVOKED})
    # Even with an NSF code, mandate status takes precedence
    res = classifier.classify(base_attempt, mandate)
    assert res.category == FailureCategory.MANDATE_EXPIRED_OR_REVOKED
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.HIGH

def test_mandate_expired(classifier, base_attempt, base_mandate):
    mandate = base_mandate.model_copy(update={"status": MandateStatus.EXPIRED})
    res = classifier.classify(base_attempt, mandate)
    assert res.category == FailureCategory.MANDATE_EXPIRED_OR_REVOKED
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.HIGH

def test_inconsistent_state(classifier, base_attempt, base_mandate):
    # Attempt has different mandate_id than the mandate provided
    attempt = base_attempt.model_copy(update={"mandate_id": uuid4()})
    res = classifier.classify(attempt, base_mandate)
    assert res.category == FailureCategory.UNKNOWN_OR_AMBIGUOUS
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.HIGH
    assert "Inconsistent state" in res.reason

def test_successful_attempt_fallback(classifier, base_attempt, base_mandate):
    attempt = base_attempt.model_copy(update={"status": AttemptStatus.SUCCESS})
    res = classifier.classify(attempt, base_mandate)
    assert res.category == FailureCategory.UNKNOWN_OR_AMBIGUOUS
    assert res.retryable is False
    assert res.confidence == ConfidenceLevel.LOW

def test_deterministic_identical_input(classifier, base_attempt, base_mandate):
    res1 = classifier.classify(base_attempt, base_mandate)
    res2 = classifier.classify(base_attempt, base_mandate)
    assert res1.category == res2.category
    assert res1.retryable == res2.retryable
    assert res1.confidence == res2.confidence
