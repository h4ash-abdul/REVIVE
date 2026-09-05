from typing import Optional
from src.domain.models import (
    PaymentAttempt,
    Mandate,
    MandateStatus,
    FailureCategory,
    ConfidenceLevel,
    FailureClassificationResult,
    AttemptStatus
)

class RuleBasedFailureClassifier:
    """
    Deterministic rule-based failure classifier for REVIVE Phase 3A.
    Uses ONLY observable domain objects.
    DOES NOT access simulator latent variables.
    """
    
    VERSION = "v1.0-rules"
    
    # Mapping of raw observable codes to our standard taxonomy
    NSF_CODES = {"ERR_INSUFFICIENT_FUNDS", "N51_FUNDS", "CODE_116_BAL"}
    TECH_CODES = {"ERR_CONNECTION_TIMEOUT", "ERR_GATEWAY", "E0001_SYS"}
    RISK_CODES = {"ERR_RISK_SUSPECTED", "POLICY_DECLINE_102"}
    AMBIGUOUS_CODES = {"E0099_UNKNOWN"}
    
    def classify(
        self,
        attempt: PaymentAttempt,
        mandate: Mandate
    ) -> FailureClassificationResult:
        
        # Guard against inconsistent state
        if attempt.mandate_id != mandate.mandate_id:
            return self._build_result(
                attempt,
                FailureCategory.UNKNOWN_OR_AMBIGUOUS,
                False,
                ConfidenceLevel.HIGH,
                "Inconsistent state: attempt and mandate IDs do not match."
            )
            
        # Check mandate lifecycle first
        # If the mandate is revoked or expired at the time of classification,
        # it's an invalid attempt regardless of network code.
        # Note: if attempt was made after mandate expiry, we map this strongly.
        if mandate.status in (MandateStatus.REVOKED, MandateStatus.EXPIRED):
            return self._build_result(
                attempt,
                FailureCategory.MANDATE_EXPIRED_OR_REVOKED,
                False,
                ConfidenceLevel.HIGH,
                f"Mandate status is {mandate.status.value}"
            )
            
        if attempt.status == AttemptStatus.SUCCESS:
            return self._build_result(
                attempt,
                FailureCategory.UNKNOWN_OR_AMBIGUOUS,
                False,
                ConfidenceLevel.LOW,
                "Attempt was successful, should not be classified as a failure."
            )
            
        # Network code mapping
        code = attempt.network_return_code
        
        if not code:
            return self._build_result(
                attempt,
                FailureCategory.UNKNOWN_OR_AMBIGUOUS,
                False,  # conservative handling
                ConfidenceLevel.LOW,
                "Missing network return code."
            )
            
        code = code.strip().upper()
        
        if code in self.NSF_CODES:
            return self._build_result(
                attempt,
                FailureCategory.INSUFFICIENT_FUNDS,
                True,
                ConfidenceLevel.HIGH,
                f"Mapped known NSF code: {code}"
            )
            
        elif code in self.TECH_CODES:
            return self._build_result(
                attempt,
                FailureCategory.TECHNICAL_FAILURE,
                True,
                ConfidenceLevel.HIGH,
                f"Mapped known technical error code: {code}"
            )
            
        elif code in self.RISK_CODES:
            return self._build_result(
                attempt,
                FailureCategory.RISK_OR_POLICY_DECLINE,
                False,
                ConfidenceLevel.HIGH,
                f"Mapped known risk/policy code: {code}"
            )
            
        elif code in self.AMBIGUOUS_CODES:
            return self._build_result(
                attempt,
                FailureCategory.UNKNOWN_OR_AMBIGUOUS,
                False, # Conservative
                ConfidenceLevel.MEDIUM,
                f"Code explicitly mapped to ambiguous: {code}"
            )
            
        else:
            # Fallback for genuinely unknown codes
            return self._build_result(
                attempt,
                FailureCategory.UNKNOWN_OR_AMBIGUOUS,
                False, # Conservative handling for unmapped codes
                ConfidenceLevel.LOW,
                f"Unmapped or unknown code: {code}"
            )
            
    def _build_result(
        self,
        attempt: PaymentAttempt,
        category: FailureCategory,
        retryable: bool,
        confidence: ConfidenceLevel,
        reason: str
    ) -> FailureClassificationResult:
        return FailureClassificationResult(
            category=category,
            retryable=retryable,
            confidence=confidence,
            reason=reason,
            source_event_id=attempt.attempt_id,
            classifier_version=self.VERSION
        )
