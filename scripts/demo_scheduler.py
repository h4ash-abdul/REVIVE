import os
import json
import joblib
import pandas as pd
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domain.models import (
    Mandate, MandateStatus, PaymentAttempt, AttemptStatus, Customer, Merchant,
    PaymentObligation, ObligationStatus
)
from src.configs.models import PolicyConfig
from src.decision.policy import DeterministicPolicyEngine
from src.decision.generator import CandidateGenerator
from src.decision.scorer import CandidateScoringService
from src.decision.copilot import CopilotStrategy
from src.features.classifier import RuleBasedFailureClassifier
from src.features.builder import PointInTimeFeatureBuilder
from src.models.hierarchical import HierarchicalPredictor

def run_demo():
    print("==================================================")
    print("PHASE 7.1: SCHEDULER DEMO (FIXED STOP_ON_SUCCESS)")
    print("==================================================")
    
    # 1. Setup Mock Domain
    current_time = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    
    mandate = Mandate(
        mandate_id=uuid4(),
        customer_id=uuid4(),
        merchant_id=uuid4(),
        amount=150.0,
        status=MandateStatus.ACTIVE,
        created_at=current_time - timedelta(days=30)
    )
    
    # Give some customer history (say, 5 successful past payments) so they get Customer mode
    history = []
    for i in range(5):
        history.append(
            PaymentAttempt(
                attempt_id=uuid4(),
                mandate_id=mandate.mandate_id,
                timestamp=current_time - timedelta(days=28 - i*5),
                amount=150.0,
                status=AttemptStatus.SUCCESS
            )
        )
        
    # The most recent attempt is a failure
    last_failure = PaymentAttempt(
        attempt_id=uuid4(),
        mandate_id=mandate.mandate_id,
        timestamp=current_time - timedelta(hours=2),
        amount=150.0,
        status=AttemptStatus.FAILED,
        network_return_code="ERR_INSUFFICIENT_FUNDS"
    )
    history.append(last_failure)
    
    # Define the current payment obligation that failed
    current_obligation = PaymentObligation(
        obligation_id=uuid4(),
        mandate_id=mandate.mandate_id,
        due_time=last_failure.timestamp,
        amount=150.0,
        status=ObligationStatus.ACTIVE_RECOVERY,
        original_attempt_id=last_failure.attempt_id,
        retry_attempt_ids=[]
    )
    
    # 2. Setup Copilot Environment
    policy_config = PolicyConfig(
        policy_version="v1.0",
        max_retries_per_mandate=3,
        min_hours_between_retries=24,
        allowed_execution_windows_utc=["00:00-23:59"],
        stop_on_success=True  # Now we can leave this True!
    )
    policy_engine = DeterministicPolicyEngine(policy_config)
    generator = CandidateGenerator(days_ahead=3, hours_of_day=[9, 14, 20])
    classifier = RuleBasedFailureClassifier()
    feature_builder = PointInTimeFeatureBuilder()
    
    # Load Real Model v1.1
    print("Loading calibrated ML model (v1.1)...")
    with open("models/artifacts/model_manifest_v1.1.json", "r") as f:
        manifest = json.load(f)
    pipeline = joblib.load(manifest["artifact_path"])
    predictor = HierarchicalPredictor(base_model=pipeline)
    
    scorer = CandidateScoringService(feature_builder, predictor)
    
    copilot = CopilotStrategy(policy_engine, generator, scorer, classifier)
    
    # 3. Evaluate Decision
    print("\nRunning Intelligent Copilot Strategy...")
    result = copilot.evaluate(mandate, history, [mandate], current_time, current_obligation)
    
    print("\n==================================================")
    print("DECISION TRACE")
    print("==================================================")
    print(f"Mandate ID: {result.mandate_id}")
    print(f"Decision Timestamp: {current_time.isoformat()}")
    
    failure_class = classifier.classify(last_failure, mandate)
    print(f"Failure: {failure_class.category.value} (Retryable: {failure_class.retryable})")
    
    print("\nPolicy Pre-Filter Results:")
    valid_count = 0
    for dec in result.policy_decisions:
        if dec.checkpoint.value == "pre_filter":
            c_action = next((c for c in result.candidate_actions if c.candidate_id == dec.candidate_id), None)
            if c_action:
                status = "PASS" if dec.is_allowed else "REJECTED"
                print(f"  - {c_action.scheduled_time.strftime('%Y-%m-%d %H:%M')} -> {status} ({dec.reason})")
                if dec.is_allowed: valid_count += 1
                
    print(f"\nGenerated {len(result.candidate_actions)} total candidates.")
    print(f"Policy pre-filter passed {valid_count} candidates.")
    
    if result.selected_action:
        print("\nSelected candidate:")
        print(result.explanation)
        mode_str = result.prediction_mode.value if hasattr(result.prediction_mode, 'value') else str(result.prediction_mode)
        print(f"\nPrediction Mode: {mode_str}")
        print("Final Policy Check: PASS")
    else:
        print("\nNo action selected.")
        print(f"Stopping Reason: {result.stopping_reason}")

if __name__ == "__main__":
    run_demo()
