import pytest
import pandas as pd
import numpy as np
from uuid import uuid4
from datetime import datetime, timezone

from src.models.pipeline import RecoveryPredictionPipeline

@pytest.fixture
def mock_data():
    df = pd.DataFrame({
        'target_success': [True, False, True, False, True],
        'mandate_id': [uuid4() for _ in range(5)],
        'candidate_id': [uuid4() for _ in range(5)],
        'customer_id': [uuid4() for _ in range(5)],
        'merchant_id': [uuid4() for _ in range(5)],
        'candidate_hour': [1, 2, 3, 4, 5],
        'candidate_weekday': [0, 1, 2, 3, 4],
        'candidate_day_of_month': [1, 2, 3, 4, 5],
        'time_until_candidate_hours': [24.0, 48.0, 12.0, 6.0, 1.0],
        'hist_payment_count': [1, 2, 3, 4, 5],
        'hist_success_count': [1, 1, 2, 2, 3],
        'hist_failure_count': [0, 1, 1, 2, 2],
        'hist_success_rate': [1.0, 0.5, 0.66, 0.5, 0.6],
        'hist_amount_mean': [100.0, 150.0, 200.0, 250.0, 300.0],
        'hist_amount_std': [0.0, 10.0, 20.0, 30.0, 40.0],
        'history_depth_days': [10.0, 20.0, 30.0, 40.0, 50.0],
        'time_since_prev_success_hours': [24.0, 48.0, np.nan, 12.0, 6.0],
        'time_since_prev_failure_hours': [np.nan, 24.0, 48.0, 12.0, 6.0],
        'hist_success_rate_hour_bucket': [1.0, np.nan, 0.5, 1.0, 0.0],
        'hist_success_rate_day_bucket': [np.nan, 1.0, 0.0, 0.5, 1.0],
        'amount': [100.0, 200.0, 300.0, 400.0, 500.0],
        'mandate_age_days': [10.0, 20.0, 30.0, 40.0, 50.0],
        'current_attempt_number': [2, 3, 4, 5, 6],
        'merchant_hist_payment_count': [100, 200, 300, 400, 500],
        'merchant_success_count': [50, 100, 150, 200, 250],
        'merchant_success_rate': [0.5, 0.5, 0.5, 0.5, 0.5],
        'merchant_history_depth_days': [100.0, 200.0, 300.0, 400.0, 500.0],
        'merchant_success_rate_hour_bucket': [0.5, 0.4, 0.6, 0.5, 0.4],
        'failure_category': ['technical_failure', 'insufficient_funds', 'UNKNOWN', 'risk_or_policy_decline', 'insufficient_funds'],
        'raw_network_return_code': ['CODE_1', 'CODE_2', None, 'CODE_4', 'CODE_2'],
        'true_payday': [1, 2, 3, 4, 5],
        'feature_version': ['v1.0'] * 5,
        'prediction_mode': ['DEFAULT'] * 5,
        'cutoff_timestamp': [datetime.now(timezone.utc)] * 5,
        'generated_at': [datetime.now(timezone.utc)] * 5
    })
    return df

def test_pipeline_leakage_protection(mock_data):
    pipeline = RecoveryPredictionPipeline()
    y = mock_data['target_success']
    
    # Passing X with target column should raise ValueError
    with pytest.raises(ValueError, match="Leakage detected"):
        pipeline.fit(mock_data, y)
        
    # Drop target but leave mandate_id
    X_bad = mock_data.drop(columns=['target_success'])
    with pytest.raises(ValueError, match="Leakage detected"):
        pipeline.fit(X_bad, y)
        
    # Drop all forbidden columns
    X_good = X_bad.drop(columns=pipeline.forbidden_columns, errors='ignore')
    pipeline.fit(X_good, y) # Should succeed
    
def test_pipeline_predict_bounds(mock_data):
    pipeline = RecoveryPredictionPipeline()
    y = mock_data['target_success']
    X = mock_data.drop(columns=pipeline.forbidden_columns, errors='ignore').drop(columns=['target_success'], errors='ignore')
    
    pipeline.fit(X, y)
    probs = pipeline.predict_proba(X)
    
    assert (probs >= 0.0).all()
    assert (probs <= 1.0).all()

def test_deterministic_preprocessing(mock_data):
    p1 = RecoveryPredictionPipeline(random_state=42)
    p2 = RecoveryPredictionPipeline(random_state=42)
    
    y = mock_data['target_success']
    X = mock_data.drop(columns=p1.forbidden_columns, errors='ignore').drop(columns=['target_success'], errors='ignore')
    
    p1.fit(X, y)
    p2.fit(X, y)
    
    prob1 = p1.predict_proba(X)
    prob2 = p2.predict_proba(X)
    
    pd.testing.assert_series_equal(prob1, prob2)
