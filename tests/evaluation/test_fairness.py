import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.models import CandidateAction, ActionType, Mandate, MandateStatus
from src.decision.baselines import SmartHistoricalHeuristicStrategy
from src.decision.ml_strategies import MLProbabilityStrategy, MLExpectedValueStrategy
from src.configs.models import PolicyConfig
from src.decision.policy import DeterministicPolicyEngine

@pytest.fixture
def policy_engine():
    cfg = PolicyConfig(
        policy_version="v1",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    return DeterministicPolicyEngine(cfg)

@pytest.fixture
def mock_candidates():
    mandate_id = uuid4()
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 1, 3, 14, 0, tzinfo=timezone.utc)
    return mandate_id, [
        CandidateAction(candidate_id=uuid4(), mandate_id=mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=t1, amount=100.0, source="generator"),
        CandidateAction(candidate_id=uuid4(), mandate_id=mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=t2, amount=100.0, source="generator"),
        CandidateAction(candidate_id=uuid4(), mandate_id=mandate_id, action_type=ActionType.PAYMENT_RETRY, scheduled_time=t3, amount=100.0, source="generator"),
    ]

class DummyScorer:
    def score_candidate(self, candidate, mandate, history, current_time):
        from src.domain.models import Prediction, PredictionMode
        # Score based on candidate time
        h = candidate.scheduled_time.hour
        return Prediction(
            prediction_id=uuid4(),
            candidate_id=candidate.candidate_id,
            probability=float(h)/24.0,
            prediction_mode=PredictionMode.DEFAULT,
            model_version="dummy",
            feature_version="v1"
        )
        
    def score_candidates(self, candidates, mandate, history, global_mandates, current_time):
        return {c.candidate_id: self.score_candidate(c, mandate, history, current_time) for c in candidates}


def test_smart_heuristic_snaps_to_universe(policy_engine, mock_candidates):
    mandate_id, candidates = mock_candidates
    mandate = Mandate(mandate_id=mandate_id, customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, status=MandateStatus.ACTIVE, created_at=datetime(2025,1,1, tzinfo=timezone.utc))
    
    # Empty history -> best_hour = 12
    strat = SmartHistoricalHeuristicStrategy(policy_engine, global_history=[])
    
    res = strat.evaluate(mandate, [], datetime(2026, 1, 1, tzinfo=timezone.utc), None, candidates)
    
    # Should snap to t2 which is at 12:00
    assert res.selected_action is not None
    assert res.selected_action.candidate_id == candidates[1].candidate_id
    assert res.selected_action.scheduled_time.hour == 12

def test_ml_prob_selects_from_universe(policy_engine, mock_candidates):
    mandate_id, candidates = mock_candidates
    mandate = Mandate(mandate_id=mandate_id, customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, status=MandateStatus.ACTIVE, created_at=datetime(2025,1,1, tzinfo=timezone.utc))
    
    strat = MLProbabilityStrategy(policy_engine, DummyScorer())
    res = strat.evaluate(mandate, [], datetime(2026, 1, 1, tzinfo=timezone.utc), None, candidates)
    
    # Highest score is t3 (14:00 -> 1.4)
    assert res.selected_action is not None
    assert res.selected_action.candidate_id == candidates[2].candidate_id

def test_ml_ev_selects_from_universe(policy_engine, mock_candidates):
    mandate_id, candidates = mock_candidates
    mandate = Mandate(mandate_id=mandate_id, customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, status=MandateStatus.ACTIVE, created_at=datetime(2025,1,1, tzinfo=timezone.utc))
    
    strat = MLExpectedValueStrategy(policy_engine, DummyScorer(), action_cost=5.0)
    res = strat.evaluate(mandate, [], datetime(2026, 1, 1, tzinfo=timezone.utc), None, candidates)
    
    # Highest score is t3
    assert res.selected_action is not None
    assert res.selected_action.candidate_id == candidates[2].candidate_id
    assert res.selected_action.scheduled_time.hour == 14

def test_strategy_fails_without_universe(policy_engine, mock_candidates):
    mandate_id, _ = mock_candidates
    mandate = Mandate(mandate_id=mandate_id, customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, status=MandateStatus.ACTIVE, created_at=datetime(2025,1,1, tzinfo=timezone.utc))
    strat = MLProbabilityStrategy(policy_engine, DummyScorer())
    with pytest.raises(ValueError, match="requires a pre-generated candidate universe"):
        strat.evaluate(mandate, [], datetime(2026, 1, 1, tzinfo=timezone.utc), None, None)
