from datetime import datetime, timezone, timedelta
from typing import List
from uuid import uuid4

from src.domain.models import CandidateAction, ActionType, Mandate

class CandidateGenerator:
    def __init__(self, days_ahead: int = 5, hours_of_day: List[int] = None):
        self.days_ahead = days_ahead
        self.hours_of_day = hours_of_day or [9, 14, 20]  # Default: 9 AM, 2 PM, 8 PM UTC
        
    def generate(self, mandate: Mandate, current_time: datetime, source_id: str = "copilot") -> List[CandidateAction]:
        """
        Generates candidate retry actions for a mandate at fixed intervals over a specified horizon.
        Ensures that generated timestamps are strictly strictly strictly > current_time.
        """
        candidates = []
        
        # Start looking from today
        base_date = current_time.replace(minute=0, second=0, microsecond=0)
        
        for day_offset in range(self.days_ahead + 1):
            target_date = base_date + timedelta(days=day_offset)
            
            for target_hour in self.hours_of_day:
                candidate_time = target_date.replace(hour=target_hour)
                
                # Must be strictly in the future relative to the decision time
                if candidate_time > current_time:
                    candidates.append(
                        CandidateAction(
                            candidate_id=uuid4(),
                            mandate_id=mandate.mandate_id,
                            action_type=ActionType.PAYMENT_RETRY,
                            scheduled_time=candidate_time,
                            amount=mandate.amount,
                            source=source_id
                        )
                    )
                    
        return candidates
