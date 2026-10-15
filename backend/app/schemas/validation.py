from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class QuestionValidationResult(BaseModel):
    """
    Validation audit record for generated questions.
    """
    question_id: str
    course_id: str
    concept_id: str
    concept_name: str
    target_difficulty: str

    # Structural Validation
    options_count_valid: bool = True  # Exactly 4 options
    single_correct_valid: bool = True  # Exactly 1 correct answer
    required_fields_present: bool = True

    # Semantic Validation
    grounded_in_transcript: bool = True
    concept_relevant: bool = True
    correct_answer_valid: bool = True
    distractors_plausible: bool = True
    difficulty_matched: bool = True

    # Quality Validation
    duplicate: bool = False
    no_answer_leakage: bool = True
    clarity_valid: bool = True

    # Aggregated Score
    validation_score: float = 1.0  # 0.0 to 1.0
    status: str = "approved"  # "approved", "rejected", "flagged"
    rejection_reasons: List[str] = Field(default_factory=list)

    validated_at: datetime = Field(default_factory=datetime.utcnow)
