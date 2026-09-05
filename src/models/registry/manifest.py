from pydantic import BaseModel
from typing import Dict, Any, Optional

class ModelManifest(BaseModel):
    model_version: str
    model_type: str
    feature_version: str
    dataset_version: str
    training_window: Dict[str, str]
    validation_window: Dict[str, str]
    test_window: Dict[str, str]
    parameters: Dict[str, Any]
    seed: int
    metrics: Dict[str, Dict[str, float]]
    artifact_path: str
    preprocessing_path: Optional[str] = None
    training_timestamp: str
