import pytest
from src.domain.models import StrategyResult, PredictionMode
from scripts.run_business_value import NoRecoveryStrategy

def test_no_recovery_strategy_does_not_mutate():
    from src.domain.models import Mandate, MandateStatus
    from uuid import uuid4
    from datetime import datetime, timezone
    
    mandate = Mandate(mandate_id=uuid4(), customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, status=MandateStatus.ACTIVE, created_at=datetime.now(timezone.utc))
    strat = NoRecoveryStrategy()
    res = strat.evaluate(mandate, [], datetime.now(timezone.utc))
    
    assert res.selected_action is None
    assert len(res.retry_plan) == 0

