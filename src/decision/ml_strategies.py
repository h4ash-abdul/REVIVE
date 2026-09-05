from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from src.domain.models import (
    Mandate, PaymentAttempt, CandidateAction, StrategyResult, PaymentObligation, PredictionMode
)
from src.decision.policy import DeterministicPolicyEngine
from src.decision.scorer import CandidateScoringService
from src.domain.interfaces import RecoveryStrategy

class MLProbabilityStrategy:
    """
    Selects the valid candidate with the highest calibrated P(success).
    """
    def __init__(
        self,
        policy: DeterministicPolicyEngine,
        scorer: CandidateScoringService
    ):
        self.policy = policy
        self.scorer = scorer
        self.version = "v1.1-prob"
        
    def evaluate(self, mandate: Mandate, history: List[PaymentAttempt], current_time: datetime, current_obligation: Optional[PaymentObligation] = None, candidate_universe: Optional[List[CandidateAction]] = None) -> StrategyResult:
        if not candidate_universe:
            raise ValueError("MLProbabilityStrategy requires a pre-generated candidate universe")
            
        # 1. Score all valid candidates
        g_m = getattr(self, "global_mandates", [mandate])
        preds_dict = self.scorer.score_candidates(candidate_universe, mandate, history, g_m, current_time)
        predictions = [(preds_dict[c.candidate_id], c) for c in candidate_universe]
            
        # 2. Rank by P(success) descending
        predictions.sort(key=lambda x: x[0].probability, reverse=True)
        
        plan = [x[1] for x in predictions]
        selected_action = plan[0] if plan else None
        
        # 3. Final validation
        final_decisions = []
        if selected_action:
            final_decisions = self.policy.final_validate([selected_action], mandate, history, current_obligation)
            if not final_decisions[0].is_allowed:
                selected_action = None
                
        pred_mode = predictions[0][0].prediction_mode if predictions else PredictionMode.DEFAULT
                
        return StrategyResult(
            strategy_name=self.__class__.__name__,
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=selected_action,
            retry_plan=plan,
            selected_time=selected_action.scheduled_time if selected_action else None,
            candidate_actions=candidate_universe,
            explanation=f"Selected highest P(success).",
            prediction_mode=pred_mode,
            policy_decisions=final_decisions,
            stopping_reason=final_decisions[-1].reason if final_decisions and not final_decisions[-1].is_allowed else "No candidates"
        )


class MLExpectedValueStrategy:
    """
    Selects the valid candidate maximizing EV = P(success) * amount - action_cost.
    """
    def __init__(
        self,
        policy: DeterministicPolicyEngine,
        scorer: CandidateScoringService,
        action_cost: float = 0.0
    ):
        self.policy = policy
        self.scorer = scorer
        self.action_cost = action_cost
        self.version = "v1.1-ev"
        
    def evaluate(self, mandate: Mandate, history: List[PaymentAttempt], current_time: datetime, current_obligation: Optional[PaymentObligation] = None, candidate_universe: Optional[List[CandidateAction]] = None) -> StrategyResult:
        if not candidate_universe:
            raise ValueError("MLExpectedValueStrategy requires a pre-generated candidate universe")
            
        # 1. Score all valid candidates
        g_m = getattr(self, "global_mandates", [mandate])
        preds_dict = self.scorer.score_candidates(candidate_universe, mandate, history, g_m, current_time)
        predictions = [((preds_dict[c.candidate_id].probability * c.amount) - self.action_cost, preds_dict[c.candidate_id], c) for c in candidate_universe]
            
        # 2. Rank by EV descending
        predictions.sort(key=lambda x: x[0], reverse=True)
        
        plan = [x[2] for x in predictions]
        selected_action = plan[0] if plan else None
        
        # 3. Final validation
        final_decisions = []
        if selected_action:
            final_decisions = self.policy.final_validate([selected_action], mandate, history, current_obligation)
            if not final_decisions[0].is_allowed:
                selected_action = None
                
        pred_mode = predictions[0][1].prediction_mode if predictions else PredictionMode.DEFAULT
                
        return StrategyResult(
            strategy_name=self.__class__.__name__,
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=selected_action,
            retry_plan=plan,
            selected_time=selected_action.scheduled_time if selected_action else None,
            candidate_actions=candidate_universe,
            explanation=f"Selected highest EV (cost={self.action_cost}).",
            prediction_mode=pred_mode,
            policy_decisions=final_decisions,
            stopping_reason=final_decisions[-1].reason if final_decisions and not final_decisions[-1].is_allowed else "No candidates"
        )
