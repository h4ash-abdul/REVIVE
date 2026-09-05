import random
from datetime import datetime, timezone
from typing import Tuple, Optional

from src.domain.models import AttemptStatus, OutcomeStatus, ActionType
from src.simulation.latent.models import CustomerLatentState, MerchantLatentState, Archetype

class OutcomeEngine:
    """
    Independent engine that determines the ground-truth outcome of an action.
    Strictly isolated from any predictive model logic.
    """
    
    def __init__(self, rng: random.Random, global_noise: float = 0.05):
        self.rng = rng
        self.global_noise = global_noise

    def execute_payment_attempt(
        self,
        customer_latent: CustomerLatentState,
        merchant_latent: MerchantLatentState,
        amount: float,
        attempt_time: datetime,
        is_retry: bool = False
    ) -> Tuple[AttemptStatus, Optional[str]]:
        
        # 1. Check technical failure
        tech_prob = customer_latent.technical_failure_propensity + merchant_latent.technical_failure_propensity
        if self.rng.random() < tech_prob:
            # Output an observable network code
            raw_codes = ["ERR_CONNECTION_TIMEOUT", "ERR_GATEWAY", "E0001_SYS", "E0099_UNKNOWN"]
            return AttemptStatus.FAILED, self.rng.choice(raw_codes)
            
        # 2. Add global noise
        # This translates latent probability into raw outputs
        
        prob_success = customer_latent.base_liquidity_probability
        
        if customer_latent.archetype == Archetype.SALARY_CYCLE_REGULAR:
            days_from_payday = abs(attempt_time.day - customer_latent.true_payday_offset)
            if days_from_payday > 15:
                days_from_payday = 30 - days_from_payday
            prob_success += max(0, 0.4 - (days_from_payday * 0.05))
            
        elif customer_latent.archetype == Archetype.IRREGULAR_GIG:
            prob_success += self.rng.uniform(-0.3, 0.3)
            
        elif customer_latent.archetype == Archetype.CHRONIC_LOW_BALANCE:
            prob_success -= 0.2
            
        prob_success = max(0.01, min(0.99, prob_success))
        
        if self.rng.random() < prob_success:
            return AttemptStatus.SUCCESS, None
        else:
            # The latent reason is insufficient funds. Produce a raw observable code.
            raw_codes = ["ERR_INSUFFICIENT_FUNDS", "N51_FUNDS", "CODE_116_BAL"]
            return AttemptStatus.FAILED, self.rng.choice(raw_codes)

    def execute_recovery_action(
        self,
        customer_latent: CustomerLatentState,
        action_type: ActionType,
        attempt_time: datetime
    ) -> Tuple[AttemptStatus, Optional[str]]:
        # Non-payment actions like notifications. Usually succeed technically.
        if self.rng.random() < customer_latent.technical_failure_propensity:
            return AttemptStatus.FAILED, "technical_failure"
        return AttemptStatus.SUCCESS, None
