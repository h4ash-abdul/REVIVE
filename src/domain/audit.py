from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, AwareDatetime

from src.domain.models import PaymentObligation, PaymentAttempt, PolicyDecision, StrategyResult, AttemptStatus

class RecoveryEventType(str, Enum):
    PAYMENT_FAILED = "PAYMENT_FAILED"
    FAILURE_CLASSIFIED = "FAILURE_CLASSIFIED"
    FEATURES_COMPUTED = "FEATURES_COMPUTED"
    RECOVERY_PREDICTION_CREATED = "RECOVERY_PREDICTION_CREATED"
    CANDIDATES_GENERATED = "CANDIDATES_GENERATED"
    POLICY_PRECHECK = "POLICY_PRECHECK"
    ACTION_SELECTED = "ACTION_SELECTED"
    EXECUTION_REQUESTED = "EXECUTION_REQUESTED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"

class RecoveryAuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: AwareDatetime
    mandate_id: UUID
    obligation_id: UUID
    event_type: RecoveryEventType
    actor: str
    details: Dict[str, Any] = Field(default_factory=dict)
    
class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

class ExecutionRecord(BaseModel):
    execution_id: UUID = Field(default_factory=uuid4)
    mandate_id: UUID
    obligation_id: UUID
    action_id: UUID
    requested_at: AwareDatetime
    executed_at: Optional[AwareDatetime] = None
    status: ExecutionStatus
    failure_reason: Optional[str] = None
    simulated_attempt_id: Optional[UUID] = None

class VerificationOutcome(BaseModel):
    outcome_id: UUID = Field(default_factory=uuid4)
    execution_id: UUID
    obligation_id: UUID
    verified_at: AwareDatetime
    success: bool
    recovered_amount: float
    network_return_code: Optional[str] = None

class RecoveryTrace(BaseModel):
    mandate_id: UUID
    obligation_id: UUID
    amount: float
    currency: str
    failure_category: str
    failure_code: str
    
    # State
    budget_remaining: int
    
    # History
    audit_trail: List[RecoveryAuditEvent] = Field(default_factory=list)
    
    # Active Decision Objects
    strategy_result: Optional[StrategyResult] = None
    execution_record: Optional[ExecutionRecord] = None
    outcome: Optional[VerificationOutcome] = None
