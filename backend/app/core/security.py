import re
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import bcrypt
from fastapi import HTTPException, status
from app.core.config import settings

# Centralized Academic Configuration
VALID_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

# Identifier Patterns
STUDENT_IDENTIFIER_PATTERN = r"^S[A-Za-z0-9]+$"
TEACHER_IDENTIFIER_PATTERN = r"^T[A-Za-z0-9]+$"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate a bcrypt password hash."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def validate_student_identifier(identifier: str) -> bool:
    """Validate Student Roll Number format (Starts with S followed by alphanumeric characters)."""
    if not identifier:
        return False
    return bool(re.match(STUDENT_IDENTIFIER_PATTERN, identifier.strip()))


def validate_teacher_identifier(identifier: str) -> bool:
    """Validate Teacher ID format (Starts with T followed by alphanumeric characters)."""
    if not identifier:
        return False
    return bool(re.match(TEACHER_IDENTIFIER_PATTERN, identifier.strip()))


def determine_role_from_identifier(identifier: str) -> Optional[str]:
    """Determine user role strictly from validated identifier format."""
    clean_id = identifier.strip() if identifier else ""
    if validate_student_identifier(clean_id):
        return "student"
    elif validate_teacher_identifier(clean_id):
        return "teacher"
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token containing identity and role claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
