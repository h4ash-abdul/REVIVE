from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import uuid4

from src.domain.models import (
    Mandate, PaymentAttempt, AttemptStatus, CandidateAction, ActionType,
    StrategyResult, PredictionMode, PaymentObligation
)
from src.decision.policy import DeterministicPolicyEngine

class ImmediateRetryStrategy:
    """
    Selects the earliest valid policy-compliant retry opportunity, extending up to the budget.
    """
    def __init__(self, policy: DeterministicPolicyEngine):
        self.policy = policy
        self.version = "v1.1"
        
    def evaluate(self, mandate: Mandate, history: List[PaymentAttempt], current_time: datetime, current_obligation: Optional[PaymentObligation] = None, candidate_universe: Optional[List[CandidateAction]] = None) -> StrategyResult:
        candidates = []
        budget = self.policy.config.max_retries_per_mandate
        
        # We need spacing between retries, using the policy min_hours to generate an immediate sequential plan
        spacing = max(1, self.policy.config.min_hours_between_retries)
        
        if candidate_universe is not None:
            candidates = candidate_universe
            decisions = []
            plan = sorted(candidates, key=lambda c: c.scheduled_time)
        else:
            candidates = []
            # We generate a large set of chronological candidates, the policy engine will select up to the budget
            for hour_offset in range(1, 24 * 30):
                c_time = current_time + timedelta(hours=hour_offset)
                c = CandidateAction(
                    candidate_id=uuid4(),
                    mandate_id=mandate.mandate_id,
                    action_type=ActionType.PAYMENT_RETRY,
                    scheduled_time=c_time,
                    amount=mandate.amount,
                    source="immediate_retry"
                )
                candidates.append(c)
                
            decisions = self.policy.pre_filter(candidates, mandate, history, current_obligation)
            plan = []
            for d in decisions:
                if d.is_allowed:
                    plan.append(next(c for c in candidates if c.candidate_id == d.candidate_id))
                
        selected_action = plan[0] if plan else None
        final_decisions = []
        if selected_action:
            final_decisions = self.policy.final_validate([selected_action], mandate, history, current_obligation)
            if not final_decisions[0].is_allowed:
                selected_action = None
                
        all_decisions = decisions + final_decisions
                
        return StrategyResult(
            strategy_name=self.__class__.__name__,
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=selected_action,
            retry_plan=plan,
            selected_time=selected_action.scheduled_time if selected_action else None,
            candidate_actions=candidates,
            explanation=f"Generated immediate plan with {len(plan)} steps.",
            prediction_mode=None,
            policy_decisions=all_decisions,
            stopping_reason=all_decisions[-1].reason if all_decisions else "No candidates"
        )


class FixedScheduleStrategy:
    """
    Uses a predetermined configurable offset schedule (e.g., [24, 48, 72] hours).
    Evaluates all offsets sequentially against policy.
    """
    def __init__(self, policy: DeterministicPolicyEngine, offsets_hours: List[int]):
        self.policy = policy
        self.offsets_hours = sorted(offsets_hours)
        self.version = "v1.1"
        
    def evaluate(self, mandate: Mandate, history: List[PaymentAttempt], current_time: datetime, current_obligation: Optional[PaymentObligation] = None, candidate_universe: Optional[List[CandidateAction]] = None) -> StrategyResult:
        candidates = []
        for offset in self.offsets_hours:
            c_time = current_time + timedelta(hours=offset)
            candidates.append(CandidateAction(
                candidate_id=uuid4(),
                mandate_id=mandate.mandate_id,
                action_type=ActionType.PAYMENT_RETRY,
                scheduled_time=c_time,
                amount=mandate.amount,
                source="fixed_schedule"
            ))
            
        decisions = self.policy.pre_filter(candidates, mandate, history, current_obligation)
        
        plan = []
        for d in decisions:
            if d.is_allowed:
                plan.append(next(c for c in candidates if c.candidate_id == d.candidate_id))
                
        selected_action = plan[0] if plan else None
        final_decisions = []
        if selected_action:
            final_decisions = self.policy.final_validate([selected_action], mandate, history, current_obligation)
            if not final_decisions[0].is_allowed:
                selected_action = None
                
        all_decisions = decisions + final_decisions
                
        return StrategyResult(
            strategy_name=self.__class__.__name__,
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=selected_action,
            retry_plan=plan,
            selected_time=selected_action.scheduled_time if selected_action else None,
            candidate_actions=candidates,
            explanation=f"Generated fixed schedule plan with {len(plan)} steps.",
            prediction_mode=None,
            policy_decisions=all_decisions,
            stopping_reason=all_decisions[-1].reason if all_decisions else "No candidates generated"
        )


class SmartHistoricalHeuristicStrategy:
    """
    Non-ML heuristic. Identifies the historical hour-of-day where success is most likely.
    Cascades from Customer -> Merchant -> Population -> Default based on configured thresholds.
    """
    def __init__(
        self, 
        policy: DeterministicPolicyEngine,
        global_history: List[PaymentAttempt],
        min_customer_history: int = 5,
        min_merchant_history: int = 50,
        min_population_history: int = 100
    ):
        self.policy = policy
        self.global_history = global_history
        self.min_customer_history = min_customer_history
        self.min_merchant_history = min_merchant_history
        self.min_population_history = min_population_history
        self.version = "v1.1"
        
    def evaluate(self, mandate: Mandate, history: List[PaymentAttempt], current_time: datetime, current_obligation: Optional[PaymentObligation] = None, candidate_universe: Optional[List[CandidateAction]] = None) -> StrategyResult:
        best_hour = 12 # safe default
        pred_mode = PredictionMode.DEFAULT
        
        # 1. Customer Level
        successes = [e for e in history if e.status == AttemptStatus.SUCCESS]
        
        merchant_successes = []
        population_successes = []
        
        # Build merchant and population pools if available
        if hasattr(self, 'global_mandates'):
            mandate_to_merchant = {m.mandate_id: m.merchant_id for m in self.global_mandates}
            target_merchant = mandate_to_merchant.get(mandate.mandate_id)
            
            for e in self.global_history:
                if e.status == AttemptStatus.SUCCESS:
                    population_successes.append(e)
                    if mandate_to_merchant.get(e.mandate_id) == target_merchant:
                        merchant_successes.append(e)
        else:
            # Fallback for testing backward compatibility
            population_successes = [e for e in self.global_history if e.status == AttemptStatus.SUCCESS]
            # In testing, we can simulate merchant successes by just checking a dummy map
            merchant_successes = [e for e in self.global_history if getattr(e, '_merchant_id', None) == mandate.merchant_id]

        if len(history) >= self.min_customer_history and successes:
            best_hour = self._get_best_hour(successes)
            pred_mode = PredictionMode.CUSTOMER
        elif len(merchant_successes) >= self.min_merchant_history:
            best_hour = self._get_best_hour(merchant_successes)
            pred_mode = PredictionMode.MERCHANT
        elif len(population_successes) >= self.min_population_history:
            best_hour = self._get_best_hour(population_successes)
            pred_mode = PredictionMode.POPULATION
        else:
            best_hour = 12
            pred_mode = PredictionMode.DEFAULT
            
        if candidate_universe is not None:
            # Phase 8: Candidate fairness snapping
            # Find the candidate in the universe that is closest to `best_hour` on any given day
            # Since candidates are pre-filtered, we just score them by distance to optimal hour
            candidates = candidate_universe
            decisions = [] # Pre-filtered by caller
            
            # Snap to optimal hour
            plan = []
            for c in candidates:
                # Calculate hour distance (circular)
                h = c.scheduled_time.hour
                dist = min(abs(h - best_hour), 24 - abs(h - best_hour))
                plan.append((dist, c))
                
            plan.sort(key=lambda x: (x[0], x[1].scheduled_time))
            plan = [x[1] for x in plan]
            
        else:
            # Legacy generation
            candidates = []
            for day_offset in range(1, 31):
                base = current_time + timedelta(days=day_offset)
                c_time = base.replace(hour=best_hour, minute=0, second=0, microsecond=0)
                if c_time > current_time:
                    candidates.append(CandidateAction(
                        candidate_id=uuid4(),
                        mandate_id=mandate.mandate_id,
                        action_type=ActionType.PAYMENT_RETRY,
                        scheduled_time=c_time,
                        amount=mandate.amount,
                        source=f"heuristic_{pred_mode.value}"
                    ))
            decisions = self.policy.pre_filter(candidates, mandate, history, current_obligation)
            plan = []
            for d in decisions:
                if d.is_allowed:
                    plan.append(next(c for c in candidates if c.candidate_id == d.candidate_id))
                
        selected_action = plan[0] if plan else None
        final_decisions = []
        if selected_action:
            final_decisions = self.policy.final_validate([selected_action], mandate, history, current_obligation)
            if not final_decisions[0].is_allowed:
                selected_action = None
                
        all_decisions = decisions + final_decisions
                
        return StrategyResult(
            strategy_name=self.__class__.__name__,
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=selected_action,
            retry_plan=plan,
            selected_time=selected_action.scheduled_time if selected_action else None,
            candidate_actions=candidates,
            explanation=f"Generated {pred_mode.value} plan with {len(plan)} steps at {best_hour}:00.",
            prediction_mode=pred_mode,
            policy_decisions=all_decisions,
            stopping_reason=all_decisions[-1].reason if all_decisions else "No candidates generated"
        )
        
    def _get_best_hour(self, successes: List[PaymentAttempt]) -> int:
        counts = {}
        for s in successes:
            h = s.timestamp.hour
            counts[h] = counts.get(h, 0) + 1
        return max(counts, key=counts.get)
