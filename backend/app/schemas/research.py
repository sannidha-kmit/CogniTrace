from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class StudentModelingMetrics(BaseModel):
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0


class AdaptiveAssessmentMetrics(BaseModel):
    concept_selection_accuracy: float = 0.0
    priority_prediction_accuracy: float = 0.0
    difficulty_adaptation_accuracy: float = 0.0


class QuestionQualityMetrics(BaseModel):
    grounding_rate: float = 0.0
    concept_relevance_rate: float = 0.0
    duplicate_rate: float = 0.0
    validation_acceptance_rate: float = 0.0
    total_validated: int = 0


class LearningGainMetrics(BaseModel):
    pre_test_score: Optional[float] = None
    post_test_score: Optional[float] = None
    learning_gain: Optional[float] = None  # post_test - pre_test
    concept_level_improvements: Dict[str, float] = Field(default_factory=dict)
    retention_score: Optional[float] = None


class ExperimentEvaluationReport(BaseModel):
    experiment_id: str
    preset_name: str
    student_modeling: StudentModelingMetrics
    adaptive_assessment: AdaptiveAssessmentMetrics
    question_quality: QuestionQualityMetrics
    learning_metrics: LearningGainMetrics
    total_sessions_analyzed: int
    ablation_comparison: Optional[Dict[str, Any]] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
