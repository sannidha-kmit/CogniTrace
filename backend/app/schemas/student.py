from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

VALID_EVENT_TYPES = [
    "PLAY",
    "PAUSE",
    "SEEK_FORWARD",
    "SEEK_BACKWARD",
    "REPLAY",
    "SPEED_CHANGE",
    "VIDEO_COMPLETE"
]


class TeacherSubjectResponse(BaseModel):
    teacher_id: str
    teacher_name: str
    subject: str
    year: str


class StudentCourseResponse(BaseModel):
    id: str
    course_name: str
    youtube_url: str
    subject: str
    teacher_id: str
    teacher_name: str
    year: str
    created_at: datetime


class InteractionEventCreate(BaseModel):
    course_id: str = Field(..., description="Target Course Object ID")
    event_type: str = Field(..., description="Event Type (PLAY, PAUSE, SEEK_FORWARD, SEEK_BACKWARD, REPLAY, SPEED_CHANGE, VIDEO_COMPLETE)")
    event_timestamp: str = Field(..., description="Video playback timestamp position e.g. 02:15")
    event_duration: Optional[float] = Field(None, description="Pause duration in seconds (if applicable)")
    playback_speed: Optional[float] = Field(None, description="Playback speed multiplier (if applicable)")
    pause_reason: Optional[str] = Field(None, description="Pause reason text (if applicable)")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid EventType. Must be one of: {', '.join(VALID_EVENT_TYPES)}")
        return v_upper


class InteractionEventResponse(BaseModel):
    id: str
    StudentID: str
    StudentName: str
    CourseID: Optional[str] = None
    CourseSubject: str
    CourseName: str
    EventType: str
    EventTimestamp: str
    EventDuration: Optional[float] = None
    PlaybackSpeed: Optional[float] = None
    PauseReason: Optional[str] = None


class LearningSessionStartRequest(BaseModel):
    course_id: str


class LearningSessionStartResponse(BaseModel):
    session_id: str
    StudentID: str
    StudentName: str
    CourseID: Optional[str] = None
    CourseSubject: str
    CourseName: str
    LearningStartTime: datetime


class LearningSessionEndRequest(BaseModel):
    session_id: str
