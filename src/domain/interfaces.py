from typing import Protocol, List, Optional
from datetime import datetime

from .models import (
    CandidateAction,
    Execution,
    Mandate,
    PolicyDecision,
    Prediction,
    AuditEvent,
    AuditEvent,
    Approval,
    StrategyResult,
    PaymentAttempt
)

class DomainContext:
    pass

class FeatureVector:
    pass


class Model(Protocol):
    def predict_proba(self, candidate: CandidateAction, features: "FeatureVector") -> Prediction:
        ...


class RecoveryStrategy(Protocol):
    def evaluate(self, mandate: Mandate, history: List[PaymentAttempt], current_time: datetime, current_obligation: Optional["PaymentObligation"] = None, candidate_universe: Optional[List[CandidateAction]] = None) -> "StrategyResult":
        ...


class PolicyEngine(Protocol):
    def pre_filter(self, candidates: List[CandidateAction], context: "DomainContext") -> List[PolicyDecision]:
        ...
        
    def final_validation(self, candidate: CandidateAction, context: "DomainContext") -> PolicyDecision:
        ...


class DecisionEngine(Protocol):
    def decide(self, mandate: Mandate, context: "DomainContext") -> CandidateAction:
        ...


class ExecutionEngine(Protocol):
    def execute(self, action: CandidateAction) -> Execution:
        ...


class AuditLedger(Protocol):
    def append(self, event: AuditEvent) -> None:
        ...
