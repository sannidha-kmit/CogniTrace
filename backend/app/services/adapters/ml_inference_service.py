import os
import math
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.core.quiz_config import quiz_settings
from app.schemas.quiz import QuizPriorityEnum

logger = logging.getLogger("cognitrace.quiz.ml_inference")


class ModelPrediction(BaseModel):
    priority: QuizPriorityEnum
    score: float = Field(..., ge=0.0, le=1.0)
    raw_output: Any = None


class AdaptiveModelService:
    """
    Member 1 ML Model Inference Service.
    Enforces strict feature ordering, input validation, and model inference separation.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.getenv("ML_MODEL_PATH", "data/adaptive_quiz_model.joblib")
        self.model = None
        self.feature_order = quiz_settings.FEATURE_ORDER
        self._load_model_safe()

    def _load_model_safe(self) -> None:
        """Attempt to load trained scikit-learn/joblib model if available on disk."""
        if self.model_path and os.path.exists(self.model_path):
            try:
                import joblib
                self.model = joblib.load(self.model_path)
                logger.info("[MEMBER 1 ML SERVICE] Successfully loaded trained ML model from %s", self.model_path)
            except Exception as err:
                logger.warning(
                    "[MEMBER 1 ML SERVICE] Could not load model from %s: %s. Using deterministic fallback inference.",
                    self.model_path, err
                )
                self.model = None
        else:
            logger.info(
                "[MEMBER 1 ML SERVICE] Model file not found at '%s'. Using Member 1 deterministic inference engine.",
                self.model_path
            )
            self.model = None

    def validate_and_order_features(self, features: Dict[str, Any]) -> List[float]:
        """
        Validate presence and data types of features and return as ordered array.
        Prevents dictionary order non-determinism.
        """
        ordered_vector = []
        for feat_name in self.feature_order:
            if feat_name not in features:
                logger.warning("Missing feature '%s', defaulting to 0.0", feat_name)
                val = 0.0
            else:
                raw_val = features[feat_name]
                try:
                    val = float(raw_val)
                except (ValueError, TypeError):
                    raise ValueError(f"Feature '{feat_name}' has invalid non-numeric value: {raw_val}")
            ordered_vector.append(val)
        return ordered_vector

    def predict(self, features: Dict[str, Any]) -> ModelPrediction:
        """
        Inference interface for concept telemetry features.
        Accepts feature dict, validates feature order, runs model or deterministic ML calculation,
        and outputs priority + normalized score.
        """
        ordered_inputs = self.validate_and_order_features(features)

        # 1. If trained joblib model is loaded, execute model.predict / predict_proba
        if self.model is not None:
            try:
                import numpy as np
                input_array = np.array([ordered_inputs])
                if hasattr(self.model, "predict_proba"):
                    proba = self.model.predict_proba(input_array)[0]
                    # Score is probability of needing practice / high difficulty
                    score = float(proba[-1]) if len(proba) > 1 else float(proba[0])
                else:
                    raw_pred = self.model.predict(input_array)[0]
                    score = float(raw_pred) if isinstance(raw_pred, (int, float)) else 0.5

                # Bound score to [0.0, 1.0]
                score = max(0.0, min(1.0, score))
                priority = self._map_score_to_priority(score)
                return ModelPrediction(priority=priority, score=score, raw_output=score)
            except Exception as err:
                logger.error("[MEMBER 1 ML SERVICE] Model prediction failed: %s. Falling back to heuristic.", err)

        # 2. Deterministic ML Inference engine (Member 1 baseline formula)
        # Features: [replay_count, pause_count, seek_backward_count, seek_forward_count, understand_pause_count, difficulty_score]
        replay = ordered_inputs[0]
        pause = ordered_inputs[1]
        seek_back = ordered_inputs[2]
        seek_fwd = ordered_inputs[3]
        understand_pause = ordered_inputs[4]
        diff_score = ordered_inputs[5]

        # Calculate composite struggle / mastery score
        weighted_struggle = (
            (replay * 2.0) +
            (seek_back * 2.0) +
            (understand_pause * 3.0) +
            (diff_score * 1.5) +
            (pause * 0.5)
        )

        # Sigmoid normalization to 0.0 - 1.0 range (centered at 5.0 struggle)
        normalized_score = 1.0 / (1.0 + math.exp(-0.4 * (weighted_struggle - 5.0)))
        normalized_score = round(normalized_score, 4)

        priority = self._map_score_to_priority(normalized_score)
        return ModelPrediction(
            priority=priority,
            score=normalized_score,
            raw_output={"weighted_struggle": weighted_struggle}
        )

    def _map_score_to_priority(self, score: float) -> QuizPriorityEnum:
        """Map normalized score to HIGH, MEDIUM, LOW priority based on thresholds."""
        if score >= quiz_settings.PRIORITY_THRESHOLDS["HIGH"]:
            return QuizPriorityEnum.HIGH
        elif score >= quiz_settings.PRIORITY_THRESHOLDS["MEDIUM"]:
            return QuizPriorityEnum.MEDIUM
        else:
            return QuizPriorityEnum.LOW


ml_service = AdaptiveModelService()
