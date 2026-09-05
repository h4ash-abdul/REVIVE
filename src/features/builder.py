import math
from datetime import datetime, timezone
from typing import List, Optional, Dict
from uuid import UUID

from src.domain.models import Mandate, PaymentAttempt, AttemptStatus, CandidateAction
from src.features.classifier import RuleBasedFailureClassifier
from src.features.models import FeatureVector

class PointInTimeFeatureBuilder:
    def __init__(self, feature_version: str = "v1.0"):
        self.feature_version = feature_version
        self.classifier = RuleBasedFailureClassifier()
        
    def build(
        self,
        mandate: Mandate,
        candidate: CandidateAction,
        global_history: List[PaymentAttempt],
        global_mandates: List[Mandate],
        cutoff_timestamp: datetime,
        target_success: Optional[bool] = None
    ) -> FeatureVector:
        
        # 1. STRICT POINT-IN-TIME FILTERING
        # Filter global history to ONLY events strictly before cutoff
        valid_history = [e for e in global_history if e.timestamp < cutoff_timestamp]
        
        # Split history
        mandate_history = [e for e in valid_history if e.mandate_id == mandate.mandate_id]
        
        # To get merchant history, we need a map of mandate_id -> merchant_id
        mandate_to_merchant = {m.mandate_id: m.merchant_id for m in global_mandates}
        merchant_history = [e for e in valid_history if mandate_to_merchant.get(e.mandate_id) == mandate.merchant_id]
        
        # 2. CANDIDATE FEATURES
        candidate_time = candidate.scheduled_time
        time_until_candidate = (candidate_time - cutoff_timestamp).total_seconds() / 3600.0
        
        # 3. FAILURE FEATURES
        # Find the immediately preceding failure for this mandate
        failures = [e for e in mandate_history if e.status == AttemptStatus.FAILED]
        last_failure = sorted(failures, key=lambda x: x.timestamp)[-1] if failures else None
        
        if last_failure:
            raw_code = last_failure.network_return_code
            classification = self.classifier.classify(last_failure, mandate)
            failure_category = classification.category.value
        else:
            raw_code = None
            failure_category = "UNKNOWN"
            
        # 4. CUSTOMER/HISTORY FEATURES
        c_pay_count = len(mandate_history)
        c_successes = [e for e in mandate_history if e.status == AttemptStatus.SUCCESS]
        c_failures = [e for e in mandate_history if e.status == AttemptStatus.FAILED]
        
        c_succ_count = len(c_successes)
        c_fail_count = len(c_failures)
        c_succ_rate = c_succ_count / c_pay_count if c_pay_count > 0 else 0.0
        
        amounts = [e.amount for e in mandate_history]
        c_amt_mean = sum(amounts) / len(amounts) if amounts else 0.0
        c_amt_std = 0.0
        if len(amounts) > 1:
            var = sum((x - c_amt_mean) ** 2 for x in amounts) / (len(amounts) - 1)
            c_amt_std = math.sqrt(var)
            
        c_depth = (cutoff_timestamp - mandate_history[0].timestamp).total_seconds() / 86400.0 if mandate_history else 0.0
        
        last_succ = sorted(c_successes, key=lambda x: x.timestamp)[-1] if c_successes else None
        t_since_succ = (cutoff_timestamp - last_succ.timestamp).total_seconds() / 3600.0 if last_succ else None
        t_since_fail = (cutoff_timestamp - last_failure.timestamp).total_seconds() / 3600.0 if last_failure else None
        
        # Buckets
        target_hour = candidate_time.hour
        target_dom = candidate_time.day
        
        hour_succ = [e for e in c_successes if e.timestamp.hour == target_hour]
        hour_attempts = [e for e in mandate_history if e.timestamp.hour == target_hour]
        c_succ_rate_hour = len(hour_succ) / len(hour_attempts) if hour_attempts else None
        
        day_succ = [e for e in c_successes if e.timestamp.day == target_dom]
        day_attempts = [e for e in mandate_history if e.timestamp.day == target_dom]
        c_succ_rate_day = len(day_succ) / len(day_attempts) if day_attempts else None
        
        # 5. MANDATE FEATURES
        mandate_age = (cutoff_timestamp - mandate.created_at).total_seconds() / 86400.0
        attempt_number = c_pay_count + 1
        
        # 6. MERCHANT FEATURES
        m_pay_count = len(merchant_history)
        m_successes = [e for e in merchant_history if e.status == AttemptStatus.SUCCESS]
        m_succ_count = len(m_successes)
        m_succ_rate = m_succ_count / m_pay_count if m_pay_count > 0 else 0.0
        m_depth = (cutoff_timestamp - merchant_history[0].timestamp).total_seconds() / 86400.0 if merchant_history else 0.0
        
        m_hour_succ = [e for e in m_successes if e.timestamp.hour == target_hour]
        m_hour_attempts = [e for e in merchant_history if e.timestamp.hour == target_hour]
        m_succ_rate_hour = len(m_hour_succ) / len(m_hour_attempts) if m_hour_attempts else None
        
        # Hierarchical Mode Fallback metadata
        pred_mode = "DEFAULT"
        if c_pay_count >= 5:
            pred_mode = "CUSTOMER"
        elif m_pay_count >= 50:
            pred_mode = "MERCHANT"
        elif len(valid_history) >= 100:
            pred_mode = "POPULATION"
        
        return FeatureVector(
            mandate_id=mandate.mandate_id,
            candidate_id=candidate.candidate_id,
            feature_version=self.feature_version,
            generated_at=datetime.now(timezone.utc),
            cutoff_timestamp=cutoff_timestamp,
            target_success=target_success,
            
            candidate_hour=candidate_time.hour,
            candidate_weekday=candidate_time.weekday(),
            candidate_day_of_month=candidate_time.day,
            time_until_candidate_hours=time_until_candidate,
            
            hist_payment_count=c_pay_count,
            hist_success_count=c_succ_count,
            hist_failure_count=c_fail_count,
            hist_success_rate=c_succ_rate,
            hist_amount_mean=c_amt_mean,
            hist_amount_std=c_amt_std,
            history_depth_days=c_depth,
            time_since_prev_success_hours=t_since_succ,
            time_since_prev_failure_hours=t_since_fail,
            hist_success_rate_hour_bucket=c_succ_rate_hour,
            hist_success_rate_day_bucket=c_succ_rate_day,
            
            amount=mandate.amount,
            mandate_age_days=mandate_age,
            current_attempt_number=attempt_number,
            
            merchant_hist_payment_count=m_pay_count,
            merchant_success_count=m_succ_count,
            merchant_success_rate=m_succ_rate,
            merchant_history_depth_days=m_depth,
            merchant_success_rate_hour_bucket=m_succ_rate_hour,
            
            failure_category=failure_category,
            raw_network_return_code=raw_code,
            prediction_mode=pred_mode
        )
