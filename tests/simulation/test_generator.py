import pytest
from datetime import datetime, timezone
from src.configs.models import SimulatorConfig, NoiseLevel, Scenario
from src.simulation.generator import DataGenerator

def test_reproducibility():
    config = SimulatorConfig(
        simulator_version="v2.1",
        seed=42,
        noise_level=NoiseLevel.LOW,
        customer_archetypes_distribution={
            "salary_cycle_regular": 0.4,
            "irregular_gig": 0.2,
            "chronic_low_balance": 0.15,
            "thin_history": 0.15,
            "technical_decline_prone": 0.1
        }
    )
    
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    
    gen1 = DataGenerator(config)
    gen1.run(start_date, 60, 10, 2, 1)
    
    gen2 = DataGenerator(config)
    gen2.run(start_date, 60, 10, 2, 1)
    
    assert [(e.status, e.amount) for e in gen1.observable_events] == [(e.status, e.amount) for e in gen2.observable_events]

def test_different_seed_different_output():
    config1 = SimulatorConfig(
        simulator_version="v2.1", seed=42, noise_level=NoiseLevel.LOW,
        customer_archetypes_distribution={"salary_cycle_regular": 1.0}
    )
    config2 = SimulatorConfig(
        simulator_version="v2.1", seed=43, noise_level=NoiseLevel.LOW,
        customer_archetypes_distribution={"salary_cycle_regular": 1.0}
    )
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    
    gen1 = DataGenerator(config1)
    gen1.run(start_date, 60, 10, 2, 1)
    
    gen2 = DataGenerator(config2)
    gen2.run(start_date, 60, 10, 2, 1)
    
    assert [(e.status, e.amount) for e in gen1.observable_events] != [(e.status, e.amount) for e in gen2.observable_events]

def test_no_latent_fields_in_observable():
    config = SimulatorConfig(
        simulator_version="v2.1", seed=42, noise_level=NoiseLevel.LOW,
        customer_archetypes_distribution={"salary_cycle_regular": 1.0}
    )
    gen = DataGenerator(config)
    gen.run(datetime(2025, 1, 1, tzinfo=timezone.utc), 60, 1, 1, 1)
    
    cust = gen.observable_customers[0]
    # Check that archetype is not in the observable dict
    assert "archetype" not in cust.model_dump()
    assert "true_payday_offset" not in cust.model_dump()

def test_valid_amounts_and_states():
    config = SimulatorConfig(
        simulator_version="v2.1", seed=42, noise_level=NoiseLevel.LOW,
        customer_archetypes_distribution={"salary_cycle_regular": 1.0}
    )
    gen = DataGenerator(config)
    gen.run(datetime(2025, 1, 1, tzinfo=timezone.utc), 60, 10, 2, 2)
    
    for m in gen.observable_mandates:
        assert m.amount > 0
        assert m.status in ["active", "expired", "revoked"]
        assert m.created_at <= m.expires_at if m.expires_at else True
        
    for e in gen.observable_events:
        assert e.amount > 0
        assert e.status in ["success", "failed", "pending", "error"]
        # Temporal consistency: Event must not happen before mandate creation
        mandate = next(m for m in gen.observable_mandates if m.mandate_id == e.mandate_id)
        assert e.timestamp >= mandate.created_at
