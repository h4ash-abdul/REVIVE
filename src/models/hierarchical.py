import pandas as pd
import numpy as np
from datetime import datetime, timezone
import uuid
from typing import List, Union

from src.models.config import HierarchicalConfig
from src.models.prediction import Prediction
from src.features.models import FeatureVector

class HierarchicalPredictor:
    def __init__(self, base_model, config: HierarchicalConfig = None):
        """
        base_model is expected to be a CalibratedWrapper or similar 
        that exposes predict_proba(X) and forbidden_columns.
        """
        self.base_model = base_model
        self.config = config or HierarchicalConfig()
        
        self.customer_features = [
            'hist_payment_count', 'hist_success_count', 'hist_failure_count', 
            'hist_success_rate', 'hist_amount_mean', 'hist_amount_std', 
            'history_depth_days', 'time_since_prev_success_hours', 
            'time_since_prev_failure_hours', 'hist_success_rate_hour_bucket', 
            'hist_success_rate_day_bucket', 'current_attempt_number'
        ]
        
        self.merchant_features = [
            'merchant_hist_payment_count', 'merchant_success_count', 
            'merchant_success_rate', 'merchant_history_depth_days', 
            'merchant_success_rate_hour_bucket'
        ]
        
    def determine_mode(self, row: pd.Series) -> str:
        """Determines the prediction mode based on observable history."""
        c_count = row.get('hist_payment_count', 0)
        m_count = row.get('merchant_hist_payment_count', 0)
        
        if c_count >= self.config.min_customer_history:
            return "customer"
        elif m_count >= self.config.min_merchant_history:
            return "merchant"
        # We assume if the model is running on the dataset, the dataset represents the population.
        # But we check against min_population_history using an approximation or external input.
        # For this point-in-time implementation, we'll assume population signal is generally sufficient
        # unless specifically instructed. For safety, if it's not merchant or customer, it's population.
        # In a real environment, population count would be known globally. We will just use 'population'
        # unless we explicitly decide it's a completely novel system (default).
        # We don't have a global count feature per row easily accessible right now, so we fallback to population.
        return "population"

    def predict(self, feature_vectors: Union[List[FeatureVector], pd.DataFrame]) -> List[Prediction]:
        if isinstance(feature_vectors, list):
            df = pd.DataFrame([fv.model_dump() for fv in feature_vectors])
        else:
            df = feature_vectors.copy()
            
        predictions = []
        
        # Iterate or vectorize. We will vectorize masking for performance, 
        # but build the Prediction objects by iteration.
        
        df['derived_mode'] = df.apply(self.determine_mode, axis=1)
        
        # Mask features
        X_eval = df.copy()
        
        # Mask customer features where mode is not customer
        not_customer_mask = X_eval['derived_mode'] != 'customer'
        for col in self.customer_features:
            if col in X_eval.columns:
                X_eval.loc[not_customer_mask, col] = np.nan
                
        # Mask merchant features where mode is population or default
        not_merchant_mask = (X_eval['derived_mode'] == 'population') | (X_eval['derived_mode'] == 'default')
        for col in self.merchant_features:
            if col in X_eval.columns:
                X_eval.loc[not_merchant_mask, col] = np.nan
                
        # Drop forbidden columns before sending to model
        if hasattr(self.base_model, 'forbidden_columns'):
            X_model = X_eval.drop(columns=self.base_model.forbidden_columns + ['derived_mode'], errors='ignore')
        else:
            X_model = X_eval.drop(columns=['derived_mode'], errors='ignore')
            
        # Get probabilities
        # Note: If mode is 'default', we override. Let's get model probabilities for all first, then override.
        base_probs = self.base_model.predict_proba(X_model)
        
        for idx in df.index:
            mode = df.loc[idx, 'derived_mode']
            c_id = df.loc[idx, 'candidate_id']
            
            if mode == 'default':
                prob = self.config.default_probability
            else:
                prob = float(base_probs.loc[idx])
                
            pred = Prediction(
                prediction_id=uuid.uuid4(),
                candidate_id=c_id,
                probability=prob,
                model_version="v1.0-hierarchical",
                feature_version=df.loc[idx, 'feature_version'],
                prediction_timestamp=datetime.now(timezone.utc),
                prediction_mode=mode
            )
            predictions.append(pred)
            
        return predictions
