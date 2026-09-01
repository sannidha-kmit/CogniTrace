from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.student import (
    InteractionEventCreate,
    InteractionEventResponse,
    LearningSessionStartRequest,
    LearningSessionStartResponse,
    LearningSessionEndRequest
)

router = APIRouter()


@router.post("/events", response_model=InteractionEventResponse, status_code=status.HTTP_201_CREATED)
async def record_interaction_event(
    req: InteractionEventCreate,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Record a real student video interaction telemetry event.
    Research dataset fields (StudentID, StudentName, CourseSubject, CourseName)
    are strictly derived from the authenticated student and database course record.
    """
    if not ObjectId.is_valid(req.course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(req.course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target course not found."
        )

    # Enforce student academic year matching course year
    if course["year"] != current_student["year"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You cannot record telemetry for courses outside your academic year."
        )

    student_id = current_student["identifier"]
    student_name = current_student["name"]
    course_id_str = str(course["_id"])
    course_subject = course["subject"]
    course_name = course["course_name"]
    now = datetime.now(timezone.utc)

    # Strictly structured research dataset event document
    event_doc = {
        "StudentID": student_id,
        "StudentName": student_name,
        "CourseID": course_id_str,
        "CourseSubject": course_subject,
        "CourseName": course_name,
        "EventType": req.event_type,
        "EventTimestamp": req.event_timestamp,
        "EventDuration": req.event_duration if req.event_duration is not None else None,
        "PlaybackSpeed": req.playback_speed if req.playback_speed is not None else None,
        "PauseReason": req.pause_reason if req.pause_reason is not None else None,
        "created_at": now
    }

    result = await database.interaction_events.insert_one(event_doc)
    event_db_id = str(result.inserted_id)

    return InteractionEventResponse(
        id=event_db_id,
        StudentID=student_id,
        StudentName=student_name,
        CourseID=course_id_str,
        CourseSubject=course_subject,
        CourseName=course_name,
        EventType=req.event_type,
        EventTimestamp=req.event_timestamp,
        EventDuration=req.event_duration,
        PlaybackSpeed=req.playback_speed,
        PauseReason=req.pause_reason
    )


@router.post("/learning/start", response_model=LearningSessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_learning_session(
    req: LearningSessionStartRequest,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Record the start of a student's learning session for a course.
    """
    if not ObjectId.is_valid(req.course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(req.course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target course not found."
        )

    if course["year"] != current_student["year"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    student_id = current_student["identifier"]
    student_name = current_student["name"]
    course_id_str = str(course["_id"])
    course_subject = course["subject"]
    course_name = course["course_name"]
    start_time = datetime.now(timezone.utc)

    session_doc = {
        "StudentID": student_id,
        "StudentName": student_name,
        "CourseID": course_id_str,
        "CourseSubject": course_subject,
        "CourseName": course_name,
        "LearningStartTime": start_time,
        "LearningEndTime": None,
        "created_at": start_time
    }

    result = await database.student_learning.insert_one(session_doc)
    session_id = str(result.inserted_id)

    return LearningSessionStartResponse(
        session_id=session_id,
        StudentID=student_id,
        StudentName=student_name,
        CourseID=course_id_str,
        CourseSubject=course_subject,
        CourseName=course_name,
        LearningStartTime=start_time
    )


@router.post("/learning/end")
async def end_learning_session(
    req: LearningSessionEndRequest,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Record the completion/end time of a student's learning session.
    """
    if not ObjectId.is_valid(req.session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format."
        )

    database = await get_database()
    end_time = datetime.now(timezone.utc)

    result = await database.student_learning.update_one(
        {
            "_id": ObjectId(req.session_id),
            "StudentID": current_student["identifier"]
        },
        {"$set": {"LearningEndTime": end_time}}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning session not found or unauthorized."
        )

    return {"message": "Learning session concluded.", "LearningEndTime": end_time}
