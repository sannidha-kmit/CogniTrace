import re
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.student import TeacherSubjectResponse, StudentCourseResponse
from app.schemas.quiz import AdaptiveQuizResponse, BulkSubmitRequest, BulkSubmitResponse
from app.services.adaptive_quiz_service import AdaptiveQuizService

router = APIRouter()


@router.get("/courses", response_model=List[StudentCourseResponse])
async def get_all_courses_for_student(
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Retrieve ALL courses available to the authenticated student based on their academic year.
    Sorted newest first.
    """
    database = await get_database()
    student_year = current_student["year"]

    cursor = database.courses.find({"year": student_year}).sort("created_at", -1)
    courses = await cursor.to_list(length=500)

    return [
        StudentCourseResponse(
            id=str(c["_id"]),
            course_name=c["course_name"],
            youtube_url=c["youtube_url"],
            subject=c["subject"],
            teacher_id=c["teacher_id"],
            teacher_name=c["teacher_name"],
            year=c["year"],
            created_at=c["created_at"]
        )
        for c in courses
    ]


@router.get("/teachers", response_model=List[TeacherSubjectResponse])
async def get_teachers_for_student_year(
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Retrieve teachers and subjects belonging ONLY to the authenticated student's academic year.
    Enforced strictly at the backend level using student's year from JWT.
    """
    database = await get_database()
    student_year = current_student["year"]

    cursor = database.teachers.find({"year": student_year}).sort("name", 1)
    teachers = await cursor.to_list(length=500)

    return [
        TeacherSubjectResponse(
            teacher_id=t["teacher_id"],
            teacher_name=t["name"],
            subject=t["subject"],
            year=t["year"]
        )
        for t in teachers
    ]


@router.get("/teachers/{teacher_id}/courses", response_model=List[StudentCourseResponse])
async def get_teacher_courses_for_student(
    teacher_id: str,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Retrieve courses created by a specific teacher for the student's academic year.
    Enforces that student's year matches teacher's year.
    Sorted NEWEST -> OLDEST (created_at DESC).
    """
    database = await get_database()
    student_year = current_student["year"]
    clean_teacher_id = teacher_id.upper().strip()

    teacher = await database.teachers.find_one({"teacher_id": clean_teacher_id})
    if not teacher or teacher["year"] != student_year:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You cannot view courses for teachers outside your academic year."
        )

    cursor = database.courses.find({
        "teacher_id": clean_teacher_id,
        "year": student_year
    }).sort("created_at", -1)

    courses = await cursor.to_list(length=500)

    return [
        StudentCourseResponse(
            id=str(c["_id"]),
            course_name=c["course_name"],
            youtube_url=c["youtube_url"],
            subject=c["subject"],
            teacher_id=c["teacher_id"],
            teacher_name=c["teacher_name"],
            year=c["year"],
            created_at=c["created_at"]
        )
        for c in courses
    ]


@router.get("/courses/search", response_model=List[StudentCourseResponse])
async def search_courses(
    query: Optional[str] = Query(None, description="Course name search query"),
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Search courses by course name.
    Case-insensitive, scoped strictly to student's academic year.
    Results sorted deterministically (Exact -> Prefix -> Substring, Newest First).
    """
    if not query or not query.strip():
        return []

    clean_query = query.strip()
    student_year = current_student["year"]
    database = await get_database()

    # Regex search restricted to student's year
    pattern = re.compile(re.escape(clean_query), re.IGNORECASE)
    cursor = database.courses.find({
        "year": student_year,
        "course_name": {"$regex": pattern}
    }).sort("created_at", -1)

    raw_courses = await cursor.to_list(length=200)

    # Sort deterministically
    def get_sort_score(course):
        name_lower = course["course_name"].lower()
        q_lower = clean_query.lower()
        if name_lower == q_lower:
            return 1
        elif name_lower.startswith(q_lower):
            return 2
        return 3

    sorted_courses = sorted(raw_courses, key=lambda c: (get_sort_score(c), -c["created_at"].timestamp()))

    return [
        StudentCourseResponse(
            id=str(c["_id"]),
            course_name=c["course_name"],
            youtube_url=c["youtube_url"],
            subject=c["subject"],
            teacher_id=c["teacher_id"],
            teacher_name=c["teacher_name"],
            year=c["year"],
            created_at=c["created_at"]
        )
        for c in sorted_courses
    ]


@router.get("/courses/{course_id}", response_model=StudentCourseResponse)
async def get_course_details_for_student(
    course_id: str,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Retrieve single course details for student.
    Enforces authorization check ensuring course's year matches student's year.
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

    if course["year"] != current_student["year"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not authorized to access courses outside your academic year."
        )

    return StudentCourseResponse(
        id=str(course["_id"]),
        course_name=course["course_name"],
        youtube_url=course["youtube_url"],
        subject=course["subject"],
        teacher_id=course["teacher_id"],
        teacher_name=course["teacher_name"],
        year=course["year"],
        created_at=course["created_at"]
    )


@router.get("/courses/{course_id}/adaptive-quiz", response_model=AdaptiveQuizResponse)
async def get_adaptive_quiz(
    course_id: str,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Generate a full adaptive quiz based on the student's telemetry predictions.
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

    if course["year"] != current_student["year"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not authorized to access courses outside your academic year."
        )

    student_id = current_student["identifier"]
    try:
        return await AdaptiveQuizService.generate_full_adaptive_quiz(
            student_id=student_id,
            course_id=course_id,
            course_name=course["course_name"]
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate adaptive quiz: {str(err)}"
        )


@router.post("/courses/{course_id}/adaptive-quiz/submit", response_model=BulkSubmitResponse)
async def submit_adaptive_quiz(
    course_id: str,
    submission: BulkSubmitRequest,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Submit and evaluate a full adaptive quiz session.
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

    if course["year"] != current_student["year"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not authorized to access courses outside your academic year."
        )

    student_id = current_student["identifier"]
    try:
        return await AdaptiveQuizService.submit_full_adaptive_quiz(
            student_id=student_id,
            course_id=course_id,
            submission=submission
        )
    except ValueError as err:
        msg = str(err)
        if "not found" in msg.lower() or "access denied" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer submission failed: {str(err)}"
        )
