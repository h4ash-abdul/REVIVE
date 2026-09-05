import pytest
import random
import subprocess
import json
import os
from uuid import UUID, uuid4
from datetime import datetime, timezone

from src.evaluation.benchmark import BenchmarkRunner, BenchmarkUniverse
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.decision.policy import DeterministicPolicyEngine
from src.configs.models import PolicyConfig
from src.domain.models import CohortSnapshot, Mandate, Customer, Merchant, PaymentAttempt, AttemptStatus
from src.simulation.latent.models import CustomerLatentState, MerchantLatentState, Archetype
from src.domain.interfaces import RecoveryStrategy
from src.domain.models import StrategyResult, CandidateAction, PredictionMode

class MockStrategy(RecoveryStrategy):
    def __init__(self, action_id: str):
        self.action_id = action_id
        
    def evaluate(self, mandate, history, current_time, current_obligation, candidate_universe) -> StrategyResult:
        if not candidate_universe:
            return StrategyResult(
                strategy_name="Mock", strategy_version="1.0", mandate_id=mandate.mandate_id,
                selected_action=None, retry_plan=[], selected_time=None, candidate_actions=[],
                explanation="None", prediction_mode=PredictionMode.DEFAULT, policy_decisions=[], stopping_reason="No valid"
            )
        action = candidate_universe[0]
        return StrategyResult(
            strategy_name="Mock", strategy_version="1.0", mandate_id=mandate.mandate_id,
            selected_action=action, retry_plan=[action], selected_time=action.scheduled_time, candidate_actions=candidate_universe,
            explanation="Mock", prediction_mode=PredictionMode.DEFAULT, policy_decisions=[], stopping_reason=None
        )

def test_rng_independence():
    mandate = Mandate(mandate_id=uuid4(), customer_id=uuid4(), merchant_id=uuid4(), amount=100.0, currency="INR", created_at=datetime.now(timezone.utc), is_active=True, status="active")
    snapshot = CohortSnapshot(
        snapshot_id=uuid4(), experiment_id=uuid4(),
        customers=[], merchants=[], mandates=[mandate],
        initial_history=[PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate.mandate_id, timestamp=datetime.now(timezone.utc), amount=100.0, status=AttemptStatus.FAILED, network_return_code="insufficient_funds")]
    )
    c_latents = {mandate.customer_id: CustomerLatentState(customer_id=mandate.customer_id, archetype=Archetype.SALARY_CYCLE_REGULAR, primary_income_day=1, time_of_day_preference=10, true_payday_offset=0, base_liquidity_probability=0.5, drift_level="moderate", timing_noise_std_dev=1.0, base_success_rate=0.5, technical_failure_propensity=0.1, price_sensitivity=1.0)}
    m_latents = {mandate.merchant_id: MerchantLatentState(merchant_id=mandate.merchant_id, category="sub", expected_ticket_size=100.0, base_success_rate=0.5, technical_failure_propensity=0.1, industry_risk_modifier=1.0, avg_mandate_amount=100.0, historical_retry_schedule=[])}
    
    policy_engine = DeterministicPolicyEngine(PolicyConfig(policy_version="1.0", max_retries_per_mandate=3, min_hours_between_retries=1, allowed_execution_windows_utc=["00:00-23:59"], stop_on_success=True))
    
    outcome_engine1 = OutcomeEngine(random.Random(42))
    runner1 = BenchmarkRunner(snapshot, policy_engine, outcome_engine1, datetime(2025, 1, 1, tzinfo=timezone.utc), c_latents, m_latents)
    runner1.base_seed = 42
    
    outcome_engine2 = OutcomeEngine(random.Random(42))
    runner2 = BenchmarkRunner(snapshot, policy_engine, outcome_engine2, datetime(2025, 1, 1, tzinfo=timezone.utc), c_latents, m_latents)
    runner2.base_seed = 42
    
    strat_a = MockStrategy("A")
    strat_b = MockStrategy("B")
    
    res_1a = runner1.run_strategy("A", strat_a)
    res_1b = runner1.run_strategy("B", strat_b)
    
    res_2b = runner2.run_strategy("B", strat_b)
    res_2a = runner2.run_strategy("A", strat_a)
    
    assert res_1b[0].attempt_count == res_2b[0].attempt_count
    assert res_1b[0].recovered_boolean == res_2b[0].recovered_boolean
    assert res_1a[0].recovered_boolean == res_2a[0].recovered_boolean

def test_cross_process_reproducibility():
    script = '''
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
'''
    with open("tmp_process1.py", "w") as f: f.write(script)
    with open("tmp_process2.py", "w") as f: f.write(script)
    
    out1 = subprocess.check_output(["uv", "run", "python", "tmp_process1.py"]).decode().strip()
    out2 = subprocess.check_output(["uv", "run", "python", "tmp_process2.py"]).decode().strip()
    
    assert out1 == out2
    assert "recovered" in out1
def test_no_hash_in_benchmark():
    import ast
    with open('src/evaluation/benchmark.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'hash':
            pytest.fail('hash() found in benchmark.py - use hashlib.sha256 instead for deterministic seeding')
