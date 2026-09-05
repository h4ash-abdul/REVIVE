from typing import List, Optional
from datetime import datetime

from src.domain.models import (
    Mandate, PaymentAttempt, AttemptStatus, StrategyResult, 
    PredictionMode, PolicyDecision, PolicyCheckpoint, PaymentObligation
)
from src.features.classifier import RuleBasedFailureClassifier
from src.decision.policy import DeterministicPolicyEngine
from src.decision.generator import CandidateGenerator
from src.decision.scorer import CandidateScoringService

class CopilotStrategy:
    def __init__(
        self,
        policy_engine: DeterministicPolicyEngine,
        generator: CandidateGenerator,
        scorer: CandidateScoringService,
        classifier: RuleBasedFailureClassifier
    ):
        self.policy_engine = policy_engine
        self.generator = generator
        self.scorer = scorer
        self.classifier = classifier
        self.version = "v1.0"
        
    def evaluate(
        self, 
        mandate: Mandate, 
        history: List[PaymentAttempt], 
        global_mandates: List[Mandate],
        current_time: datetime,
        current_obligation: PaymentObligation = None
    ) -> StrategyResult:
        
        # 1. Failure Analysis (Failure Safety)
        mandate_history = sorted([e for e in history if e.mandate_id == mandate.mandate_id], key=lambda x: x.timestamp)
        failed_attempts = [e for e in mandate_history if e.status == AttemptStatus.FAILED]
        
        if not failed_attempts:
            return self._stop_decision(mandate, "No failures found to recover.")
            
        last_failure = failed_attempts[-1]
        classification = self.classifier.classify(last_failure, mandate)
        
        if not classification.retryable:
            return self._stop_decision(mandate, f"Failure not retryable: {classification.category.value}")
            
        # 2. Candidate Generation
        all_candidates = self.generator.generate(mandate, current_time, source_id="copilot_ml")
        
        # 3. Policy Pre-Filter
        pre_filter_decisions = self.policy_engine.pre_filter(all_candidates, mandate, history, current_obligation)
        valid_candidate_ids = {d.candidate_id for d in pre_filter_decisions if d.is_allowed}
        valid_candidates = [c for c in all_candidates if c.candidate_id in valid_candidate_ids]
        
        if not valid_candidates:
            return self._stop_decision(
                mandate, 
                "No policy-compliant candidate windows available.", 
                candidates=all_candidates, 
                decisions=pre_filter_decisions
            )
            
        # 4. Point-In-Time Scoring
        predictions_map = self.scorer.score_candidates(
            candidates=valid_candidates,
            mandate=mandate,
            history=history,
            global_mandates=global_mandates,
            decision_time=current_time
        )
        
        # 5. Ranking and Selection
        # Sort descending by probability
        ranked_candidates = sorted(
            valid_candidates, 
            key=lambda c: predictions_map[c.candidate_id].probability, 
            reverse=True
        )
        
        best_candidate = ranked_candidates[0]
        best_prediction = predictions_map[best_candidate.candidate_id]
        
        # 6. Final Policy Validation (Safety Double-Check before execution)
        final_decisions = self.policy_engine.final_validate([best_candidate], mandate, history, current_obligation)
        final_decision = final_decisions[0]
        
        all_decisions = pre_filter_decisions + final_decisions
        
        if not final_decision.is_allowed:
            return self._stop_decision(
                mandate, 
                f"Selected candidate failed final validation: {final_decision.reason}",
                candidates=all_candidates,
                decisions=all_decisions
            )
            
        # Compile Explanation
        alt_texts = []
        for c in ranked_candidates[1:4]: # Show top 3 alternatives
            prob = predictions_map[c.candidate_id].probability
            alt_texts.append(f"{c.scheduled_time.strftime('%Y-%m-%d %H:%M')} -> {prob:.2f}")
            
        explanation = f"Highest predicted recovery probability among policy-valid candidates.\n"
        explanation += f"Selected: {best_candidate.scheduled_time.strftime('%Y-%m-%d %H:%M')} (prob: {best_prediction.probability:.2f})\n"
        if alt_texts:
            explanation += f"Alternatives:\n" + "\n".join(alt_texts)

        return StrategyResult(
            strategy_name="CopilotML",
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=best_candidate,
            retry_plan=[best_candidate], # MVP: just returns the single best next action
            selected_time=best_candidate.scheduled_time,
            candidate_actions=all_candidates,
            explanation=explanation,
            prediction_mode=best_prediction.prediction_mode,
            policy_decisions=all_decisions,
            stopping_reason=None
        )

    def _stop_decision(
        self, 
        mandate: Mandate, 
        reason: str, 
        candidates: List = None, 
        decisions: List = None
    ) -> StrategyResult:
        return StrategyResult(
            strategy_name="CopilotML",
            strategy_version=self.version,
            mandate_id=mandate.mandate_id,
            selected_action=None,
            retry_plan=[],
            selected_time=None,
            candidate_actions=candidates or [],
            explanation=reason,
            prediction_mode=None,
            policy_decisions=decisions or [],
            stopping_reason=reason
        )
