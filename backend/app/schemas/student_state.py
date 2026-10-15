from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ConceptStateResponse(BaseModel):
    """
    Concept-level student state containing both behavioral evidence
    and assessment evidence.
    """
    student_id: str
    course_id: str
    concept_id: str
    concept_name: str

    # Behavioral Evidence
    evidence_score: float = 0.0
    normalized_behavioral_evidence: float = 0.0
    interaction_evidence: Dict[str, float] = Field(default_factory=dict)
    raw_event_counts: Dict[str, int] = Field(default_factory=dict)

    # Assessment Evidence & Mastery
    quiz_attempts: int = 0
    correct_answers: int = 0
    incorrect_answers: int = 0
    mastery_score: Optional[float] = None
    is_mastery_known: bool = False
    knowledge_gap: float = 0.5  # 1 - mastery, or 0.5 if unknown
    recent_performance: List[bool] = Field(default_factory=list)

    # Integrated Research Priority
    ml_priority: str = "MEDIUM"  # "HIGH", "MEDIUM", "LOW"
    ml_score: float = 0.5
    research_priority_score: float = 0.5
    final_priority_label: str = "MEDIUM"
    target_difficulty: str = "MEDIUM"

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class StudentCourseConceptStatesResponse(BaseModel):
    """
    All concept states for a student in a course.
    """
    student_id: str
    course_id: str
    course_name: Optional[str] = None
    concepts: List[ConceptStateResponse]
    overall_mastery_average: Optional[float] = None
    total_evidence_sum: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
