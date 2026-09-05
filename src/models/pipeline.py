import pandas as pd
import numpy as np
from typing import List, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from src.models.config import HierarchicalConfig

class RecoveryPredictionPipeline:
    def __init__(self, random_state: int = 42, config: HierarchicalConfig = None):
        self.random_state = random_state
        self.config = config or HierarchicalConfig()
        self.model = None
        self.pipeline = None
        
        # Define feature columns
        self.numeric_features = [
            'candidate_hour', 'candidate_weekday', 'candidate_day_of_month',
            'time_until_candidate_hours', 'hist_payment_count', 'hist_success_count',
            'hist_failure_count', 'hist_success_rate', 'hist_amount_mean', 'hist_amount_std',
            'history_depth_days', 'time_since_prev_success_hours', 'time_since_prev_failure_hours',
            'hist_success_rate_hour_bucket', 'hist_success_rate_day_bucket',
            'amount', 'mandate_age_days', 'current_attempt_number',
            'merchant_hist_payment_count', 'merchant_success_count', 'merchant_success_rate',
            'merchant_history_depth_days', 'merchant_success_rate_hour_bucket'
        ]
        
        self.categorical_features = [
            'failure_category', 'raw_network_return_code', 'prediction_mode'
        ]
        
        # Columns strictly forbidden from X to prevent leakage
        self.forbidden_columns = [
            'target_success', 'mandate_id', 'candidate_id', 'customer_id',
            'merchant_id', 'true_payday', 'drift_level', 'archetype',
            'feature_version', 'generated_at', 'cutoff_timestamp'
        ]
        
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

    def __setstate__(self, state):
        self.__dict__.update(state)
        if not hasattr(self, 'config'):
            self.config = HierarchicalConfig()
        if not hasattr(self, 'customer_features'):
            self.customer_features = [
                'hist_payment_count', 'hist_success_count', 'hist_failure_count', 
                'hist_success_rate', 'hist_amount_mean', 'hist_amount_std', 
                'history_depth_days', 'time_since_prev_success_hours', 
                'time_since_prev_failure_hours', 'hist_success_rate_hour_bucket', 
                'hist_success_rate_day_bucket', 'current_attempt_number'
            ]
        if not hasattr(self, 'merchant_features'):
            self.merchant_features = [
                'merchant_hist_payment_count', 'merchant_success_count', 
                'merchant_success_rate', 'merchant_history_depth_days', 
                'merchant_success_rate_hour_bucket'
            ]

    def _determine_mode(self, row: pd.Series) -> str:
        c_count = row.get('hist_payment_count', 0)
        if pd.isna(c_count):
            c_count = 0
            
        m_count = row.get('merchant_hist_payment_count', 0)
        if pd.isna(m_count):
            m_count = 0
            
        config = getattr(self, 'config', None) or HierarchicalConfig()
        
        if c_count >= config.min_customer_history:
            return "customer"
        elif m_count >= config.min_merchant_history:
            return "merchant"
        return "population"
        
    def _mask_hierarchical_features(self, X: pd.DataFrame) -> pd.DataFrame:
        X_masked = X.copy()
        
        if 'prediction_mode' not in X_masked.columns:
            X_masked['prediction_mode'] = 'UNKNOWN'
            
        X_masked['prediction_mode'] = X_masked.apply(self._determine_mode, axis=1)
        
        not_customer_mask = X_masked['prediction_mode'] != 'customer'
        for col in self.customer_features:
            if col in X_masked.columns:
                X_masked.loc[not_customer_mask, col] = np.nan
                
        not_merchant_mask = (X_masked['prediction_mode'] == 'population') | (X_masked['prediction_mode'] == 'default')
        for col in self.merchant_features:
            if col in X_masked.columns:
                X_masked.loc[not_merchant_mask, col] = np.nan
                
        return X_masked

    def _build_pipeline(self):
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features)
            ]
        )
        
        self.pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', LogisticRegression(random_state=self.random_state, max_iter=1000, class_weight='balanced'))
        ])

    def _check_leakage(self, X: pd.DataFrame):
        for col in self.forbidden_columns:
            if col in X.columns:
                raise ValueError(f"Leakage detected: Column '{col}' is present in the feature matrix.")

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self._check_leakage(X)
        X_masked = self._mask_hierarchical_features(X)
        if self.pipeline is None:
            self._build_pipeline()
            
        self.pipeline.fit(X_masked, y)
        
    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        self._check_leakage(X)
        X_masked = self._mask_hierarchical_features(X)
        
        probas = self.pipeline.predict_proba(X_masked)[:, 1]
        return pd.Series(probas, index=X.index)
        
    def get_feature_names(self) -> List[str]:
        if self.pipeline is None:
            return []
        
        preprocessor = self.pipeline.named_steps['preprocessor']
        
        num_features = self.numeric_features.copy()
        if 'num' in preprocessor.named_transformers_:
            num_imputer = preprocessor.named_transformers_['num'].named_steps['imputer']
            # add_indicator=True adds indicator features
            if hasattr(num_imputer, 'indicator_') and num_imputer.indicator_ is not None:
                indicator_indices = num_imputer.indicator_.features_
                for idx in indicator_indices:
                    num_features.append(f"missingindicator_{self.numeric_features[idx]}")
                    
        cat_features = []
        if 'cat' in preprocessor.named_transformers_:
            cat_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
            cat_features = list(cat_encoder.get_feature_names_out(self.categorical_features))
            
        return num_features + cat_features
        
    def get_coefficients(self) -> dict:
        if self.pipeline is None:
            return {}
            
        feature_names = self.get_feature_names()
        classifier = self.pipeline.named_steps['classifier']
        
        if not hasattr(classifier, 'coef_'):
            return {}
            
        coefs = classifier.coef_[0]
        return dict(zip(feature_names, coefs))
