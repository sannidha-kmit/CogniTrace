from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.concept import (
    ConceptResponse,
    ConceptStatusResponse,
    ConceptSegmentItem
)

router = APIRouter()


@router.post("/courses/{course_id}/concepts/extract", status_code=status.HTTP_202_ACCEPTED)
async def queue_concept_extraction(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Queue concept extraction for a course in concept_extraction_jobs queue.
    FastAPI returns immediately (<15ms) without running heavy NLP.
    The standalone concept worker process (app/workers/concept_worker.py) claims and processes the job.
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
            detail="Access denied. You can only extract concepts for your own courses."
        )

    # 1. Check if Transcript exists and is COMPLETED
    tx_doc = await database.course_transcripts.find_one({"course_id": course_id})
    if not tx_doc or tx_doc.get("status") != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript is required before concept extraction. Please generate transcript first."
        )

    # 2. Check if concept extraction is already COMPLETED
    existing_concepts = await database.concept_segments.find_one({"course_id": course_id})
    if existing_concepts and existing_concepts.get("status") == "COMPLETED":
        return {
            "message": "Concept extraction already completed.",
            "status": "COMPLETED",
            "course_id": course_id
        }

    # 3. Check if a job is already PENDING or PROCESSING
    existing_job = await database.concept_extraction_jobs.find_one({"course_id": course_id})
    if existing_job and existing_job.get("status") in ["PENDING", "PROCESSING"]:
        return {
            "message": f"Concept extraction is currently {existing_job.get('status')}.",
            "status": existing_job.get("status"),
            "course_id": course_id
        }

    now = datetime.now(timezone.utc)

    # 4. Upsert job into concept_extraction_jobs
    await database.concept_extraction_jobs.update_one(
        {"course_id": course_id},
        {
            "$set": {
                "course_id": course_id,
                "teacher_id": current_teacher["identifier"],
                "status": "PENDING",
                "attempts": 0,
                "error_message": None,
                "created_at": now,
                "updated_at": now
            }
        },
        upsert=True
    )

    # 5. Upsert status in concept_segments collection
    await database.concept_segments.update_one(
        {"course_id": course_id},
        {
            "$set": {
                "course_id": course_id,
                "CourseSubject": course["subject"],
                "CourseName": course["course_name"],
                "teacher_id": course["teacher_id"],
                "teacher_name": course["teacher_name"],
                "status": "PENDING",
                "segments": [],
                "error_message": None,
                "created_at": now,
                "updated_at": now
            }
        },
        upsert=True
    )

    from app.workers.concept_worker import trigger_concept_worker_wakeup
    trigger_concept_worker_wakeup()

    return {
        "message": "Concept extraction queued successfully.",
        "status": "PENDING",
        "course_id": course_id
    }


@router.get("/courses/{course_id}/concepts/status", response_model=ConceptStatusResponse)
async def get_concept_status(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Get concept extraction status for a course (<5ms response time).
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

    concept_doc = await database.concept_segments.find_one({"course_id": course_id})
    if not concept_doc:
        return ConceptStatusResponse(
            course_id=course_id,
            status="NOT_GENERATED",
            concept_count=0,
            error_message=None
        )

    segments = concept_doc.get("segments", [])
    return ConceptStatusResponse(
        course_id=course_id,
        status=concept_doc.get("status", "NOT_GENERATED"),
        concept_count=len(segments),
        error_message=concept_doc.get("error_message")
    )


@router.get("/courses/{course_id}/concepts", response_model=ConceptResponse)
async def get_course_concepts(
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve full derived concept dataset for a course. Enforces strict teacher ownership.
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
            detail="Access denied. You can only view concepts for your own courses."
        )

    concept_doc = await database.concept_segments.find_one({"course_id": course_id})
    if not concept_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concepts have not been extracted for this course yet."
        )

    raw_segments = concept_doc.get("segments", [])
    formatted_items = [
        ConceptSegmentItem(
            Concept=s["Concept"],
            ConceptStart=s["ConceptStart"],
            ConceptEnd=s["ConceptEnd"],
            Prerequisite=s.get("Prerequisite", "None"),
            DifficultyLevel=s.get("DifficultyLevel", "Easy")
        )
        for s in raw_segments
    ]

    return ConceptResponse(
        id=str(concept_doc["_id"]),
        course_id=course_id,
        course_name=concept_doc.get("CourseName", course["course_name"]),
        subject=concept_doc.get("CourseSubject", course["subject"]),
        teacher_id=concept_doc.get("teacher_id", course["teacher_id"]),
        teacher_name=concept_doc.get("teacher_name", course["teacher_name"]),
        status=concept_doc.get("status", "NOT_GENERATED"),
        segments=formatted_items,
        error_message=concept_doc.get("error_message"),
        created_at=concept_doc.get("created_at", datetime.now(timezone.utc)),
        updated_at=concept_doc.get("updated_at", datetime.now(timezone.utc))
    )


@router.get("/courses/{course_id}/concepts/export")
async def export_course_concepts(
    course_id: str,
    format: str = Query("csv", description="Export format: csv, json, xlsx"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Export Phase 6 Concept Dataset.
    """
    from app.services.export_service import ExportService
    
    concept_res = await get_course_concepts(course_id, current_teacher)
    
    # Export segments only
    data = [s.model_dump() for s in concept_res.segments]
        
    fieldnames = ["Concept", "ConceptStart", "ConceptEnd", "Prerequisite", "DifficultyLevel"]
    return ExportService.get_export_response(data, fieldnames, "concepts", format.lower())
