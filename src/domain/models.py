from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, AwareDatetime


def utc_now() -> AwareDatetime:
    return datetime.now(timezone.utc)


class MandateStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    COMPLETED = "completed"


class AttemptStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"


class OutcomeStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    NOTIFICATION = "notification"
    PROMISE_TO_PAY = "promise_to_pay"
    PAYMENT_RETRY = "payment_retry"


class PredictionMode(str, Enum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    POPULATION = "population"
    DEFAULT = "default"


class EventType(str, Enum):
    CANDIDATES_GENERATED = "CANDIDATES_GENERATED"
    POLICY_PRE_FILTERED = "POLICY_PRE_FILTERED"
    PREDICTION_SCORED = "PREDICTION_SCORED"
    DECISION_MADE = "DECISION_MADE"
    DECISION_APPROVED = "DECISION_APPROVED"
    POLICY_FINAL_VALIDATED = "POLICY_FINAL_VALIDATED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"


class ApprovalMode(str, Enum):
    MANUAL = "manual"
    POLICY_AUTO = "policy_auto"
    DEMO_AUTO = "demo_auto"


class PolicyCheckpoint(str, Enum):
    PRE_FILTER = "pre_filter"
    FINAL_VALIDATION = "final_validation"


class Customer(BaseModel):
    model_config = ConfigDict(frozen=True)
    customer_id: UUID
    created_at: AwareDatetime
    segment: str


class Merchant(BaseModel):
    model_config = ConfigDict(frozen=True)
    merchant_id: UUID
    name: str
    industry: str
    fallback_config: Dict[str, Any]


class Mandate(BaseModel):
    model_config = ConfigDict(frozen=True)
    mandate_id: UUID
    customer_id: UUID
    merchant_id: UUID
    amount: float = Field(gt=0)
    status: MandateStatus
    created_at: AwareDatetime
    expires_at: Optional[AwareDatetime] = None


class PaymentAttempt(BaseModel):
    model_config = ConfigDict(frozen=True)
    attempt_id: UUID
    mandate_id: UUID
    timestamp: AwareDatetime
    amount: float = Field(gt=0)
    status: AttemptStatus
    
    # Boundary Documentation:
    # This field holds the raw observable error code returned by the synthetic bank/network.
    # It must NOT contain the simulator's latent truth or the future ML classifier's
    # clean "failure_category" (which the model must learn to infer).
    network_return_code: Optional[str] = None


class FailureCategory(str, Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    TECHNICAL_FAILURE = "technical_failure"
    MANDATE_EXPIRED_OR_REVOKED = "mandate_expired_or_revoked"
    RISK_OR_POLICY_DECLINE = "risk_or_policy_decline"
    UNKNOWN_OR_AMBIGUOUS = "unknown_or_ambiguous"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FailureClassificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    category: FailureCategory
    retryable: bool
    confidence: ConfidenceLevel
    reason: str
    source_event_id: UUID
    classifier_version: str


class RecoveryAction(BaseModel):
    model_config = ConfigDict(frozen=True)
    action_id: UUID
    mandate_id: UUID
    timestamp: AwareDatetime
    type: ActionType
    status: AttemptStatus


class CandidateAction(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidate_id: UUID
    mandate_id: UUID  # Added for relational linkage to the Mandate
    action_type: ActionType
    scheduled_time: AwareDatetime
    amount: float = Field(gt=0)
    source: str


class Prediction(BaseModel):
    model_config = ConfigDict(frozen=True)
    prediction_id: UUID
    candidate_id: UUID
    probability: float = Field(ge=0.0, le=1.0)
    prediction_mode: PredictionMode
    model_version: str
    feature_version: str
    created_at: AwareDatetime = Field(default_factory=utc_now)


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision_id: UUID
    candidate_id: UUID
    is_allowed: bool
    reason: Optional[str] = None
    policy_version: str
    checkpoint: PolicyCheckpoint


class StrategyResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    strategy_name: str
    strategy_version: str
    mandate_id: UUID
    selected_action: Optional[CandidateAction]
    retry_plan: List[CandidateAction]
    selected_time: Optional[AwareDatetime]
    candidate_actions: List[CandidateAction]
    explanation: str
    prediction_mode: Optional[PredictionMode]
    policy_decisions: List[PolicyDecision]
    stopping_reason: Optional[str]


class Approval(BaseModel):
    model_config = ConfigDict(frozen=True)
    approval_id: UUID
    decision_id: UUID
    mode: ApprovalMode
    timestamp: AwareDatetime = Field(default_factory=utc_now)


class Execution(BaseModel):
    model_config = ConfigDict(frozen=True)
    execution_id: UUID
    candidate_id: UUID
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    idempotency_key: str


class Outcome(BaseModel):
    model_config = ConfigDict(frozen=True)
    outcome_id: UUID
    execution_id: UUID
    status: OutcomeStatus
    metadata: Dict[str, Any]


class AuditEvent(BaseModel):
    """Append-only event ledger representation."""
    model_config = ConfigDict(frozen=True)
    event_id: UUID
    correlation_id: UUID
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    mandate_id: UUID
    customer_id: UUID
    event_type: EventType
    sequence_number: int = Field(ge=0)
    payload: Dict[str, Any]


class ExperimentRun(BaseModel):
    model_config = ConfigDict(frozen=True)
    experiment_id: UUID
    dataset_version: str
    simulator_version: str
    policy_version: str
    strategy_versions: Dict[str, str]  # Map of strategy name to version
    seed: int
    cohort_snapshot_id: UUID
    start_time: AwareDatetime = Field(default_factory=utc_now)
    end_time: Optional[AwareDatetime] = None
    configuration: Dict[str, Any]


class CohortSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    snapshot_id: UUID
    experiment_id: UUID
    customers: List[Customer]
    merchants: List[Merchant]
    mandates: List[Mandate]
    initial_history: List[PaymentAttempt]


class ObligationStatus(str, Enum):
    PENDING = "pending"
    ACTIVE_RECOVERY = "active_recovery"
    SUCCESS = "success"
    FAILED_EXHAUSTED = "failed_exhausted"


class PaymentObligation(BaseModel):
    model_config = ConfigDict(frozen=True)
    obligation_id: UUID
    mandate_id: UUID
    due_time: AwareDatetime
    amount: float = Field(gt=0)
    status: ObligationStatus
    original_attempt_id: Optional[UUID] = None
    retry_attempt_ids: List[UUID] = Field(default_factory=list)


class MandateResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    mandate_id: UUID
    strategy: str
    initial_amount: float
    recovered_amount: float
    recovered_boolean: bool
    attempt_count: int
    retry_budget_exhausted: bool
    stop_reason: str
    policy_violation_count: int
    execution_error_count: int


