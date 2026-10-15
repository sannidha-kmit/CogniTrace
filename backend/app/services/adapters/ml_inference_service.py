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
        self.model_path = model_path
        self.model = None
        self.feature_order = quiz_settings.FEATURE_ORDER
        self._load_model_safe()

    def _load_model_safe(self) -> None:
        """Attempt to load trained scikit-learn/joblib model if available on disk."""
        candidate_paths = [
            self.model_path,
            os.getenv("ML_MODEL_PATH"),
            "models/adaptive_quiz_model.pkl",
            "../models/adaptive_quiz_model.pkl",
            "backend/models/adaptive_quiz_model.pkl",
            "data/adaptive_quiz_model.joblib"
        ]
        chosen_path = next((p for p in candidate_paths if p and os.path.exists(p)), None)

        if chosen_path:
            try:
                import joblib
                loaded = joblib.load(chosen_path)
                if isinstance(loaded, dict) and "model" in loaded:
                    self.model = loaded["model"]
                    if "feature_names" in loaded:
                        self.feature_order = loaded["feature_names"]
                else:
                    self.model = loaded
                self.model_path = chosen_path
                logger.info("[ADAPTIVE ML SERVICE] Successfully loaded production ML model from %s", chosen_path)
            except Exception as err:
                logger.warning(
                    "[ADAPTIVE ML SERVICE] Could not load model from %s: %s. Using deterministic fallback inference.",
                    chosen_path, err
                )
                self.model = None
        else:
            logger.info(
                "[ADAPTIVE ML SERVICE] Model file not found. Using deterministic fallback inference engine."
            )
            self.model = None

    def validate_and_order_features(self, features: Dict[str, Any]) -> List[float]:
        """
        Validate presence and data types of the exact 6 features and return as ordered array:
        [backward_count, replay_count, study_pause_count, other_work_pause_count, forward_count, speed_increase_count]
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
        Accepts feature dict, validates feature order, runs production model or deterministic fallback calculation,
        and outputs priority (HIGH/MEDIUM/LOW) + confidence score.
        """
        ordered_inputs = self.validate_and_order_features(features)

        # 1. If trained joblib model is loaded, execute model.predict / predict_proba
        if self.model is not None:
            try:
                import numpy as np
                import pandas as pd
                
                df_input = pd.DataFrame([ordered_inputs], columns=self.feature_order)
                raw_pred = self.model.predict(df_input)[0]
                pred_label = str(raw_pred).upper().strip()

                # Model confidence from predict_proba
                confidence = 1.0
                if hasattr(self.model, "predict_proba"):
                    proba = self.model.predict_proba(df_input)[0]
                    confidence = float(np.max(proba))

                # Bound confidence to [0.0, 1.0]
                confidence = max(0.0, min(1.0, confidence))

                # Map directly to QuizPriorityEnum
                try:
                    priority = QuizPriorityEnum(pred_label)
                except ValueError:
                    priority = self._map_score_to_priority(confidence)

                return ModelPrediction(
                    priority=priority,
                    score=confidence,
                    raw_output={"prediction": pred_label, "confidence": confidence}
                )
            except Exception as err:
                logger.error("[ADAPTIVE ML SERVICE] Model prediction failed: %s. Falling back to heuristic.", err)

        # 2. Deterministic ML Fallback Inference engine
        # Features: [backward_count, replay_count, study_pause_count, other_work_pause_count, forward_count, speed_increase_count]
        backward = ordered_inputs[0]
        replay = ordered_inputs[1]
        study_pause = ordered_inputs[2]
        other_work_pause = ordered_inputs[3]
        forward = ordered_inputs[4]
        speed_increase = ordered_inputs[5]

        # Forward_count and speed_increase_count must NOT be treated as difficulty.
        # Backward, replay, and study-pause represent evidence of needing more revision.
        weighted_struggle = (
            (backward * 2.0) +
            (replay * 2.0) +
            (study_pause * 3.0)
        )

        normalized_score = 1.0 / (1.0 + math.exp(-0.4 * (weighted_struggle - 5.0)))
        normalized_score = round(normalized_score, 4)

        if weighted_struggle >= 7.0:
            priority = QuizPriorityEnum.HIGH
        elif weighted_struggle >= 3.0:
            priority = QuizPriorityEnum.MEDIUM
        else:
            priority = QuizPriorityEnum.LOW

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
