
import json
import random
from uuid import UUID
from datetime import datetime, timezone
from src.evaluation.benchmark import BenchmarkRunner
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.decision.policy import DeterministicPolicyEngine
from src.configs.models import PolicyConfig
from src.domain.models import CohortSnapshot, Mandate, PaymentAttempt, AttemptStatus
from src.simulation.latent.models import CustomerLatentState, MerchantLatentState, Archetype
from tests.evaluation.test_benchmark_rng_independence import MockStrategy

m_id = UUID('12345678-1234-5678-1234-567812345678')
mandate = Mandate(mandate_id=m_id, customer_id=UUID('22345678-1234-5678-1234-567812345678'), merchant_id=UUID('32345678-1234-5678-1234-567812345678'), amount=100.0, currency="INR", created_at=datetime(2025, 1, 1, tzinfo=timezone.utc), is_active=True, status="active")
snapshot = CohortSnapshot(
    snapshot_id=UUID('42345678-1234-5678-1234-567812345678'), experiment_id=UUID('52345678-1234-5678-1234-567812345678'),
    customers=[], merchants=[], mandates=[mandate],
    initial_history=[PaymentAttempt(attempt_id=UUID('62345678-1234-5678-1234-567812345678'), mandate_id=mandate.mandate_id, timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc), amount=100.0, status=AttemptStatus.FAILED, network_return_code="insufficient_funds")]
)
c_latents = {mandate.customer_id: CustomerLatentState(customer_id=mandate.customer_id, archetype=Archetype.SALARY_CYCLE_REGULAR, primary_income_day=1, time_of_day_preference=10, true_payday_offset=0, base_liquidity_probability=0.5, drift_level="moderate", timing_noise_std_dev=1.0, base_success_rate=0.5, technical_failure_propensity=0.1, price_sensitivity=1.0)}
m_latents = {mandate.merchant_id: MerchantLatentState(merchant_id=mandate.merchant_id, category="sub", expected_ticket_size=100.0, base_success_rate=0.5, technical_failure_propensity=0.1, industry_risk_modifier=1.0, avg_mandate_amount=100.0, historical_retry_schedule=[])}

policy = DeterministicPolicyEngine(PolicyConfig(policy_version="1.0", max_retries_per_mandate=3, min_hours_between_retries=1, allowed_execution_windows_utc=["00:00-23:59"], stop_on_success=True))
outcome_engine = OutcomeEngine(random.Random(42))
runner = BenchmarkRunner(snapshot, policy, outcome_engine, datetime(2025, 1, 2, tzinfo=timezone.utc), c_latents, m_latents)
runner.base_seed = 42

res = runner.run_strategy("A", MockStrategy("A"))
print(json.dumps({"recovered": res[0].recovered_boolean, "attempts": res[0].attempt_count}))
