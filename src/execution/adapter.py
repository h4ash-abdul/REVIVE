from typing import Optional, List, Tuple
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.models import PaymentObligation, CandidateAction, PolicyDecision, PaymentAttempt, AttemptStatus, Mandate
from src.domain.audit import ExecutionRecord, ExecutionStatus, VerificationOutcome
from src.simulation.outcome_engine.engine import OutcomeEngine

class PolicyViolationError(Exception):
    pass

class SimulatedExecutionAdapter:
    """
    Executes an action deterministically against the OutcomeEngine.
    Enforces a strict boundary: only approved PolicyDecisions can be executed.
    """
    def __init__(self, outcome_engine: OutcomeEngine):
        self.outcome_engine = outcome_engine
        
    def execute(self, action: CandidateAction, policy_decision: PolicyDecision, obligation: PaymentObligation, mandate: Mandate, c_latent, m_latent, current_time: datetime) -> Tuple[ExecutionRecord, Optional[PaymentAttempt]]:
        if action.candidate_id != policy_decision.candidate_id:
            raise PolicyViolationError("Action ID does not match PolicyDecision ID.")
            
        if not policy_decision.is_allowed:
            record = ExecutionRecord(
                execution_id=uuid4(),
                mandate_id=mandate.mandate_id,
                obligation_id=obligation.obligation_id,
                action_id=action.candidate_id,
                requested_at=current_time,
                executed_at=current_time,
                status=ExecutionStatus.REJECTED,
                failure_reason=f"Policy rejected: {policy_decision.reason}"
            )
            return record, None
            
        # Simulate execution
        status, code = self.outcome_engine.execute_payment_attempt(
            customer_latent=c_latent,
            merchant_latent=m_latent,
            amount=action.amount,
            attempt_time=action.scheduled_time,
            is_retry=True
        )
        
        simulated_attempt = PaymentAttempt(
            attempt_id=uuid4(),
            mandate_id=mandate.mandate_id,
            timestamp=action.scheduled_time,
            amount=action.amount,
            status=status,
            network_return_code=code
        )
        
        record = ExecutionRecord(
            execution_id=uuid4(),
            mandate_id=mandate.mandate_id,
            obligation_id=obligation.obligation_id,
            action_id=action.candidate_id,
            requested_at=current_time,
            executed_at=action.scheduled_time,
            status=ExecutionStatus.COMPLETED,
            simulated_attempt_id=simulated_attempt.attempt_id
        )
        
        return record, simulated_attempt

class OutcomeVerifier:
    """
    Verifies execution results.
    Strictly uses observable outcomes attached to the current obligation cycle.
    """
    def verify(self, execution_record: ExecutionRecord, simulated_attempt: Optional[PaymentAttempt], current_time: datetime) -> VerificationOutcome:
        if execution_record.status == ExecutionStatus.REJECTED:
            return VerificationOutcome(
                outcome_id=uuid4(),
                execution_id=execution_record.execution_id,
                obligation_id=execution_record.obligation_id,
                verified_at=current_time,
                success=False,
                recovered_amount=0.0,
                network_return_code="POLICY_REJECTED"
            )
            
        if not simulated_attempt:
            return VerificationOutcome(
                outcome_id=uuid4(),
                execution_id=execution_record.execution_id,
                obligation_id=execution_record.obligation_id,
                verified_at=current_time,
                success=False,
                recovered_amount=0.0,
                network_return_code="SIMULATION_ERROR"
            )
            
        is_success = simulated_attempt.status == AttemptStatus.SUCCESS
        
        return VerificationOutcome(
            outcome_id=uuid4(),
            execution_id=execution_record.execution_id,
            obligation_id=execution_record.obligation_id,
            verified_at=current_time,
            success=is_success,
            recovered_amount=simulated_attempt.amount if is_success else 0.0,
            network_return_code=simulated_attempt.network_return_code
        )
