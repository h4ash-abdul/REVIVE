from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from src.domain.models import (
    Mandate, PaymentAttempt, AttemptStatus, CohortSnapshot,
    ExperimentRun, MandateResult, PaymentObligation, ObligationStatus
)
from src.domain.interfaces import RecoveryStrategy
from src.decision.policy import DeterministicPolicyEngine
from src.simulation.outcome_engine.engine import OutcomeEngine

class BenchmarkUniverse:
    """
    An isolated simulated universe for a single strategy.
    Maintains its own copy of the evolving history.
    """
    def __init__(self, snapshot: CohortSnapshot, strategy: RecoveryStrategy, policy: DeterministicPolicyEngine, outcome_engine: OutcomeEngine, latent_customers: dict, latent_merchants: dict):
        self.snapshot = snapshot
        self.strategy = strategy
        self.policy = policy
        self.outcome_engine = outcome_engine
        self.latent_customers = latent_customers
        self.latent_merchants = latent_merchants
        
        # Deep clone the observable history
        self.history_by_mandate = {}
        for attempt in snapshot.initial_history:
            if attempt.mandate_id not in self.history_by_mandate:
                self.history_by_mandate[attempt.mandate_id] = []
            # We copy to ensure isolation
            self.history_by_mandate[attempt.mandate_id].append(attempt.model_copy())
            
    def get_history(self, mandate_id) -> List[PaymentAttempt]:
        return self.history_by_mandate.get(mandate_id, [])
        
    def add_attempt(self, attempt: PaymentAttempt):
        if attempt.mandate_id not in self.history_by_mandate:
            self.history_by_mandate[attempt.mandate_id] = []
        self.history_by_mandate[attempt.mandate_id].append(attempt)


class BenchmarkRunner:
    """
    Evaluates strategies fairly by cloning the CohortSnapshot.
    """
    def __init__(self, snapshot: CohortSnapshot, policy: DeterministicPolicyEngine, outcome_engine: OutcomeEngine, current_time: datetime, latent_customers: dict, latent_merchants: dict):
        self.snapshot = snapshot
        self.policy = policy
        self.outcome_engine = outcome_engine
        self.current_time = current_time
        self.latent_customers = latent_customers
        self.latent_merchants = latent_merchants
        
    def run_strategy(self, strategy_name: str, strategy: RecoveryStrategy) -> List[MandateResult]:
        universe = BenchmarkUniverse(self.snapshot, strategy, self.policy, self.outcome_engine, self.latent_customers, self.latent_merchants)
        results = []
        
        for mandate in self.snapshot.mandates:
            # We only evaluate failed mandates that are eligible for retry
            initial_history = universe.get_history(mandate.mandate_id)
            if any(e.status == AttemptStatus.SUCCESS for e in initial_history):
                continue
                
            res = self._evaluate_mandate(universe, mandate)
            # Annotate with strategy name before saving
            res = res.model_copy(update={"strategy": strategy_name})
            results.append(res)
            
        return results
        
    def _evaluate_mandate(self, universe: BenchmarkUniverse, mandate: Mandate) -> MandateResult:
        import random
        import hashlib
        from src.simulation.outcome_engine.engine import OutcomeEngine
        # Isolate RNG per mandate for strategy independence
        base_seed = getattr(self, "base_seed", 42)
        seed_bytes = hashlib.sha256(f"{base_seed}_{mandate.mandate_id}".encode()).digest()
        rng_seed = int.from_bytes(seed_bytes[:8], byteorder='little')
        mandate_outcome_engine = OutcomeEngine(random.Random(rng_seed), global_noise=universe.outcome_engine.global_noise)
        attempt_count = 0
        policy_violations = 0
        exec_errors = 0
        recovered = False
        stop_reason = "Unknown"
        
        current_time = self.current_time
        initial_history = universe.get_history(mandate.mandate_id)
        last_attempt = initial_history[-1] if initial_history else None
        
        # Construct the PaymentObligation for the current failure cycle
        obligation = PaymentObligation(
            obligation_id=uuid4(),
            mandate_id=mandate.mandate_id,
            due_time=last_attempt.timestamp if last_attempt else current_time,
            amount=mandate.amount,
            status=ObligationStatus.ACTIVE_RECOVERY,
            original_attempt_id=last_attempt.attempt_id if last_attempt else None,
            retry_attempt_ids=[]
        )
        
        from src.decision.generator import CandidateGenerator
        generator = CandidateGenerator(days_ahead=30, hours_of_day=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        
        while True:
            history = universe.get_history(mandate.mandate_id)
            
            # 1. Generate Universe
            raw_candidates = generator.generate(mandate, current_time)
            
            # 2. Policy Pre-Filter
            decisions = universe.policy.pre_filter(raw_candidates, mandate, history, obligation)
            policy_violations += len([d for d in decisions if not d.is_allowed])
            
            valid_candidates = []
            for d in decisions:
                if d.is_allowed:
                    valid_candidates.append(next(c for c in raw_candidates if c.candidate_id == d.candidate_id))
                    
            if not valid_candidates:
                stop_reason = decisions[-1].reason if decisions else "No candidates generated"
                break
            
            # 3. Strategy Selection
            strategy_res = universe.strategy.evaluate(
                mandate=mandate,
                history=history,
                current_time=current_time,
                current_obligation=obligation,
                candidate_universe=valid_candidates
            )
            
            if not strategy_res.retry_plan:
                stop_reason = strategy_res.stopping_reason or "Strategy generated empty plan"
                break
                
            next_action = strategy_res.retry_plan[0]
            
            # Fairness enforcement
            if next_action.candidate_id not in [c.candidate_id for c in valid_candidates]:
                raise ValueError("Strategy selected action outside common candidate universe")
            
            # CRITICAL ENFORCEMENT: Final Validation before Execution
            final_check = universe.policy.final_validate([next_action], mandate, history, obligation)
            if not final_check[0].is_allowed:
                stop_reason = f"Execution blocked by final validation: {final_check[0].reason}"
                policy_violations += 1
                break
            
            attempt_count += 1
            current_time = next_action.scheduled_time
            
            # Execute through latent outcome engine
            c_latent = universe.latent_customers[mandate.customer_id]
            m_latent = universe.latent_merchants[mandate.merchant_id]
            status, code = mandate_outcome_engine.execute_payment_attempt(
                customer_latent=c_latent,
                merchant_latent=m_latent,
                amount=next_action.amount,
                attempt_time=current_time,
                is_retry=True
            )
            
            attempt = PaymentAttempt(
                attempt_id=uuid4(),
                mandate_id=mandate.mandate_id,
                timestamp=current_time,
                amount=next_action.amount,
                status=status,
                network_return_code=code
            )
            universe.add_attempt(attempt)
            obligation.retry_attempt_ids.append(attempt.attempt_id)
            
            if attempt.status == AttemptStatus.SUCCESS:
                obligation = obligation.model_copy(update={"status": ObligationStatus.SUCCESS})
                recovered = True
                stop_reason = "Recovered"
                break
                
            elif attempt.status == AttemptStatus.ERROR:
                exec_errors += 1
                stop_reason = "Execution Error"
                break
                
            # If failed, we loop back around and the strategy will generate a new plan based on updated history
            
        failed_count = len(obligation.retry_attempt_ids)
        budget_exhausted = failed_count >= universe.policy.config.max_retries_per_mandate
        
        if budget_exhausted and not recovered:
            stop_reason = "Budget Exhausted"
            
        return MandateResult(
            mandate_id=mandate.mandate_id,
            strategy="Placeholder",
            initial_amount=mandate.amount,
            recovered_amount=mandate.amount if recovered else 0.0,
            recovered_boolean=recovered,
            attempt_count=attempt_count,
            retry_budget_exhausted=budget_exhausted,
            stop_reason=stop_reason,
            policy_violation_count=policy_violations,
            execution_error_count=exec_errors
        )
