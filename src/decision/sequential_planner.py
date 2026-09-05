from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from uuid import uuid4

from src.domain.models import Mandate, PaymentAttempt, PaymentObligation, CandidateAction, StrategyResult, AttemptStatus
from src.domain.interfaces import RecoveryStrategy
from src.decision.scorer import CandidateScoringService
from src.decision.policy import DeterministicPolicyEngine
from src.decision.generator import CandidateGenerator

class SequentialPlannerStrategy(RecoveryStrategy):
    def __init__(self, policy: DeterministicPolicyEngine, scorer: CandidateScoringService, max_depth: int = 3):
        self.policy = policy
        self.scorer = scorer
        self.max_depth = max_depth
        self.global_mandates = []
        self.generator = CandidateGenerator(days_ahead=30, hours_of_day=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        
    def evaluate(
        self,
        mandate: Mandate,
        history: List[PaymentAttempt],
        current_time: datetime,
        current_obligation: PaymentObligation,
        candidate_universe: List[CandidateAction]
    ) -> StrategyResult:
        
        # We need to compute the best sequence.
        # V(state, depth) = max_{a} [ P(success|a) * amount + (1 - P(success|a)) * V(state', depth+1) ]
        
        # To avoid infinite recursion, we limit max_depth based on policy remaining retries
        max_retries = self.policy.config.max_retries_per_mandate
        attempts_in_obligation = len(current_obligation.retry_attempt_ids)
        remaining_budget = max_retries - attempts_in_obligation
        
        if remaining_budget <= 0:
            return StrategyResult(
                strategy_name="SequentialPlanner", strategy_version="1.0", mandate_id=mandate.mandate_id,
                selected_action=None, retry_plan=[], selected_time=None, candidate_actions=candidate_universe,
                explanation="No budget remaining", prediction_mode=None, policy_decisions=[], stopping_reason="budget_exhausted"
            )
            
        # Optimization: We only explore a subset of candidates to keep branching factor manageable.
        # E.g. top 3 candidates per step.
        best_val, best_plan, pred_mode = self._plan(mandate, history, current_time, current_obligation, candidate_universe, remaining_budget)
        
        if not best_plan:
            return StrategyResult(
                strategy_name="SequentialPlanner", strategy_version="1.0", mandate_id=mandate.mandate_id,
                selected_action=None, retry_plan=[], selected_time=None, candidate_actions=candidate_universe,
                explanation="No valid plan found", prediction_mode=None, policy_decisions=[], stopping_reason="no_valid_plan"
            )
            
        return StrategyResult(
            strategy_name="SequentialPlanner", strategy_version="1.0", mandate_id=mandate.mandate_id,
            selected_action=best_plan[0], retry_plan=best_plan, selected_time=best_plan[0].scheduled_time,
            candidate_actions=candidate_universe,
            explanation=f"Planned sequence with EV {best_val:.2f}",
            prediction_mode=pred_mode,
            policy_decisions=[],
            stopping_reason=None
        )
        
    def _plan(self, mandate: Mandate, history: List[PaymentAttempt], current_time: datetime, obligation: PaymentObligation, candidates: List[CandidateAction], budget: int) -> Tuple[float, List[CandidateAction], Any]:
        if budget <= 0 or not candidates:
            return 0.0, [], None
            
        # Score candidates
        preds = self.scorer.score_candidates(candidates, mandate, history, self.global_mandates, current_time)
        
        # Sort candidates by probability to prune branching factor (greedy heuristic for tree search)
        sorted_cands = sorted(candidates, key=lambda c: preds[c.candidate_id].probability, reverse=True)
        top_cands = sorted_cands[:3] # Branching factor of 3
        
        best_val = -1.0
        best_seq = []
        best_mode = None
        
        for cand in top_cands:
            p = preds[cand.candidate_id].probability
            mode = preds[cand.candidate_id].prediction_mode
            
            # Expected immediate reward
            imm_reward = p * cand.amount
            
            # Future expected value
            future_val = 0.0
            if budget > 1:
                # Simulate failure
                sim_attempt = PaymentAttempt(
                    attempt_id=uuid4(), mandate_id=mandate.mandate_id,
                    timestamp=cand.scheduled_time, amount=cand.amount, status=AttemptStatus.FAILED, network_return_code="insufficient_funds"
                )
                new_history = history + [sim_attempt]
                new_ob = obligation.model_copy(update={"retry_attempt_ids": obligation.retry_attempt_ids + [sim_attempt.attempt_id]})
                
                # Generate new valid candidates
                raw_cands = self.generator.generate(mandate, cand.scheduled_time)
                decisions = self.policy.pre_filter(raw_cands, mandate, new_history, new_ob)
                valid_cands = [next(c for c in raw_cands if c.candidate_id == d.candidate_id) for d in decisions if d.is_allowed]
                
                if valid_cands:
                    f_val, _, _ = self._plan(mandate, new_history, cand.scheduled_time, new_ob, valid_cands, budget - 1)
                    future_val = f_val
                    
            ev = imm_reward + (1 - p) * future_val
            
            if ev > best_val:
                best_val = ev
                best_seq = [cand] # We only return the plan root because true execution interleaves
                best_mode = mode
                
        return best_val, best_seq, best_mode
