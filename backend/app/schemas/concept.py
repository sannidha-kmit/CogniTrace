from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ConceptSegmentItem(BaseModel):
    Concept: str = Field(..., description="Educational Concept Name e.g. Arrays, Binary Search")
    ConceptStart: str = Field(..., description="Concept start timestamp string e.g. 00:00")
    ConceptEnd: str = Field(..., description="Concept end timestamp string e.g. 02:00")
    Prerequisite: Optional[str] = Field("None", description="Prerequisite concept name or None")
    DifficultyLevel: str = Field("Easy", description="Intrinsic content difficulty: Easy, Medium, Hard")


class ConceptResponse(BaseModel):
    id: str
    course_id: str
    course_name: str
    subject: str
    teacher_id: str
    teacher_name: str
    status: str = Field(..., description="Processing status: NOT_GENERATED, PENDING, PROCESSING, COMPLETED, FAILED")
    segments: List[ConceptSegmentItem] = []
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConceptStatusResponse(BaseModel):
    course_id: str
    status: str
    concept_count: int = 0
    error_message: Optional[str] = None
