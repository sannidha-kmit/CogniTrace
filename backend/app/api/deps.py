from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from app.db.mongodb import get_database

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to authenticate request via JWT Bearer Token.
    Returns authenticated user payload along with database profile.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    identifier = payload.get("identifier")
    role = payload.get("role")

    if not user_id or not identifier or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    database = await get_database()
    user = await database.users.find_one({"identifier": identifier})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch role profile
    profile = None
    if role == "student":
        profile = await database.students.find_one({"user_id": str(user["_id"])})
    elif role == "teacher":
        profile = await database.teachers.find_one({"user_id": str(user["_id"])})

    return {
        "id": str(user["_id"]),
        "identifier": user["identifier"],
        "role": user["role"],
        "name": profile.get("name") if profile else "",
        "year": profile.get("year") if profile else "",
        "subject": profile.get("subject") if profile and role == "teacher" else None,
    }


def require_role(allowed_roles: List[str]):
    """
    Dependency generator enforcing role-based authorization.
    Raises 403 Forbidden if current user's role is not in allowed_roles.
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}. Your role: {current_user['role']}."
            )
        return current_user
    return role_checker
