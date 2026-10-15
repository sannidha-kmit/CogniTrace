from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    determine_role_from_identifier
)
from app.db.mongodb import get_database
from app.schemas.auth import (
    StudentRegisterRequest,
    TeacherRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse
)
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/register/student", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_student(req: StudentRegisterRequest):
    """
    Register a new student account.
    Prevents duplicate Roll Numbers and hashes password securely.
    """
    database = await get_database()
    roll_number = req.roll_number.upper()

    # Check existing user
    existing_user = await database.users.find_one({"identifier": roll_number})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this identifier already exists."
        )

    password_hash = get_password_hash(req.password)
    now = datetime.now(timezone.utc)

    try:
        # Create core user document
        user_doc = {
            "identifier": roll_number,
            "role": "student",
            "password_hash": password_hash,
            "created_at": now
        }
        user_result = await database.users.insert_one(user_doc)
        user_id = str(user_result.inserted_id)

        # Create student profile document
        student_doc = {
            "user_id": user_id,
            "roll_number": roll_number,
            "name": req.name,
            "year": req.year,
            "created_at": now
        }
        await database.students.insert_one(student_doc)

        # Issue JWT
        access_token = create_access_token({
            "sub": user_id,
            "identifier": roll_number,
            "role": "student"
        })

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user_id,
                identifier=roll_number,
                role="student",
                name=req.name,
                year=req.year
            )
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this identifier already exists."
        )


@router.post("/register/teacher", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_teacher(req: TeacherRegisterRequest):
    """
    Register a new teacher account.
    Prevents duplicate Teacher IDs and hashes password securely.
    """
    database = await get_database()
    teacher_id = req.teacher_id.upper()

    # Check existing user
    existing_user = await database.users.find_one({"identifier": teacher_id})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this identifier already exists."
        )

    password_hash = get_password_hash(req.password)
    now = datetime.now(timezone.utc)

    try:
        # Create core user document
        user_doc = {
            "identifier": teacher_id,
            "role": "teacher",
            "password_hash": password_hash,
            "created_at": now
        }
        user_result = await database.users.insert_one(user_doc)
        user_id = str(user_result.inserted_id)

        # Create teacher profile document
        teacher_doc = {
            "user_id": user_id,
            "teacher_id": teacher_id,
            "name": req.name,
            "year": req.year,
            "subject": req.subject,
            "created_at": now
        }
        await database.teachers.insert_one(teacher_doc)

        # Issue JWT
        access_token = create_access_token({
            "sub": user_id,
            "identifier": teacher_id,
            "role": "teacher"
        })

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user_id,
                identifier=teacher_id,
                role="teacher",
                name=req.name,
                year=req.year,
                subject=req.subject
            )
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this identifier already exists."
        )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """
    Unified login for both Students and Teachers.
    Determines role automatically from registered account identity.
    """
    identifier = req.identifier.upper()
    import logging
    logger = logging.getLogger("auth_debug")

    # Validate identifier format
    role_type = determine_role_from_identifier(identifier)

    if not role_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid identifier format. Roll Number must start with 'S' and Teacher ID must start with 'T'."
        )

    database = await get_database()
    user = await database.users.find_one({"identifier": identifier})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Roll Number / Teacher ID or password."
        )
    
    pw_verified = verify_password(req.password, user["password_hash"])
    
    if not pw_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Roll Number / Teacher ID or password."
        )


    user_id = str(user["_id"])
    user_role = user["role"]

    # Fetch corresponding profile
    profile = None
    if user_role == "student":
        profile = await database.students.find_one({"user_id": user_id})
    elif user_role == "teacher":
        profile = await database.teachers.find_one({"user_id": user_id})

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account profile data is missing."
        )

    access_token = create_access_token({
        "sub": user_id,
        "identifier": user["identifier"],
        "role": user_role
    })

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user_id,
            identifier=user["identifier"],
            role=user_role,
            name=profile.get("name", ""),
            year=profile.get("year", ""),
            subject=profile.get("subject") if user_role == "teacher" else None
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """
    Retrieve authenticated user profile details.
    """
    return UserResponse(
        id=current_user["id"],
        identifier=current_user["identifier"],
        role=current_user["role"],
        name=current_user["name"],
        year=current_user["year"],
        subject=current_user["subject"]
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout endpoint confirmation.
    Client clears local JWT token upon receiving this response.
    """
    return {"message": "Successfully logged out."}
