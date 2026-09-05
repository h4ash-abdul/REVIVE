from typing import List
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from src.domain.models import (
    CandidateAction, 
    PolicyDecision, 
    PolicyCheckpoint, 
    Mandate, 
    MandateStatus,
    PaymentAttempt,
    AttemptStatus,
    PaymentObligation,
    ObligationStatus
)
from src.configs.models import PolicyConfig


class DeterministicPolicyEngine:
    def __init__(self, config: PolicyConfig):
        self.config = config

    def pre_filter(self, candidates: List[CandidateAction], mandate: Mandate, history: List[PaymentAttempt], current_obligation: PaymentObligation = None) -> List[PolicyDecision]:
        decisions = []
        
        # Determine relevant history
        if current_obligation:
            relevant_ids = set(current_obligation.retry_attempt_ids)
            if current_obligation.original_attempt_id:
                relevant_ids.add(current_obligation.original_attempt_id)
            relevant_history = [e for e in history if e.attempt_id in relevant_ids]
            
            # Check success state of current obligation
            if self.config.stop_on_success and current_obligation.status == ObligationStatus.SUCCESS:
                for c in candidates:
                    decisions.append(PolicyDecision(
                        decision_id=uuid4(),
                        candidate_id=c.candidate_id,
                        is_allowed=False,
                        reason="Current payment obligation already has a successful payment",
                        policy_version=self.config.policy_version,
                        checkpoint=PolicyCheckpoint.PRE_FILTER
                    ))
                return decisions
        else:
            relevant_history = history
            # DO NOT check historical mandate-level successes for stop_on_success.
            # Only current_obligation can definitively prove the current cycle succeeded.
            
        # 2. Check mandate expiry / revocation
        if mandate.status in (MandateStatus.REVOKED, MandateStatus.EXPIRED):
            for c in candidates:
                decisions.append(PolicyDecision(
                    decision_id=uuid4(),
                    candidate_id=c.candidate_id,
                    is_allowed=False,
                    reason=f"Mandate status is {mandate.status}",
                    policy_version=self.config.policy_version,
                    checkpoint=PolicyCheckpoint.PRE_FILTER
                ))
            return decisions

        # Sort candidates chronologically
        sorted_cands = sorted(candidates, key=lambda x: x.scheduled_time)
        
        # Only count retries (failed or otherwise) for the current cycle budget
        if current_obligation:
            failed_retries_count = len(current_obligation.retry_attempt_ids)
        else:
            failed_retries_count = len([e for e in relevant_history if e.status == AttemptStatus.FAILED])
            
        last_attempt_time = max([e.timestamp for e in relevant_history]) if relevant_history else None
        
        for c in sorted_cands:
            # 3. Check retry budget
            if failed_retries_count >= self.config.max_retries_per_mandate:
                decisions.append(PolicyDecision(
                    decision_id=uuid4(),
                    candidate_id=c.candidate_id,
                    is_allowed=False,
                    reason="Exceeded maximum retries",
                    policy_version=self.config.policy_version,
                    checkpoint=PolicyCheckpoint.PRE_FILTER
                ))
                continue
                
            # 4. Check time distances for each candidate
            if last_attempt_time:
                delta = c.scheduled_time - last_attempt_time
                if delta.total_seconds() < self.config.min_hours_between_retries * 3600:
                    decisions.append(PolicyDecision(
                        decision_id=uuid4(),
                        candidate_id=c.candidate_id,
                        is_allowed=False,
                        reason=f"Must wait {self.config.min_hours_between_retries} hours between retries",
                        policy_version=self.config.policy_version,
                        checkpoint=PolicyCheckpoint.PRE_FILTER
                    ))
                    continue
                    
            if mandate.expires_at and c.scheduled_time > mandate.expires_at:
                decisions.append(PolicyDecision(
                    decision_id=uuid4(),
                    candidate_id=c.candidate_id,
                    is_allowed=False,
                    reason="Scheduled time is after mandate expiry",
                    policy_version=self.config.policy_version,
                    checkpoint=PolicyCheckpoint.PRE_FILTER
                ))
                continue
                
            # If allowed, it consumes a budget slot and updates the last attempt time
            decisions.append(PolicyDecision(
                decision_id=uuid4(),
                candidate_id=c.candidate_id,
                is_allowed=True,
                reason="Passes pre-filter policies",
                policy_version=self.config.policy_version,
                checkpoint=PolicyCheckpoint.PRE_FILTER
            ))
            failed_retries_count += 1
            last_attempt_time = c.scheduled_time
            
        return decisions

    def final_validate(self, candidates: List[CandidateAction], mandate: Mandate, history: List[PaymentAttempt], current_obligation: PaymentObligation = None) -> List[PolicyDecision]:
        """
        Final safety check before execution. Re-evaluates state and budget.
        Re-uses pre_filter logic but flags as FINAL_VALIDATION.
        """
        pre_filter_results = self.pre_filter(candidates, mandate, history, current_obligation)
        
        final_decisions = []
        for dec in pre_filter_results:
            final_decisions.append(PolicyDecision(
                decision_id=uuid4(),
                candidate_id=dec.candidate_id,
                is_allowed=dec.is_allowed,
                reason=dec.reason,
                policy_version=dec.policy_version,
                checkpoint=PolicyCheckpoint.FINAL_VALIDATION
            ))
            
        return final_decisions
