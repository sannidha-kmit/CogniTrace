from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    TranscriptStart: str = Field(..., description="Formatted start timestamp string e.g. 00:00")
    TranscriptEnd: str = Field(..., description="Formatted end timestamp string e.g. 00:15")


class TranscriptResponse(BaseModel):
    id: str
    course_id: str
    course_name: str
    subject: str
    teacher_id: str
    teacher_name: str
    youtube_url: str
    status: str = Field(..., description="NOT_GENERATED, PENDING, PROCESSING, COMPLETED, FAILED")
    progress: int = Field(0, description="Real-time progress percentage (0-100)")
    stage: Optional[str] = Field("NOT_STARTED", description="Current stage e.g. TRANSCRIBING")
    message: Optional[str] = None
    processed_seconds: float = 0.0
    total_duration_seconds: float = 0.0
    language: Optional[str] = "en"
    segments: List[TranscriptSegment] = []
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TranscriptStatusResponse(BaseModel):
    course_id: str
    status: str
    progress: int = 0
    stage: Optional[str] = "NOT_STARTED"
    message: Optional[str] = None
    processed_seconds: float = 0.0
    total_duration_seconds: float = 0.0
    completed: bool = False
    language: Optional[str] = None
    segment_count: int = 0
    error_message: Optional[str] = None
