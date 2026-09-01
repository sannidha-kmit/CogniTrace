from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.transcript import (
    TranscriptResponse,
    TranscriptStatusResponse,
    TranscriptSegment
)

router = APIRouter()


@router.post("/courses/{course_id}/transcript/generate", status_code=status.HTTP_202_ACCEPTED)
async def queue_transcript_generation(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Queue transcript generation for a course in the transcription_jobs collection.
    FastAPI returns immediately (<10ms) without executing Faster-Whisper.
    The standalone worker process (app/workers/transcript_worker.py) claims and processes the job.
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
            detail="Target course not found."
        )

    # Ownership check
    if course["teacher_id"] != current_teacher["identifier"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only generate transcripts for your own courses."
        )

    # 1. Check if transcript is already COMPLETED in course_transcripts or transcription_jobs
    existing_tx = await database.course_transcripts.find_one({"course_id": course_id})
    existing_job = await database.transcription_jobs.find_one({"course_id": course_id})

    if (existing_tx and existing_tx.get("status") == "COMPLETED") or (existing_job and existing_job.get("status") == "COMPLETED"):
        return {
            "message": "Transcript already generated.",
            "status": "COMPLETED",
            "progress": 100,
            "course_id": course_id
        }

    # 2. Check if a job is currently PENDING or PROCESSING
    if existing_job and existing_job.get("status") in ["PENDING", "PROCESSING"]:
        return {
            "message": f"Transcript generation is currently {existing_job.get('status')}.",
            "status": existing_job.get("status"),
            "progress": existing_job.get("progress", 0),
            "stage": existing_job.get("stage", "QUEUED"),
            "course_id": course_id
        }

    now = datetime.now(timezone.utc)

    # 3. Create/Upsert job in transcription_jobs queue
    await database.transcription_jobs.update_one(
        {"course_id": course_id},
        {
            "$set": {
                "course_id": course_id,
                "teacher_id": current_teacher["identifier"],
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

    # 4. Upsert course_transcripts status to PENDING
    await database.course_transcripts.update_one(
        {"course_id": course_id},
        {
            "$set": {
                "course_id": course_id,
                "course_name": course["course_name"],
                "subject": course["subject"],
                "teacher_id": course["teacher_id"],
                "teacher_name": course["teacher_name"],
                "youtube_url": course["youtube_url"],
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

    # Wake up in-process worker to process job immediately
    from app.workers.transcript_worker import trigger_worker_wakeup
    trigger_worker_wakeup()

    return {
        "message": "Transcript generation queued successfully.",
        "status": "PENDING",
        "progress": 0,
        "stage": "QUEUED",
        "course_id": course_id
    }


@router.get("/courses/{course_id}/transcript/status", response_model=TranscriptStatusResponse)
async def get_transcript_status(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Get transcript processing status and real percentage progress for a course (<5ms).
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
            detail="Access denied."
        )

    # Check job queue first for active progress
    job_doc = await database.transcription_jobs.find_one({"course_id": course_id})
    tx_doc = await database.course_transcripts.find_one({"course_id": course_id})

    if not tx_doc and not job_doc:
        return TranscriptStatusResponse(
            course_id=course_id,
            status="NOT_GENERATED",
            progress=0,
            stage="NOT_STARTED",
            completed=False,
            segment_count=0
        )

    if tx_doc and tx_doc.get("status") == "COMPLETED":
        status_val = "COMPLETED"
        progress_val = 100
        stage_val = "COMPLETED"
        message_val = "Transcription complete."
    elif job_doc:
        status_val = job_doc.get("status", "NOT_GENERATED")
        progress_val = job_doc.get("progress", 0)
        stage_val = job_doc.get("stage", "NOT_STARTED")
        message_val = job_doc.get("message")
    elif tx_doc:
        status_val = tx_doc.get("status", "NOT_GENERATED")
        progress_val = tx_doc.get("progress", 0)
        stage_val = tx_doc.get("stage", "NOT_STARTED")
        message_val = tx_doc.get("message")
    else:
        status_val = "NOT_GENERATED"
        progress_val = 0
        stage_val = "NOT_STARTED"
        message_val = None
    proc_sec = job_doc.get("processed_seconds", 0.0) if job_doc else tx_doc.get("processed_seconds", 0.0)
    tot_sec = job_doc.get("total_duration_seconds", 0.0) if job_doc else tx_doc.get("total_duration_seconds", 0.0)
    segments = tx_doc.get("segments", []) if tx_doc else []

    if status_val == "COMPLETED":
        progress_val = 100
        stage_val = "COMPLETED"

    return TranscriptStatusResponse(
        course_id=course_id,
        status=status_val,
        progress=progress_val,
        stage=stage_val,
        message=message_val,
        processed_seconds=proc_sec,
        total_duration_seconds=tot_sec,
        completed=(status_val == "COMPLETED"),
        language=tx_doc.get("language") if tx_doc else None,
        segment_count=len(segments),
        error_message=job_doc.get("error_message") if job_doc else (tx_doc.get("error_message") if tx_doc else None)
    )


@router.get("/courses/{course_id}/transcript", response_model=TranscriptResponse)
async def get_course_transcript(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve transcript document for a course.
    Returns status="NOT_GENERATED" with 200 OK if transcript has not been requested yet.
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
            detail="Access denied. You can only view transcripts for your own courses."
        )

    tx_doc = await database.course_transcripts.find_one({"course_id": course_id})
    job_doc = await database.transcription_jobs.find_one({"course_id": course_id})

    now = datetime.now(timezone.utc)
    if not tx_doc:
        return TranscriptResponse(
            id=str(ObjectId()),
            course_id=course_id,
            course_name=course["course_name"],
            subject=course["subject"],
            teacher_id=course["teacher_id"],
            teacher_name=course["teacher_name"],
            youtube_url=course["youtube_url"],
            status=job_doc.get("status", "NOT_GENERATED") if job_doc else "NOT_GENERATED",
            progress=job_doc.get("progress", 0) if job_doc else 0,
            stage=job_doc.get("stage", "NOT_STARTED") if job_doc else "NOT_STARTED",
            message=job_doc.get("message") if job_doc else None,
            processed_seconds=0.0,
            total_duration_seconds=0.0,
            language="en",
            segments=[],
            error_message=job_doc.get("error_message") if job_doc else None,
            created_at=now,
            updated_at=now
        )

    raw_segments = tx_doc.get("segments", [])
    formatted_segments = [
        TranscriptSegment(
            start=s["start"],
            end=s["end"],
            text=s["text"],
            TranscriptStart=s.get("TranscriptStart", f"{int(s['start'])}s"),
            TranscriptEnd=s.get("TranscriptEnd", f"{int(s['end'])}s")
        )
        for s in raw_segments
    ]

    status_val = tx_doc.get("status", "NOT_GENERATED")
    progress_val = tx_doc.get("progress", 100 if status_val == "COMPLETED" else 0)
    if status_val == "COMPLETED":
        progress_val = 100

    return TranscriptResponse(
        id=str(tx_doc["_id"]),
        course_id=course_id,
        course_name=tx_doc.get("course_name", course["course_name"]),
        subject=tx_doc.get("subject", course["subject"]),
        teacher_id=tx_doc.get("teacher_id", course["teacher_id"]),
        teacher_name=tx_doc.get("teacher_name", course["teacher_name"]),
        youtube_url=tx_doc.get("youtube_url", course["youtube_url"]),
        status=status_val,
        progress=progress_val,
        stage=tx_doc.get("stage", "COMPLETED" if status_val == "COMPLETED" else "NOT_STARTED"),
        message=tx_doc.get("message"),
        processed_seconds=tx_doc.get("processed_seconds", 0.0),
        total_duration_seconds=tx_doc.get("total_duration_seconds", 0.0),
        language=tx_doc.get("language", "en"),
        segments=formatted_segments,
        error_message=tx_doc.get("error_message"),
        created_at=tx_doc.get("created_at", now),
        updated_at=tx_doc.get("updated_at", now)
    )


@router.post("/courses/{course_id}/transcript/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def queue_transcript_regeneration(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Queue transcript regeneration for a course (retrying failed jobs or updating).
    FastAPI returns immediately (<10ms).
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
            detail="Access denied."
        )

    now = datetime.now(timezone.utc)

    # Reset job queue item
    await database.transcription_jobs.update_one(
        {"course_id": course_id},
        {
            "$set": {
                "course_id": course_id,
                "teacher_id": current_teacher["identifier"],
                "status": "PENDING",
                "progress": 0,
                "stage": "QUEUED",
                "message": "Re-queued for background processing...",
                "attempts": 0,
                "error_message": None,
                "updated_at": now
            }
        },
        upsert=True
    )

    # Reset course_transcripts record status to PENDING
    await database.course_transcripts.update_one(
        {"course_id": course_id},
        {
            "$set": {
                "status": "PENDING",
                "progress": 0,
                "stage": "QUEUED",
                "message": "Re-queued for background processing...",
                "error_message": None,
                "updated_at": now
            }
        },
        upsert=True
    )

    from app.workers.transcript_worker import trigger_worker_wakeup
    trigger_worker_wakeup()

    return {
        "message": "Transcript regeneration queued successfully.",
        "status": "PENDING",
        "progress": 0,
        "stage": "QUEUED",
        "course_id": course_id
    }


@router.get("/courses/{course_id}/transcript/export")
async def export_course_transcript(
    course_id: str,
    format: str = Query("csv", description="Export format: csv, json, xlsx"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Export Phase 4 Course Transcript.
    """
    from app.services.export_service import ExportService
    
    transcript_res = await get_course_transcript(course_id, current_teacher)
    
    # We want to export only the segments
    data = []
    for s in transcript_res.segments:
        data.append({
            "TranscriptStart": s.TranscriptStart,
            "TranscriptEnd": s.TranscriptEnd,
            "Transcript": s.text
        })
        
    fieldnames = ["TranscriptStart", "TranscriptEnd", "Transcript"]
    return ExportService.get_export_response(data, fieldnames, "course_transcripts", format.lower())
