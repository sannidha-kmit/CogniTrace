import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# YouTube URL Validation Regex Pattern
YOUTUBE_URL_PATTERN = r"^(https?://)?(www\.|m\.|music\.)?(youtube\.com/(watch\?.*v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})"


def is_valid_youtube_url(url: str) -> bool:
    """Validate standard YouTube video watch, embed, or short URLs."""
    if not url:
        return False
    return bool(re.search(YOUTUBE_URL_PATTERN, url.strip()))


class CourseCreateRequest(BaseModel):
    course_name: str = Field(..., min_length=2, max_length=150, description="Name of the course / topic")
    youtube_url: str = Field(..., description="YouTube Video URL")

    @field_validator("course_name", "youtube_url", mode="before")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube(cls, v: str) -> str:
        if not is_valid_youtube_url(v):
            raise ValueError(
                "Invalid YouTube Video URL. Must be a valid single video watch link (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...)."
            )
        return v


class CourseResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    year: str
    subject: str
    course_name: str
    youtube_url: str
    created_at: datetime


class StudentListItemResponse(BaseModel):
    id: str
    roll_number: str
    name: str
    year: str
