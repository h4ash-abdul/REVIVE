from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class NoiseLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Scenario(str, Enum):
    STRONG_TEMPORAL_SIGNAL = "strong_temporal_signal"
    NOISY_SIGNAL = "noisy_signal"
    COLD_START_HEAVY = "cold_start_heavy"
    BEHAVIOR_DRIFT = "behavior_drift"
    WEAK_TEMPORAL_CORRELATION = "weak_temporal_correlation"

class SimulatorConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    simulator_version: str
    seed: int
    scenario: Scenario = Field(default=Scenario.STRONG_TEMPORAL_SIGNAL)
    noise_level: NoiseLevel = Field(default=NoiseLevel.MEDIUM)
    customer_archetypes_distribution: Dict[str, float]
    behavioral_drift_rate: float = Field(default=0.0)
    enable_technical_declines: bool = True


class PolicyConfig(BaseModel):
    """
    Configuration for the deterministic policy engine.
    NOTE: Example values in default configs or tests are for simulation only 
    and make NO claims about actual regulatory rules or Razorpay compliance.
    """
    model_config = ConfigDict(frozen=True)
    policy_version: str
    max_retries_per_mandate: int = Field(ge=1)
    min_hours_between_retries: int = Field(ge=0)
    allowed_execution_windows_utc: List[str]  # e.g., ["09:00-17:00"]
    stop_on_success: bool = True
    require_manual_approval_over_amount: float = Field(default=1000.0)


class ModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    model_version: str
    feature_version: str
    model_type: str  # e.g., "logistic_regression"
    hyperparameters: Dict[str, Any]
    fallback_hierarchy: List[str]  # e.g., ["customer", "merchant", "population"]
    probability_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    experiment_id: str
    strategy_version: str
    simulator_config: SimulatorConfig
    policy_config: PolicyConfig
    model_config: ModelConfig
    dataset_version: str
    duration_days: int = Field(ge=1)
    metrics_to_track: List[str]
