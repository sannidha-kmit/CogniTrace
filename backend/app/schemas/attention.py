from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AttentionStateEnum(str, Enum):
    FOCUSED = "FOCUSED"
    POSSIBLE_DISTRACTION = "POSSIBLE_DISTRACTION"
    SUSTAINED_DISTRACTION = "SUSTAINED_DISTRACTION"
    HIGH_DISTRACTION = "HIGH_DISTRACTION"
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    RECOVERED = "RECOVERED"
    MONITORING_PAUSED = "MONITORING_PAUSED"


class DistractionEventTypeEnum(str, Enum):
    LOOKING_AWAY = "LOOKING_AWAY"
    PHONE_INTERACTION = "PHONE_INTERACTION"
    POSSIBLE_TALKING = "POSSIBLE_TALKING"
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    HIGH_NOISE = "HIGH_NOISE"
    RECOVERED_ATTENTION = "RECOVERED_ATTENTION"
    DISTRACTION_NOTIFICATION_SHOWN = "DISTRACTION_NOTIFICATION_SHOWN"
    FOCUSED_HEARTBEAT = "FOCUSED_HEARTBEAT"


class NoiseLevelEnum(str, Enum):
    QUIET = "QUIET"
    MODERATE = "MODERATE"
    NOISY = "NOISY"
    DISABLED = "DISABLED"


class HeadPoseData(BaseModel):
    yaw: float = Field(0.0, description="Yaw angle in degrees (-90 to +90)")
    pitch: float = Field(0.0, description="Pitch angle in degrees (-90 to +90)")
    roll: float = Field(0.0, description="Roll angle in degrees (-90 to +90)")


class AttentionTelemetryCreate(BaseModel):
    course_id: str = Field(..., description="Target Course MongoDB ID")
    video_timestamp: str = Field(..., description="Playback timestamp position (e.g. 02:15 or 135.2)")
    attention_state: AttentionStateEnum = Field(..., description="Current state machine state")
    distraction_score: float = Field(..., ge=0.0, le=100.0, description="Calculated distraction score (0=attentive, 100=distracted)")
    distraction_duration: float = Field(0.0, ge=0.0, description="Continuous duration of current distraction state in seconds")
    event_type: DistractionEventTypeEnum = Field(..., description="Event type classification")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence metric of estimation (0.0 to 1.0)")
    head_pose: Optional[HeadPoseData] = Field(None, description="Estimated head orientation (yaw, pitch, roll)")
    noise_level: Optional[NoiseLevelEnum] = Field(NoiseLevelEnum.DISABLED, description="Estimated ambient noise level from Web Audio")
    environmental_distraction: bool = Field(False, description="Whether high ambient noise is contributing")
    behavioral_distraction: bool = Field(False, description="Whether student posture/gaze deviation is contributing")
    notification_triggered: bool = Field(False, description="Whether a gentle notification was displayed to the student")
    client_timestamp: Optional[datetime] = Field(None, description="Client-side ISO timestamp")


class AttentionTelemetryResponse(BaseModel):
    id: str
    StudentID: str
    StudentName: str
    CourseID: str
    CourseSubject: str
    CourseName: str
    video_timestamp: str
    attention_state: str
    distraction_score: float
    distraction_duration: float
    event_type: str
    confidence: float
    head_pose: Optional[Dict[str, float]] = None
    noise_level: Optional[str] = None
    environmental_distraction: bool = False
    behavioral_distraction: bool = False
    notification_triggered: bool = False
    created_at: datetime


class BatchAttentionTelemetryCreate(BaseModel):
    events: List[AttentionTelemetryCreate] = Field(..., max_length=100, description="Batch of attention telemetry events")


class AttentionSummaryResponse(BaseModel):
    student_id: str
    course_id: str
    course_name: str
    total_events: int
    focused_ratio: float
    distraction_event_count: int
    avg_distraction_score: float
    total_distraction_seconds: float
    dominant_distraction_type: Optional[str] = None
    high_noise_incidents: int


class AttentionThresholdSettings(BaseModel):
    yaw_threshold_degrees: float = Field(25.0, description="Yaw angle deviation threshold")
    pitch_threshold_degrees: float = Field(20.0, description="Pitch angle deviation threshold")
    brief_movement_grace_seconds: float = Field(3.0, description="Brief glance ignore duration")
    possible_distraction_seconds: float = Field(6.0, description="Possible distraction threshold")
    high_distraction_seconds: float = Field(10.0, description="High distraction notification threshold")
    notification_cooldown_seconds: float = Field(45.0, description="Minimum seconds between notifications")
    noise_rms_threshold: float = Field(0.08, description="Web Audio RMS threshold for noisy environment")
    sample_rate_fps: int = Field(8, ge=2, le=15, description="Client-side processing frames per second")
