from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional

class FeatureVector(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    # Metadata
    mandate_id: UUID
    candidate_id: UUID
    feature_version: str
    generated_at: datetime
    cutoff_timestamp: datetime
    
    # Target (Only for supervised learning, never used as input)
    target_success: Optional[bool] = None
    
    # Candidate Features
    candidate_hour: int
    candidate_weekday: int
    candidate_day_of_month: int
    time_until_candidate_hours: float
    
    # Customer/History Features
    hist_payment_count: int
    hist_success_count: int
    hist_failure_count: int
    hist_success_rate: float
    hist_amount_mean: float
    hist_amount_std: float
    history_depth_days: float
    time_since_prev_success_hours: Optional[float]
    time_since_prev_failure_hours: Optional[float]
    
    # Time-bucketed Customer Success Rates
    hist_success_rate_hour_bucket: Optional[float]
    hist_success_rate_day_bucket: Optional[float]
    
    # Mandate Features
    amount: float
    mandate_age_days: float
    current_attempt_number: int
    
    # Merchant Features
    merchant_hist_payment_count: int
    merchant_success_count: int
    merchant_success_rate: float
    merchant_history_depth_days: float
    merchant_success_rate_hour_bucket: Optional[float]
    
    # Failure Features
    failure_category: str
    raw_network_return_code: Optional[str]
    
    # Hierarchical Mode
    prediction_mode: str
