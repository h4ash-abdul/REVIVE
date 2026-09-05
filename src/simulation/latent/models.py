from enum import Enum
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Dict, Optional, List

class Archetype(str, Enum):
    SALARY_CYCLE_REGULAR = "salary_cycle_regular"
    IRREGULAR_GIG = "irregular_gig"
    CHRONIC_LOW_BALANCE = "chronic_low_balance"
    THIN_HISTORY = "thin_history"
    TECHNICAL_DECLINE_PRONE = "technical_decline_prone"

class BehavioralDrift(str, Enum):
    NONE = "none"
    MODERATE = "moderate"
    STRONG = "strong"

class CustomerLatentState(BaseModel):
    """
    STRICTLY INTERNAL TO SIMULATOR. 
    Must NEVER be exposed to features, models, or decision logic.
    """
    model_config = ConfigDict(frozen=True)
    customer_id: UUID
    archetype: Archetype
    true_payday_offset: int  # e.g., days from start of month
    base_liquidity_probability: float  # Base probability they have funds
    technical_failure_propensity: float # e.g. 0.01 for normal, 0.1 for technical_decline_prone
    drift_level: BehavioralDrift
    timing_noise_std_dev: float  # std dev for timing noise in days
    
class MerchantLatentState(BaseModel):
    model_config = ConfigDict(frozen=True)
    merchant_id: UUID
    industry_risk_modifier: float # Adjusts failure rates slightly
    avg_mandate_amount: float
    technical_failure_propensity: float
    # Diversity of historical retries (offsets in days) to prevent model shortcutting
    historical_retry_schedule: List[int]
