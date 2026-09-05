import pytest
import pandas as pd
import numpy as np
from uuid import uuid4
from datetime import datetime, timezone

from src.models.config import HierarchicalConfig
from src.models.hierarchical import HierarchicalPredictor

class MockBaseModel:
    def __init__(self):
        self.forbidden_columns = ['forbidden1', 'forbidden2']
        
    def predict_proba(self, X):
        # Return probability 0.5 for everything
        return pd.Series([0.5] * len(X), index=X.index)

@pytest.fixture
def mock_df():
    return pd.DataFrame({
        'candidate_id': [uuid4() for _ in range(4)],
        'feature_version': ['v1.0'] * 4,
        'hist_payment_count': [5, 2, 0, 0],
        'merchant_hist_payment_count': [100, 100, 10, 0],
        'hist_amount_mean': [100.0, 100.0, 100.0, 100.0],
        'merchant_success_rate': [0.8, 0.8, 0.8, 0.8],
        'forbidden1': ['a', 'b', 'c', 'd']
    })

def test_mode_selection(mock_df):
    config = HierarchicalConfig(min_customer_history=3, min_merchant_history=50)
    predictor = HierarchicalPredictor(base_model=MockBaseModel(), config=config)
    
    # 0 -> Customer (5 >= 3)
    # 1 -> Merchant (2 < 3, 100 >= 50)
    # 2 -> Population (0 < 3, 10 < 50)
    
    preds = predictor.predict(mock_df)
    
    assert preds[0].prediction_mode == 'customer'
    assert preds[1].prediction_mode == 'merchant'
    assert preds[2].prediction_mode == 'population'
    assert preds[3].prediction_mode == 'population'

def test_feature_masking():
    # We will instrument the base model to record the X it received
    class InstrumentingBaseModel:
        def __init__(self):
            self.forbidden_columns = []
            self.received_X = None
            
        def predict_proba(self, X):
            self.received_X = X.copy()
            return pd.Series([0.5] * len(X), index=X.index)
            
    df = pd.DataFrame({
        'candidate_id': [uuid4()],
        'feature_version': ['v1.0'],
        'hist_payment_count': [1], # < 3, goes to merchant
        'merchant_hist_payment_count': [60], # >= 50
        'hist_amount_mean': [999.0],
        'merchant_success_rate': [0.8]
    })
    
    config = HierarchicalConfig(min_customer_history=3, min_merchant_history=50)
    model = InstrumentingBaseModel()
    predictor = HierarchicalPredictor(base_model=model, config=config)
    
    predictor.predict(df)
    
    X_received = model.received_X
    
    # hist_amount_mean should be masked to NaN because it's in merchant mode
    assert pd.isna(X_received.loc[0, 'hist_amount_mean'])
    
    # merchant_success_rate should remain intact
    assert X_received.loc[0, 'merchant_success_rate'] == 0.8
