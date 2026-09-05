import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.decision.sequential_planner import SequentialPlannerStrategy
from src.decision.policy import DeterministicPolicyEngine
from src.configs.models import PolicyConfig
from src.domain.models import Mandate, PaymentAttempt, AttemptStatus, PaymentObligation, ObligationStatus, CandidateAction, ActionType
from src.domain.models import Prediction, PredictionMode

class MockScorer:
    def score_candidates(self, candidates, mandate, history, global_mandates, current_time):
        preds = {}
        for c in candidates:
            # Fake logic: afternoon has higher probability
            prob = 0.3
            if c.scheduled_time.hour >= 15:
                prob = 0.6
            preds[c.candidate_id] = Prediction(prediction_id=uuid4(), model_version="1.0", feature_version="1.0", mandate_id=mandate.mandate_id, candidate_id=c.candidate_id, probability=prob, prediction_mode=PredictionMode.CUSTOMER)
        return preds

def test_planner_constraints():
    policy = DeterministicPolicyEngine(PolicyConfig(policy_version="1.0", max_retries_per_mandate=3, min_hours_between_retries=24, allowed_execution_windows_utc=["00:00-23:59"], stop_on_success=True))
    scorer = MockScorer()
    planner = SequentialPlannerStrategy(policy, scorer)
    
    mandate = Mandate(mandate_id=uuid4(), customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, currency="INR", created_at=datetime.now(timezone.utc), is_active=True, status="active")
    current_time = datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    history = [PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=current_time - timedelta(days=1), amount=100.0, status=AttemptStatus.FAILED, network_return_code="insufficient_funds")]
    obligation = PaymentObligation(obligation_id=uuid4(), mandate_id=mandate.mandate_id, due_time=history[0].timestamp, amount=100.0, status=ObligationStatus.ACTIVE_RECOVERY, original_attempt_id=history[0].attempt_id, retry_attempt_ids=[])
    
    cands = planner.generator.generate(mandate, current_time)
    decisions = policy.pre_filter(cands, mandate, history, obligation)
    valid_cands = [next(c for c in cands if c.candidate_id == d.candidate_id) for d in decisions if d.is_allowed]
    
    res = planner.evaluate(mandate, history, current_time, obligation, valid_cands)
    
    assert res.selected_action is not None
    assert res.explanation.startswith("Planned sequence with EV")
    
    # Test exhausted budget
    obligation = obligation.model_copy(update={"retry_attempt_ids": [uuid4(), uuid4(), uuid4()]})
    res2 = planner.evaluate(mandate, history, current_time, obligation, valid_cands)
    assert res2.selected_action is None
    assert res2.stopping_reason == "budget_exhausted"
