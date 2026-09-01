from typing import Optional
from pydantic import BaseModel, Field


class DifficultyDatasetResponse(BaseModel):
    """
    CogniTrace Phase 8 Difficulty Dataset Response.
    Contains exactly 13 required fields.
    """
    id: str = Field(..., description="Unique mapping document MongoDB ID string")
    StudentID: str = Field(..., description="Student Roll Number/ID")
    StudentName: str = Field(..., description="Student registered name")
    CourseID: Optional[str] = Field(None, description="Target Course Object ID")
    CourseSubject: str = Field(..., description="Course subject code")
    CourseName: str = Field(..., description="Course title")
    Concept: str = Field(..., description="Phase 6 Concept Name")
    
    ReplayCount: int = Field(0, description="Count of REPLAY events (derived from real interaction events)")
    PauseCount: int = Field(0, description="Count of PAUSE events")
    SeekBackwardCount: int = Field(0, description="Count of SEEK_BACKWARD events (excluding simultaneous REPLAYs)")
    SeekForwardCount: int = Field(0, description="Count of SEEK_FORWARD events")
    UnderstandPauseCount: int = Field(0, description="Count of PAUSE events with understanding intent")
    
    DifficultyScore: float = Field(0.0, description="Deterministic Difficulty Score")
    DifficultyLevel: str = Field("Easy", description="Easy, Medium, or High")
    NeedsRevision: bool = Field(False, description="True if DifficultyLevel is High")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "6a7e08000000000000000001",
                "StudentID": "S24A001",
                "StudentName": "Sannidha",
                "CourseSubject": "DAA",
                "CourseName": "Definition",
                "Concept": "Def Fundamentals",
                "ReplayCount": 2,
                "PauseCount": 2,
                "SeekBackwardCount": 2,
                "SeekForwardCount": 1,
                "UnderstandPauseCount": 1,
                "DifficultyScore": 13.5,
                "DifficultyLevel": "High",
                "NeedsRevision": True
            }
        }
