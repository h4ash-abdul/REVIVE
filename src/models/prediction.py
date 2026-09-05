from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class Prediction(BaseModel):
    prediction_id: UUID
    candidate_id: UUID
    probability: float
    model_version: str
    feature_version: str
    prediction_timestamp: datetime
    prediction_mode: str
