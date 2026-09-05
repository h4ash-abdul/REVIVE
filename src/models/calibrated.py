import pandas as pd

class CalibratedWrapper:
    def __init__(self, base_pipe, calibrator, method):
        self.base_pipe = base_pipe
        self.calibrator = calibrator
        self.method = method
        
    def predict_proba(self, X):
        base_preds = self.base_pipe.predict_proba(X)
        if self.method == 'sigmoid':
            calib_preds = self.calibrator.predict_proba(base_preds.to_numpy().reshape(-1, 1))[:, 1]
        else:
            calib_preds = self.calibrator.predict(base_preds)
        return pd.Series(calib_preds, index=X.index)
        
    @property
    def forbidden_columns(self):
        return self.base_pipe.forbidden_columns
        
    def get_coefficients(self):
        return self.base_pipe.get_coefficients()
