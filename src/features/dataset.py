import pandas as pd
from datetime import datetime
from typing import List, Tuple
from uuid import uuid4

from src.domain.models import CohortSnapshot, AttemptStatus, ActionType, CandidateAction
from src.features.builder import PointInTimeFeatureBuilder
from src.features.models import FeatureVector

class TrainingDatasetBuilder:
    def __init__(self, feature_version: str = "v1.0"):
        self.builder = PointInTimeFeatureBuilder(feature_version=feature_version)
        
    def build_from_snapshot(self, snapshot: CohortSnapshot) -> Tuple[List[FeatureVector], dict]:
        features = []
        
        # To generate training examples, we look at the observable history.
        # Any attempt that happened after a failure is a "retry".
        # We can reconstruct the "decision context" right before that retry,
        # treating the retry's timestamp as the `candidate_time` and its outcome as the `target`.
        
        # Group history by mandate
        history_by_mandate = {}
        for event in snapshot.initial_history:
            if event.mandate_id not in history_by_mandate:
                history_by_mandate[event.mandate_id] = []
            history_by_mandate[event.mandate_id].append(event)
            
        mandate_map = {m.mandate_id: m for m in snapshot.mandates}
        
        for mandate_id, events in history_by_mandate.items():
            events = sorted(events, key=lambda x: x.timestamp)
            mandate = mandate_map[mandate_id]
            
            # We need at least one failure to prompt a retry decision
            for i in range(1, len(events)):
                prev_event = events[i-1]
                curr_event = events[i]
                
                # If the previous event was a failure, the time right after it (e.g. 1ms later or just using prev_event.timestamp as cutoff)
                # is the decision time. The curr_event is the "candidate action" chosen.
                if prev_event.status == AttemptStatus.FAILED:
                    cutoff = prev_event.timestamp
                    candidate_action = CandidateAction(
                        candidate_id=uuid4(),
                        mandate_id=mandate_id,
                        action_type=ActionType.PAYMENT_RETRY,
                        scheduled_time=curr_event.timestamp,
                        amount=curr_event.amount,
                        source="historical_data"
                    )
                    
                    target = (curr_event.status == AttemptStatus.SUCCESS)
                    
                    vec = self.builder.build(
                        mandate=mandate,
                        candidate=candidate_action,
                        global_history=snapshot.initial_history,
                        global_mandates=snapshot.mandates,
                        cutoff_timestamp=cutoff,
                        target_success=target
                    )
                    
                    features.append(vec)
                    
        # Temporal Split setup
        if not features:
            return [], {}
            
        df = pd.DataFrame([f.model_dump() for f in features])
        df = df.sort_values(by="cutoff_timestamp")
        
        n = len(df)
        train_end = int(n * 0.7)
        val_end = int(n * 0.85)
        
        train_cutoff = df.iloc[train_end]['cutoff_timestamp'] if train_end < n else df.iloc[-1]['cutoff_timestamp']
        val_cutoff = df.iloc[val_end]['cutoff_timestamp'] if val_end < n else df.iloc[-1]['cutoff_timestamp']
        
        metadata = {
            "total_examples": n,
            "train_size": train_end,
            "validation_size": val_end - train_end,
            "test_size": n - val_end,
            "train_end_timestamp": train_cutoff.isoformat(),
            "validation_end_timestamp": val_cutoff.isoformat(),
            "feature_version": self.builder.feature_version
        }
        
        return features, metadata
