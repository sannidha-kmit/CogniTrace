from typing import Optional
from pydantic import BaseModel, Field


class ConceptEventMappingResponse(BaseModel):
    """
    CogniTrace Phase 7 Concept-Event Mapping Dataset Response.
    Contains ONLY the 9 required fields for Phase 7 dataset collection.
    """
    id: str = Field(..., description="Unique mapping document MongoDB ID string")
    StudentID: str = Field(..., description="Student Roll Number/ID")
    StudentName: str = Field(..., description="Student registered name")
    CourseID: Optional[str] = Field(None, description="Target Course Object ID")
    CourseSubject: str = Field(..., description="Course subject code")
    CourseName: str = Field(..., description="Course title")
    EventType: str = Field(..., description="Interaction event type (e.g. PAUSE, PLAY, SEEK_FORWARD, SEEK_BACKWARD, SPEED_CHANGE, VIDEO_COMPLETE)")
    EventTimestamp: str = Field(..., description="Formatted timestamp string where event occurred (e.g. 00:43)")
    Transcript: str = Field(..., description="Exact transcript text segment corresponding to the event timestamp")
    Concept: str = Field(..., description="Exact Phase 6 concept corresponding to the event timestamp")
    Prerequisite: str = Field(..., description="Prerequisite associated with the mapped concept")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "6a7e08000000000000000000",
                "StudentID": "S24A001",
                "StudentName": "Sannidha",
                "CourseSubject": "DAA",
                "CourseName": "Definition",
                "EventType": "PAUSE",
                "EventTimestamp": "00:43",
                "Transcript": "Let us define what an algorithm is.",
                "Concept": "Def Fundamentals",
                "Prerequisite": "None"
            }
        }
