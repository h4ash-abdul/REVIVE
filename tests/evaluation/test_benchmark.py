import pytest
from datetime import datetime, timezone
import random
from uuid import uuid4

from src.domain.models import CohortSnapshot, Mandate, MandateStatus, PaymentAttempt, AttemptStatus
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.decision.policy import DeterministicPolicyEngine
from src.configs.models import PolicyConfig
from src.evaluation.benchmark import BenchmarkRunner, BenchmarkUniverse
from src.decision.baselines import ImmediateRetryStrategy, FixedScheduleStrategy
from src.simulation.latent.models import CustomerLatentState, Archetype, MerchantLatentState, BehavioralDrift

@pytest.fixture
def mock_snapshot():
    mandate_id = uuid4()
    cust_id = uuid4()
    merch_id = uuid4()
    mandate = Mandate(
        mandate_id=mandate_id,
        customer_id=cust_id,
        merchant_id=merch_id,
        amount=100.0,
        status=MandateStatus.ACTIVE,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )
    attempt = PaymentAttempt(
        attempt_id=uuid4(),
        mandate_id=mandate_id,
        timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
        amount=100.0,
        status=AttemptStatus.FAILED
    )
    return CohortSnapshot(
        snapshot_id=uuid4(),
        experiment_id=uuid4(),
        customers=[], merchants=[],
        mandates=[mandate],
        initial_history=[attempt]
    )

@pytest.fixture
def mock_latents(mock_snapshot):
    c_latents = {mock_snapshot.mandates[0].customer_id: CustomerLatentState(customer_id=mock_snapshot.mandates[0].customer_id, archetype=Archetype.SALARY_CYCLE_REGULAR, true_payday_offset=1, base_liquidity_probability=0.5, technical_failure_propensity=0.01, drift_level=BehavioralDrift.NONE, timing_noise_std_dev=0.0)}
    m_latents = {mock_snapshot.mandates[0].merchant_id: MerchantLatentState(merchant_id=mock_snapshot.mandates[0].merchant_id, industry="test", technical_failure_propensity=0.01, historical_retry_schedule=[1], industry_risk_modifier=0.0, avg_mandate_amount=100.0)}
    return c_latents, m_latents

@pytest.fixture
def runner(mock_snapshot, mock_latents):
    policy_cfg = PolicyConfig(
        policy_version="v1",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True
    )
    policy = DeterministicPolicyEngine(policy_cfg)
    outcome_engine = OutcomeEngine(random.Random(42))
    return BenchmarkRunner(mock_snapshot, policy, outcome_engine, datetime(2025, 1, 3, tzinfo=timezone.utc), mock_latents[0], mock_latents[1])


def test_fairness_independent_clones(runner):
    strat1 = ImmediateRetryStrategy(runner.policy)
    strat2 = FixedScheduleStrategy(runner.policy, [48, 72, 96])
    
    univ1 = BenchmarkUniverse(runner.snapshot, strat1, runner.policy, runner.outcome_engine, runner.latent_customers, runner.latent_merchants)
    univ2 = BenchmarkUniverse(runner.snapshot, strat2, runner.policy, runner.outcome_engine, runner.latent_customers, runner.latent_merchants)
    
    mandate_id = runner.snapshot.mandates[0].mandate_id
    
    # Mutate univ1
    univ1.add_attempt(PaymentAttempt(attempt_id=uuid4(), mandate_id=mandate_id, timestamp=datetime.now(timezone.utc), amount=100.0, status=AttemptStatus.FAILED))
    
    # Univ2 should be isolated
    assert len(univ1.get_history(mandate_id)) == 2
    assert len(univ2.get_history(mandate_id)) == 1

def test_integrity_amount_recovered(runner):
    strat = ImmediateRetryStrategy(runner.policy)
    results = runner.run_strategy("Immediate", strat)
    
    res = results[0]
    assert res.recovered_amount <= res.initial_amount
    if res.recovered_boolean:
        assert res.recovered_amount == res.initial_amount

def test_budget_exhausted_stops(runner):
    strat = ImmediateRetryStrategy(runner.policy)
    # Give outcome engine an impossible customer so they always fail
    c_id = runner.snapshot.mandates[0].customer_id
    runner.latent_customers[c_id] = CustomerLatentState(customer_id=c_id, archetype=Archetype.CHRONIC_LOW_BALANCE, true_payday_offset=1, base_liquidity_probability=-10.0, technical_failure_propensity=0.0, drift_level=BehavioralDrift.NONE, timing_noise_std_dev=0.0)
    
    results = runner.run_strategy("Immediate", strat)
    res = results[0]
    
    # max budget is 3. Since budget is isolated to retries, 3 retries are allowed.
    assert res.attempt_count == 3
    assert res.retry_budget_exhausted is True
    assert res.stop_reason == "Budget Exhausted"

def test_success_stops(runner):
    strat = ImmediateRetryStrategy(runner.policy)
    # Guarantee success
    c_id = runner.snapshot.mandates[0].customer_id
    runner.latent_customers[c_id] = CustomerLatentState(customer_id=c_id, archetype=Archetype.CHRONIC_LOW_BALANCE, true_payday_offset=1, base_liquidity_probability=10.0, technical_failure_propensity=0.0, drift_level=BehavioralDrift.NONE, timing_noise_std_dev=0.0)
    
    results = runner.run_strategy("Immediate", strat)
    res = results[0]
    
    # Should stop on first attempt due to guaranteed success
    assert res.attempt_count == 1
    assert res.recovered_boolean is True
    assert res.retry_budget_exhausted is False
    assert res.stop_reason == "Recovered"



def test_final_validate_blocks_execution(runner, monkeypatch):
    from src.domain.models import PolicyDecision, PolicyCheckpoint
    
    # Mock final_validate to always fail
    def always_reject(*args, **kwargs):
        return [PolicyDecision(
            decision_id=uuid4(),
            candidate_id=uuid4(),
            is_allowed=False,
            reason="Rejected by test mock final_validate",
            policy_version="v1.0",
            checkpoint=PolicyCheckpoint.FINAL_VALIDATION
        )]
    
    monkeypatch.setattr(runner.policy, 'final_validate', always_reject)
    
    strat = ImmediateRetryStrategy(runner.policy)
    results = runner.run_strategy("Immediate", strat)
    res = results[0]
    
    assert res.attempt_count == 0
    assert "Execution blocked by final validation: Rejected by test mock final_validate" in res.stop_reason
