import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
from uuid import uuid4

from src.domain.models import (
    Customer, Merchant, Mandate, MandateStatus, PaymentAttempt, AttemptStatus, ActionType
)
from src.simulation.latent.models import (
    CustomerLatentState, MerchantLatentState, Archetype, BehavioralDrift
)
from src.simulation.outcome_engine.engine import OutcomeEngine
from src.configs.models import SimulatorConfig, NoiseLevel

class DataGenerator:
    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        
        # Noise level configuration
        if config.noise_level == NoiseLevel.LOW:
            gn = 0.01
        elif config.noise_level == NoiseLevel.HIGH:
            gn = 0.15
        else:
            gn = 0.05
        self.outcome_engine = OutcomeEngine(self.rng, global_noise=gn)
        
        self.observable_customers: List[Customer] = []
        self.observable_merchants: List[Merchant] = []
        self.observable_mandates: List[Mandate] = []
        self.observable_events: List[PaymentAttempt] = []
        
        self.latent_customers: Dict[UUID, CustomerLatentState] = {}
        self.latent_merchants: Dict[UUID, MerchantLatentState] = {}
        
    def run(self, start_date: datetime, duration_days: int, num_customers: int, num_merchants: int, mandates_per_customer: int):
        self._generate_merchants(num_merchants)
        self._generate_customers(num_customers, start_date)
        self._generate_mandates(mandates_per_customer, start_date, duration_days)
        self._simulate_history(start_date, duration_days)
        
    def _generate_merchants(self, count: int):
        for i in range(count):
            m_id = uuid4()
            merch = Merchant(
                merchant_id=m_id,
                name=f"Merchant_{i}",
                industry=self.rng.choice(["Utilities", "Streaming", "Loans", "SaaS"]),
                fallback_config={}
            )
            
            # Merchant-specific historical retry policy
            retry_policy = self.rng.choice([
                [1, 3],       # typical 1d then 3d
                [2, 5],       # spaced out
                [1, 2, 3],    # aggressive
                [3]           # lazy
            ])
            
            lat = MerchantLatentState(
                merchant_id=m_id,
                industry_risk_modifier=self.rng.uniform(-0.05, 0.05),
                avg_mandate_amount=self.rng.uniform(10.0, 500.0),
                technical_failure_propensity=self.rng.uniform(0.001, 0.02) if self.config.enable_technical_declines else 0.0,
                historical_retry_schedule=retry_policy
            )
            self.observable_merchants.append(merch)
            self.latent_merchants[m_id] = lat

    def _generate_customers(self, count: int, start_date: datetime):
        archetypes = list(self.config.customer_archetypes_distribution.keys())
        weights = list(self.config.customer_archetypes_distribution.values())
        
        for _ in range(count):
            c_id = uuid4()
            arch_str = self.rng.choices(archetypes, weights=weights)[0]
            arch = Archetype(arch_str)
            
            base_liq = 0.8
            tech_fail = 0.01
            drift = BehavioralDrift.NONE
            timing_noise = 1.0
            
            if arch == Archetype.CHRONIC_LOW_BALANCE:
                base_liq = 0.3
            elif arch == Archetype.IRREGULAR_GIG:
                base_liq = 0.6
                timing_noise = 5.0
            elif arch == Archetype.THIN_HISTORY:
                base_liq = 0.5
            elif arch == Archetype.TECHNICAL_DECLINE_PRONE:
                tech_fail = 0.15
                
            if self.rng.random() < self.config.behavioral_drift_rate:
                drift = self.rng.choice([BehavioralDrift.MODERATE, BehavioralDrift.STRONG])

            lat = CustomerLatentState(
                customer_id=c_id,
                archetype=arch,
                true_payday_offset=self.rng.randint(1, 28),
                base_liquidity_probability=base_liq + self.rng.uniform(-0.1, 0.1),
                technical_failure_propensity=tech_fail,
                drift_level=drift,
                timing_noise_std_dev=timing_noise
            )
            
            cust = Customer(
                customer_id=c_id,
                created_at=start_date - timedelta(days=self.rng.randint(0, 365)),
                segment="default"
            )
            
            self.observable_customers.append(cust)
            self.latent_customers[c_id] = lat

    def _generate_mandates(self, mandates_per_customer: int, start_date: datetime, duration_days: int):
        for cust in self.observable_customers:
            for _ in range(mandates_per_customer):
                merch = self.rng.choice(self.observable_merchants)
                lat_merch = self.latent_merchants[merch.merchant_id]
                
                created_offset = self.rng.randint(0, max(1, duration_days - 30))
                m_created = start_date + timedelta(days=created_offset)
                
                # Realistic lifecycle probability
                lifecycle_roll = self.rng.random()
                if lifecycle_roll < 0.05:
                    status = MandateStatus.REVOKED
                    expires_at = m_created + timedelta(days=self.rng.randint(10, 180))
                elif lifecycle_roll < 0.15:
                    status = MandateStatus.EXPIRED
                    expires_at = m_created + timedelta(days=self.rng.randint(10, 365))
                else:
                    status = MandateStatus.ACTIVE
                    expires_at = m_created + timedelta(days=365*5)
                
                mandate = Mandate(
                    mandate_id=uuid4(),
                    customer_id=cust.customer_id,
                    merchant_id=merch.merchant_id,
                    amount=round(lat_merch.avg_mandate_amount * self.rng.uniform(0.5, 2.0), 2),
                    status=status,
                    created_at=m_created,
                    expires_at=expires_at
                )
                self.observable_mandates.append(mandate)

    def _simulate_history(self, start_date: datetime, duration_days: int):
        for mandate in self.observable_mandates:
            current_date = mandate.created_at + timedelta(days=30)
            end_date = start_date + timedelta(days=duration_days)
            
            lat_cust = self.latent_customers[mandate.customer_id]
            lat_merch = self.latent_merchants[mandate.merchant_id]
            
            while current_date < end_date:
                # Stop if mandate has expired/revoked before this execution attempt
                if mandate.expires_at and current_date > mandate.expires_at:
                    break
                
                noise_days = int(self.rng.gauss(0, lat_cust.timing_noise_std_dev))
                attempt_time = current_date + timedelta(days=noise_days)
                
                # Ensure chronological consistency
                if attempt_time < mandate.created_at:
                    attempt_time = mandate.created_at + timedelta(days=1)
                
                status, fail_cat = self.outcome_engine.execute_payment_attempt(
                    customer_latent=lat_cust,
                    merchant_latent=lat_merch,
                    amount=mandate.amount,
                    attempt_time=attempt_time,
                    is_retry=False
                )
                
                attempt = PaymentAttempt(
                    attempt_id=uuid4(),
                    mandate_id=mandate.mandate_id,
                    timestamp=attempt_time,
                    amount=mandate.amount,
                    status=status,
                    network_return_code=fail_cat
                )
                self.observable_events.append(attempt)
                
                # Apply historical retry schedule
                if status == AttemptStatus.FAILED:
                    for retry_offset in lat_merch.historical_retry_schedule:
                        retry_time = attempt_time + timedelta(days=retry_offset)
                        
                        if retry_time > end_date or (mandate.expires_at and retry_time > mandate.expires_at):
                            break
                            
                        r_status, r_fail_cat = self.outcome_engine.execute_payment_attempt(
                            customer_latent=lat_cust,
                            merchant_latent=lat_merch,
                            amount=mandate.amount,
                            attempt_time=retry_time,
                            is_retry=True
                        )
                        retry_attempt = PaymentAttempt(
                            attempt_id=uuid4(),
                            mandate_id=mandate.mandate_id,
                            timestamp=retry_time,
                            amount=mandate.amount,
                            status=r_status,
                            network_return_code=r_fail_cat
                        )
                        self.observable_events.append(retry_attempt)
                        if r_status == AttemptStatus.SUCCESS:
                            break  # stop retrying if successful
                
                current_date += timedelta(days=30)

