import json
import random
from uuid import uuid4, UUID
from datetime import datetime, timezone
from pathlib import Path

from src.simulation.generator import DataGenerator
from src.configs.models import SimulatorConfig, NoiseLevel, Scenario
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.domain.models import AttemptStatus

def generate_demo_data():
    print("Generating base cohort...")
    sim_config = SimulatorConfig(
        simulator_version="v2.1",
        seed=42,
        noise_level=NoiseLevel.MEDIUM,
        scenario=Scenario.STRONG_TEMPORAL_SIGNAL,
        time_period_days=60,
        customer_archetypes_distribution={
            "salary_cycle_regular": 0.4,
            "irregular_gig": 0.2,
            "chronic_low_balance": 0.15,
            "thin_history": 0.15,
            "technical_decline_prone": 0.1
        }
    )
    generator = DataGenerator(sim_config)
    generator.run(datetime(2025, 1, 1, tzinfo=timezone.utc), 60, 2000, 100, 2)
    from src.domain.models import CohortSnapshot
    snapshot = CohortSnapshot(
        snapshot_id=uuid4(),
        experiment_id=uuid4(),
        customers=generator.observable_customers,
        merchants=generator.observable_merchants,
        mandates=list(generator.observable_mandates),
        initial_history=generator.observable_events
    )
    print("Finding matching cases...")
    cases = {}
    
    # Sort mandates to ensure determinism in selection
    sorted_mandates = sorted(snapshot.mandates, key=lambda m: str(m.mandate_id))
    
    for mandate in sorted_mandates:
        history = [h for h in snapshot.initial_history if h.mandate_id == mandate.mandate_id]
        if not history:
            continue
            
        last_attempt = sorted(history, key=lambda x: x.timestamp)[-1]
        
        if last_attempt.status == AttemptStatus.FAILED:
            c_lat = generator.latent_customers[mandate.customer_id]
            m_lat = generator.latent_merchants[mandate.merchant_id]
            code = last_attempt.network_return_code
            
            if code in ["ERR_INSUFFICIENT_FUNDS", "N51_FUNDS", "CODE_116_BAL"] and "A" not in cases:
                cases["A"] = (mandate, history, c_lat, m_lat, "Insufficient funds - High Confidence")
            elif code in ["ERR_CONNECTION_TIMEOUT", "ERR_GATEWAY", "E0001_SYS", "technical_failure"] and "B" not in cases:
                cases["B"] = (mandate, history, c_lat, m_lat, "Technical Failure / Do Not Honor")
            elif code in ["invalid_mandate", "revoked"] and "C" not in cases:
                cases["C"] = (mandate, history, c_lat, m_lat, "Mandate Revoked/Expired")
            elif code in ["E0099_UNKNOWN", "unknown_error"] and "D" not in cases:
                cases["D"] = (mandate, history, c_lat, m_lat, "Unknown Failure")
            elif "E" not in cases and len(history) > 3:
                cases["E"] = (mandate, history, c_lat, m_lat, "Policy Restricted (Too many attempts)")
            elif "F" not in cases and c_lat.base_liquidity_probability > 0.8:
                cases["F"] = (mandate, history, c_lat, m_lat, "Will Succeed on Retry")
            elif "G" not in cases and c_lat.base_liquidity_probability < 0.2:
                cases["G"] = (mandate, history, c_lat, m_lat, "Will Exhaust Budget")
                
        if len(cases) == 7:
            break
            
    print("Serializing...")
    out_cases = []
    
    def pydantic_encoder(obj):
        if hasattr(obj, 'model_dump'):
            return obj.model_dump(mode='json')
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
        
    for key, (mandate, history, c_lat, m_lat, title) in cases.items():
        out_cases.append({
            "scenario_key": key,
            "title": title,
            "mandate": mandate.model_dump(mode='json'),
            "history": [h.model_dump(mode='json') for h in history],
            "customer_latent": c_lat.model_dump(mode='json'),
            "merchant_latent": m_lat.model_dump(mode='json')
        })
        
    out_path = Path("data/demo/cases.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out_cases, f, indent=2, default=pydantic_encoder)
        
    print(f"Demo dataset written to {out_path}")

if __name__ == "__main__":
    generate_demo_data()
