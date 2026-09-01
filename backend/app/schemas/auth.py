from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.core.security import (
    VALID_YEARS, 
    validate_student_identifier, 
    validate_teacher_identifier
)


class StudentRegisterRequest(BaseModel):
    roll_number: str = Field(..., description="Student Roll Number (e.g. S24A001)")
    name: str = Field(..., min_length=2, description="Student Full Name")
    year: str = Field(..., description="Academic Year selection")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    confirm_password: str = Field(..., description="Confirm Password")

    @field_validator("roll_number", "name", mode="before")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("roll_number")
    @classmethod
    def validate_roll_number_format(cls, v: str) -> str:
        if not validate_student_identifier(v):
            raise ValueError("Student Roll Number must start with 'S' followed by alphanumeric characters (e.g., S24A001).")
        return v.upper()

    @field_validator("year")
    @classmethod
    def validate_academic_year(cls, v: str) -> str:
        if v not in VALID_YEARS:
            raise ValueError(f"Invalid academic year selected. Must be one of: {', '.join(VALID_YEARS)}")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match.")
        return v


class TeacherRegisterRequest(BaseModel):
    teacher_id: str = Field(..., description="Teacher ID (e.g. T24A001)")
    name: str = Field(..., min_length=2, description="Teacher Full Name")
    year: str = Field(..., description="Target Academic Year selection")
    subject: str = Field(..., min_length=2, description="Subject Name")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    confirm_password: str = Field(..., description="Confirm Password")

    @field_validator("teacher_id", "name", "year", "subject", mode="before")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("teacher_id")
    @classmethod
    def validate_teacher_id_format(cls, v: str) -> str:
        if not validate_teacher_identifier(v):
            raise ValueError("Teacher ID must start with 'T' followed by alphanumeric characters (e.g., T24A001).")
        return v.upper()

    @field_validator("year")
    @classmethod
    def validate_academic_year(cls, v: str) -> str:
        if v not in VALID_YEARS:
            raise ValueError(f"Invalid academic year selected. Must be one of: {', '.join(VALID_YEARS)}")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match.")
        return v


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Roll Number or Teacher ID")
    password: str = Field(..., description="Password")

    @field_validator("identifier", mode="before")
    @classmethod
    def trim_identifier(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().upper()
        return v


class UserResponse(BaseModel):
    id: str
    identifier: str
    role: str
    name: str
    year: str
    subject: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
