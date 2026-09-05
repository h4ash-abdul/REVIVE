from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID

from src.domain.models import CandidateAction, Mandate, PaymentAttempt, Prediction
from src.features.builder import PointInTimeFeatureBuilder
from src.models.hierarchical import HierarchicalPredictor

class CandidateScoringService:
    def __init__(self, feature_builder: PointInTimeFeatureBuilder, predictor: HierarchicalPredictor):
        self.feature_builder = feature_builder
        self.predictor = predictor
        
    def score_candidates(
        self,
        candidates: List[CandidateAction],
        mandate: Mandate,
        history: List[PaymentAttempt],
        global_mandates: List[Mandate],
        decision_time: datetime
    ) -> Dict[UUID, Prediction]:
        """
        Builds features and scores each valid candidate.
        Returns a mapping of candidate_id -> Prediction.
        """
        if not candidates:
            return {}
            
        feature_vectors = []
        
        for candidate in candidates:
            # Important: The builder uses decision_time as the strict cutoff
            fv = self.feature_builder.build(
                mandate=mandate,
                candidate=candidate,
                global_history=history,
                global_mandates=global_mandates,
                cutoff_timestamp=decision_time
            )
            feature_vectors.append(fv)
            
        predictions = self.predictor.predict(feature_vectors)
        
        return {pred.candidate_id: pred for pred in predictions}
