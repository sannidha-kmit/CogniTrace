from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


class GenerateQuestionsRequest(BaseModel):
    concept_identifier: Optional[str] = Field(None, description="Concept name or index within the course concept segments")
    concept_reference: Optional[str] = Field(None, description="Alias for concept_identifier")
    concept_id: Optional[str] = Field(None, description="Alias for concept_identifier")
    concept_name: Optional[str] = Field(None, description="Alias for concept_identifier")
    count: int = Field(3, ge=1, le=10, description="Number of questions to generate (1-10)")
    difficulty: Optional[str] = Field(None, description="Target difficulty level: EASY, MEDIUM, HARD (Optional)")

    @model_validator(mode="after")
    def resolve_concept_identifier(self):
        target = self.concept_identifier or self.concept_reference or self.concept_id or self.concept_name
        if not target:
            raise ValueError("One of 'concept_identifier', 'concept_reference', 'concept_id', or 'concept_name' must be provided.")
        self.concept_identifier = target
        return self


class GeneratedMCQ(BaseModel):
    question: str = Field(..., description="The multiple choice question text")
    options: List[str] = Field(..., description="List of exactly 4 choices")
    correct_answer: str = Field(..., description="The correct answer text matching exactly one option")
    difficulty: str = Field("MEDIUM", description="Difficulty level: EASY, MEDIUM, or HARD")
    explanation: str = Field(..., description="Detailed explanation based strictly on transcript content")
    concept: str = Field(..., description="The concept this question addresses")
    learning_point: Optional[str] = Field(None, description="Specific learning point tested by the question")
    source_evidence: Optional[str] = Field(None, description="Exact factual evidence from the concept transcript")

    @field_validator("options")
    @classmethod
    def validate_options_count(cls, v: List[str]) -> List[str]:
        if len(v) != 4:
            raise ValueError("MCQ must contain exactly 4 options.")
        return v

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer_in_options(cls, v: str, info) -> str:
        options = info.data.get("options", [])
        if options and v not in options:
            raise ValueError("correct_answer must match one of the 4 options exactly.")
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty_value(cls, v: str) -> str:
        upper = v.upper()
        if upper not in ["EASY", "MEDIUM", "HARD"]:
            return "MEDIUM"
        return upper


class TeacherQuestionResponse(BaseModel):
    id: str
    course_id: str
    concept_ref: str
    concept_name: str
    question: str
    options: List[str]
    correct_answer: str
    difficulty: str
    explanation: str
    created_at: datetime


class StudentQuestionResponse(BaseModel):
    id: str
    course_id: str
    concept_ref: str
    concept_name: str
    question: str
    options: List[str]
    difficulty: str
    # Security Rule: correct_answer and explanation MUST NOT be included for students before submission!


class QuestionSubmissionRequest(BaseModel):
    selected_option: str = Field(..., description="Option selected by student")


class QuestionSubmissionResponse(BaseModel):
    question_id: str
    is_correct: bool
    correct_answer: str
    explanation: str


class TeacherQuestionListResponse(BaseModel):
    course_id: str
    concept_ref: Optional[str] = None
    concept_name: Optional[str] = None
    total: int
    questions: List[TeacherQuestionResponse]


class StudentQuestionListResponse(BaseModel):
    course_id: str
    concept_ref: Optional[str] = None
    concept_name: Optional[str] = None
    total: int
    questions: List[StudentQuestionResponse]
