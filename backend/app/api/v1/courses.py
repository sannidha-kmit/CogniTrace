from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.api.deps import require_role, get_current_user
from app.db.mongodb import get_database
from app.schemas.course import CourseCreateRequest, CourseResponse

router = APIRouter()


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    req: CourseCreateRequest,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Create a new course with a single YouTube video URL.
    Ownership fields (teacher_id, teacher_name, year, subject) are strictly derived
    from the authenticated teacher's identity.
    """
    database = await get_database()
    teacher_id = current_teacher["identifier"]
    teacher_name = current_teacher["name"]
    year = current_teacher["year"]
    subject = current_teacher["subject"] or ""

    course_name = req.course_name.strip()
    youtube_url = req.youtube_url.strip()

    # Check for existing duplicate course by the same teacher
    existing = await database.courses.find_one({
        "teacher_id": teacher_id,
        "course_name": course_name,
        "youtube_url": youtube_url
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This course already exists."
        )

    now = datetime.now(timezone.utc)
    course_doc = {
        "teacher_id": teacher_id,
        "teacher_name": teacher_name,
        "year": year,
        "subject": subject,
        "course_name": course_name,
        "youtube_url": youtube_url,
        "created_at": now
    }

    try:
        result = await database.courses.insert_one(course_doc)
        course_id = str(result.inserted_id)

        # Automatically queue transcript generation
        await database.transcription_jobs.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "course_id": course_id,
                    "teacher_id": teacher_id,
                    "status": "PENDING",
                    "progress": 0,
                    "stage": "QUEUED",
                    "message": "Queued for background processing...",
                    "attempts": 0,
                    "error_message": None,
                    "created_at": now,
                    "updated_at": now
                }
            },
            upsert=True
        )

        await database.course_transcripts.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "course_id": course_id,
                    "course_name": course_name,
                    "subject": subject,
                    "teacher_id": teacher_id,
                    "teacher_name": teacher_name,
                    "youtube_url": youtube_url,
                    "status": "PENDING",
                    "progress": 0,
                    "stage": "QUEUED",
                    "message": "Queued for background processing...",
                    "language": "en",
                    "segments": [],
                    "error_message": None,
                    "created_at": now,
                    "updated_at": now
                }
            },
            upsert=True
        )

        from app.workers.transcript_worker import trigger_worker_wakeup
        trigger_worker_wakeup()

        return CourseResponse(
            id=course_id,
            teacher_id=teacher_id,
            teacher_name=teacher_name,
            year=year,
            subject=subject,
            course_name=course_name,
            youtube_url=youtube_url,
            created_at=now
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This course already exists."
        )


@router.get("/my", response_model=List[CourseResponse])
async def get_my_courses(
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve courses belonging ONLY to the authenticated teacher,
    sorted by creation date in DESCENDING order (newest first).
    """
    database = await get_database()
    teacher_id = current_teacher["identifier"]

    cursor = database.courses.find({"teacher_id": teacher_id}).sort("created_at", -1)
    courses = await cursor.to_list(length=500)

    return [
        CourseResponse(
            id=str(c["_id"]),
            teacher_id=c["teacher_id"],
            teacher_name=c["teacher_name"],
            year=c["year"],
            subject=c["subject"],
            course_name=c["course_name"],
            youtube_url=c["youtube_url"],
            created_at=c["created_at"]
        )
        for c in courses
    ]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course_by_id(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve single course details by ID for authenticated Teachers or Students.
    """
    if not ObjectId.is_valid(course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )

    if current_user["role"] == "teacher" and course["teacher_id"] != current_user["identifier"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this course."
        )

    if current_user["role"] == "student" and course["year"] != current_user["year"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Course is outside your academic year."
        )

    return CourseResponse(
        id=str(course["_id"]),
        teacher_id=course["teacher_id"],
        teacher_name=course["teacher_name"],
        year=course["year"],
        subject=course["subject"],
        course_name=course["course_name"],
        youtube_url=course["youtube_url"],
        created_at=course["created_at"]
    )


@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Delete a course safely.
    Verifies that the course belongs strictly to the requesting teacher.
    """
    if not ObjectId.is_valid(course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )

    if course["teacher_id"] != current_teacher["identifier"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this course."
        )

    await database.courses.delete_one({"_id": ObjectId(course_id)})
    return {"message": "Course deleted successfully."}
