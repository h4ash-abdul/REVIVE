import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from src.domain.models import (
    Mandate,
    MandateStatus,
    CandidateAction,
    ActionType,
    Prediction,
    PredictionMode,
    AuditEvent,
    EventType,
)

def test_mandate_validation():
    # Valid mandate
    mandate = Mandate(
        mandate_id=uuid4(),
        customer_id=uuid4(),
        merchant_id=uuid4(),
        amount=100.50,
        status=MandateStatus.ACTIVE,
        created_at=datetime.now(timezone.utc)
    )
    assert mandate.amount == 100.50

    # Invalid amount
    with pytest.raises(ValidationError):
        Mandate(
            mandate_id=uuid4(),
            customer_id=uuid4(),
            merchant_id=uuid4(),
            amount=-10.0,  # Negative amount should fail gt=0 validation
            status=MandateStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )

def test_prediction_validation():
    candidate_id = uuid4()
    
    prediction = Prediction(
        prediction_id=uuid4(),
        candidate_id=candidate_id,
        probability=0.85,
        prediction_mode=PredictionMode.CUSTOMER,
        model_version="v1.0",
        feature_version="f1.2"
    )
    assert prediction.probability == 0.85
    assert prediction.prediction_mode == "customer"
    
    # Invalid probability
    with pytest.raises(ValidationError):
        Prediction(
            prediction_id=uuid4(),
            candidate_id=candidate_id,
            probability=1.5,  # Should fail le=1.0 validation
            prediction_mode=PredictionMode.CUSTOMER,
            model_version="v1.0",
            feature_version="f1.2"
        )

def test_audit_event_immutability():
    event = AuditEvent(
        event_id=uuid4(),
        correlation_id=uuid4(),
        mandate_id=uuid4(),
        customer_id=uuid4(),
        event_type=EventType.CANDIDATES_GENERATED,
        sequence_number=1,
        payload={"key": "value"}
    )
    
    with pytest.raises(ValidationError):
        # Should be frozen
        event.sequence_number = 2

def test_candidate_action_requires_mandate_id():
    # Ensures mandate_id is required
    with pytest.raises(ValidationError):
        CandidateAction(
            candidate_id=uuid4(),
            action_type=ActionType.PAYMENT_RETRY,
            scheduled_time=datetime.now(timezone.utc),
            amount=100.0,
            source="scheduler"
        )
