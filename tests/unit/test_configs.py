import pytest
from pydantic import ValidationError
from src.configs.models import SimulatorConfig, PolicyConfig, NoiseLevel

def test_simulator_config():
    config = SimulatorConfig(
        simulator_version="v1",
        seed=42,
        noise_level=NoiseLevel.LOW,
        customer_archetypes_distribution={"type_a": 0.5, "type_b": 0.5},
        behavioral_drift_rate=0.01,
        enable_technical_declines=True
    )
    assert config.seed == 42
    
    with pytest.raises(ValidationError):
        SimulatorConfig(
            simulator_version="v1",
            seed=42,
            noise_level="invalid_enum_value",
            customer_archetypes_distribution={"type_a": 0.5, "type_b": 0.5}
        )

def test_policy_config():
    config = PolicyConfig(
        policy_version="p1",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["09:00-17:00"]
    )
    assert config.max_retries_per_mandate == 3
    
    with pytest.raises(ValidationError):
        PolicyConfig(
            policy_version="p1",
            max_retries_per_mandate=-1, # Should fail ge=1 validation
            min_hours_between_retries=24,
            allowed_execution_windows_utc=["09:00-17:00"]
        )
