from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.attention import (
    AttentionTelemetryCreate,
    AttentionTelemetryResponse,
    BatchAttentionTelemetryCreate,
    AttentionSummaryResponse,
    AttentionThresholdSettings
)
from app.services.attention_service import AttentionService

router = APIRouter()


@router.get("/attention/config", response_model=AttentionThresholdSettings)
async def get_attention_config():
    """
    Retrieve recommended client-side distraction monitoring configuration and thresholds.
    These can be tuned dynamically without hardcoding in the browser client.
    """
    return AttentionService.get_default_settings()


@router.post("/student/attention/telemetry", response_model=AttentionTelemetryResponse, status_code=status.HTTP_201_CREATED)
async def record_attention_telemetry(
    req: AttentionTelemetryCreate,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Record a single real-time attention/distraction telemetry event for the authenticated student.
    Strict privacy preservation: ONLY derived numeric metrics are stored. Zero camera or audio recordings.
    """
    return await AttentionService.record_telemetry(req, current_student)


@router.post("/student/attention/batch", status_code=status.HTTP_201_CREATED)
async def record_batch_attention_telemetry(
    req: BatchAttentionTelemetryCreate,
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Record a batch of derived attention telemetry events to reduce network overhead.
    """
    return await AttentionService.record_batch_telemetry(req.events, current_student)


@router.get("/student/attention/summary", response_model=AttentionSummaryResponse)
async def get_student_attention_summary(
    course_id: str = Query(..., description="Target course ID"),
    current_student: dict = Depends(require_role(["student"]))
):
    """
    Get aggregated attention summary metrics for the authenticated student on a specific course.
    """
    student_id = current_student["identifier"]
    return await AttentionService.get_student_course_summary(course_id, student_id)


@router.get("/teacher/attention/course/{course_id}")
async def get_teacher_course_attention_analytics(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve aggregated, anonymized attention analytics for a course owned by the teacher.
    Allows teachers to understand where students commonly drift without compromising individual privacy.
    """
    if not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid course ID.")

    database = await get_database()
    teacher_id = current_teacher["identifier"]

    course = await database.courses.find_one({
        "_id": ObjectId(course_id),
        "teacher_id": teacher_id
    })
    if not course:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course not found or not authorized."
        )

    # Fetch all attention events for this course
    cursor = database.student_attention_events.find({"CourseID": course_id})
    events = await cursor.to_list(length=5000)

    total_events = len(events)
    if total_events == 0:
        return {
            "course_id": course_id,
            "course_name": course.get("course_name"),
            "total_events": 0,
            "average_focus_ratio": 1.0,
            "distraction_breakdown": {},
            "common_distraction_timestamps": []
        }

    focused_count = sum(1 for e in events if e.get("attention_state") in ["FOCUSED", "RECOVERED"])
    breakdown = {}
    timestamp_buckets = {}

    for e in events:
        et = e.get("event_type", "LOOKING_AWAY")
        breakdown[et] = breakdown.get(et, 0) + 1

        ts = e.get("video_timestamp", "00:00")
        if e.get("attention_state") in ["SUSTAINED_DISTRACTION", "HIGH_DISTRACTION"]:
            timestamp_buckets[ts] = timestamp_buckets.get(ts, 0) + 1

    # Find top 5 timestamps where distraction occurred
    sorted_ts = sorted(timestamp_buckets.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "course_id": course_id,
        "course_name": course.get("course_name"),
        "total_events": total_events,
        "average_focus_ratio": round(focused_count / total_events, 3),
        "distraction_breakdown": breakdown,
        "common_distraction_timestamps": [{"timestamp": ts, "count": cnt} for ts, cnt in sorted_ts]
    }
