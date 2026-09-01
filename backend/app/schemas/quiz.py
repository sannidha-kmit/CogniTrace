from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class QuizDifficultyEnum(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuizPriorityEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class QuizSessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ConceptFeatureData(BaseModel):
    concept_id: str
    concept_name: str
    features: Dict[str, float] = Field(default_factory=dict)


class ConceptPriority(BaseModel):
    concept_id: str
    concept_name: str
    priority: QuizPriorityEnum
    score: float = Field(..., ge=0.0, le=1.0)
    allocated_count: int = Field(0, ge=0)


class SafeQuizQuestion(BaseModel):
    quiz_session_id: str
    question_id: str
    concept_id: str
    concept_name: str
    question_text: str
    options: List[str]
    difficulty: str
    question_number: int
    total_questions: int


class RevisionResource(BaseModel):
    video_id: Optional[str] = None
    video_title: str
    video_url: str
    timestamp_seconds: Optional[int] = None
    timestamp_display: Optional[str] = None
    revision_url: str


class LearningSupport(BaseModel):
    concept_id: str
    concept_name: str
    explanation: Optional[str] = None
    explanation_status: str = "available"  # "available", "cached", "unavailable"
    revision: Optional[RevisionResource] = None


class InternalQuizQuestion(BaseModel):
    question_id: str
    concept_id: str
    concept_name: str
    question_text: str
    options: List[str]
    correct_answer: str
    difficulty: str
    explanation: Optional[str] = None
    answered: bool = False
    selected_option: Optional[str] = None
    is_correct: Optional[bool] = None
    answered_at: Optional[datetime] = None
    learning_support: Optional[LearningSupport] = None


class StartQuizRequest(BaseModel):
    course_id: str = Field(..., description="Target Course ID for the quiz")
    total_questions: Optional[int] = Field(10, ge=3, le=30, description="Total questions for the quiz session")


class StartQuizResponse(BaseModel):
    quiz_session_id: str
    course_id: str
    student_id: str
    status: QuizSessionStatus
    current_question: SafeQuizQuestion
    question_number: int
    total_questions: int
    started_at: datetime


class CurrentQuestionResponse(BaseModel):
    quiz_session_id: str
    question: SafeQuizQuestion
    question_number: int
    total_questions: int
    answered_questions: int
    status: QuizSessionStatus


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(..., description="ID of the question being answered")
    answer: str = Field(..., description="Selected option text or letter")


class SubmitAnswerResponse(BaseModel):
    quiz_session_id: str
    question_id: str
    is_correct: bool
    answered_questions: int
    remaining_questions: int
    total_questions: int
    current_score: float
    is_completed: bool
    feedback: Optional[str] = None
    correct_answer: Optional[str] = None  # Safely revealed only AFTER submission
    explanation: Optional[str] = None
    learning_support: Optional[LearningSupport] = None


class ExplanationResponse(BaseModel):
    """Response for re-fetching explanation after answer submission."""
    quiz_session_id: str
    question_id: str
    is_correct: bool
    learning_support: Optional[LearningSupport] = None


class FinishQuizResponse(BaseModel):
    quiz_session_id: str
    student_id: str
    course_id: str
    status: QuizSessionStatus
    total_questions: int
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    score_percentage: float
    completed_at: datetime


class ConceptResultBreakdown(BaseModel):
    concept_id: str
    concept_name: str
    priority: str
    total_questions: int
    correct_answers: int
    accuracy_percentage: float


class QuizResultResponse(BaseModel):
    quiz_session_id: str
    student_id: str
    course_id: str
    status: QuizSessionStatus
    total_questions: int
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    score_percentage: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    concept_breakdown: List[ConceptResultBreakdown] = Field(default_factory=list)
