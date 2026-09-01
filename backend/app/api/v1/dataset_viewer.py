from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Any, Dict
from bson import ObjectId
from datetime import datetime, timezone
import math

from app.api.deps import require_role
from app.db.mongodb import get_database

router = APIRouter()

# Dataset collection names mapping
COLLECTIONS = {
    "interactions": "interaction_events",
    "transcripts": "course_transcripts",
    "concepts": "concept_segments",
    "mappings": "concept_event_mappings",
    "difficulty": "difficulty"
}

async def get_teacher_courses(database, teacher_id: str, teacher_year: str, teacher_subject: str):
    cursor = database.courses.find({
        "teacher_id": teacher_id,
        "year": teacher_year,
        "subject": teacher_subject
    })
    courses = await cursor.to_list(length=1000)
    return courses

@router.get("/summary")
async def get_dataset_summary(
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Get total records across the 5 datasets scoped to the teacher's courses.
    """
    database = await get_database()
    teacher_id = current_teacher["identifier"]
    teacher_year = current_teacher["year"]
    teacher_subject = current_teacher["subject"]

    courses = await get_teacher_courses(database, teacher_id, teacher_year, teacher_subject)
    course_names = [c["course_name"] for c in courses]
    course_ids = [str(c["_id"]) for c in courses]
    
    if not course_names:
        return {
            "interactions": 0,
            "transcripts": 0,
            "concepts": 0,
            "mappings": 0,
            "difficulty": 0
        }

    # Interactions count
    interactions_count = await database.interaction_events.count_documents({
        "CourseSubject": teacher_subject,
        "CourseName": {"$in": course_names}
    })

    # Transcripts count (we count segments across completed transcripts)
    tx_cursor = database.course_transcripts.find({"course_id": {"$in": course_ids}, "status": "COMPLETED"})
    tx_docs = await tx_cursor.to_list(length=1000)
    transcripts_count = sum(len(doc.get("segments", [])) for doc in tx_docs)

    # Concepts count (segments across completed concept documents)
    concept_cursor = database.concept_segments.find({"course_id": {"$in": course_ids}, "status": "COMPLETED"})
    concept_docs = await concept_cursor.to_list(length=1000)
    concepts_count = sum(len(doc.get("segments", [])) for doc in concept_docs)

    # Mappings count
    mappings_count = await database.concept_event_mappings.count_documents({
        "CourseSubject": teacher_subject,
        "CourseName": {"$in": course_names}
    })

    # Difficulty count
    difficulty_count = await database.difficulty.count_documents({
        "CourseSubject": teacher_subject,
        "CourseName": {"$in": course_names}
    })

    return {
        "interactions": interactions_count,
        "transcripts": transcripts_count,
        "concepts": concepts_count,
        "mappings": mappings_count,
        "difficulty": difficulty_count
    }


@router.get("/{dataset_type}")
async def get_paginated_dataset(
    dataset_type: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    course_id: Optional[str] = None,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Get paginated datasets scoped to teacher.
    """
    if dataset_type not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Dataset type not found.")
        
    database = await get_database()
    teacher_id = current_teacher["identifier"]
    teacher_year = current_teacher["year"]
    teacher_subject = current_teacher["subject"]

    courses = await get_teacher_courses(database, teacher_id, teacher_year, teacher_subject)
    course_names = [c["course_name"] for c in courses]
    course_ids = [str(c["_id"]) for c in courses]

    if not course_names:
        return {"total": 0, "page": page, "limit": limit, "data": []}

    query = {}
    
    if dataset_type in ["transcripts", "concepts"]:
        query["course_id"] = {"$in": course_ids}
        if course_id and course_id != "ALL":
            if course_id in course_ids:
                query["course_id"] = course_id
            else:
                return {"total": 0, "page": page, "limit": limit, "data": []}
    else:
        query["CourseSubject"] = teacher_subject
        query["CourseName"] = {"$in": course_names}
        if course_id and course_id != "ALL":
            target = next((c for c in courses if str(c["_id"]) == course_id), None)
            if target:
                query["$or"] = [
                    {"CourseID": str(course_id)},
                    {"CourseName": target["course_name"]}
                ]
            else:
                return {"total": 0, "page": page, "limit": limit, "data": []}

    if search and search.strip():
        s = search.strip()
        if dataset_type == "interactions":
            query["$or"] = [
                {"StudentID": {"$regex": s, "$options": "i"}},
                {"EventType": {"$regex": s, "$options": "i"}}
            ]
        elif dataset_type == "transcripts":
            pass 
        elif dataset_type == "concepts":
            pass
        elif dataset_type == "mappings":
            query["$or"] = [
                {"StudentID": {"$regex": s, "$options": "i"}},
                {"Concept": {"$regex": s, "$options": "i"}},
                {"EventType": {"$regex": s, "$options": "i"}}
            ]
        elif dataset_type == "difficulty":
            query["$or"] = [
                {"StudentID": {"$regex": s, "$options": "i"}},
                {"Concept": {"$regex": s, "$options": "i"}}
            ]

    col = database[COLLECTIONS[dataset_type]]
    
    if dataset_type in ["transcripts", "concepts"]:
        # We need to flatten the arrays for pagination
        query["status"] = "COMPLETED"
        docs = await col.find(query).to_list(None)
        all_segments = []
        for d in docs:
            segs = d.get("segments", [])
            for idx, seg in enumerate(segs):
                seg_copy = dict(seg)
                seg_copy["_id"] = f"{d['_id']}_{idx}" # Pseudo ID
                seg_copy["parent_id"] = str(d["_id"])
                if dataset_type == "transcripts":
                    seg_copy["CourseName"] = d.get("course_name")
                else:
                    seg_copy["CourseName"] = d.get("CourseName")
                all_segments.append(seg_copy)
        
        # Apply search manually
        if search and search.strip():
            s = search.strip().lower()
            if dataset_type == "transcripts":
                all_segments = [seg for seg in all_segments if s in str(seg.get("text", "")).lower()]
            else:
                all_segments = [seg for seg in all_segments if s in str(seg.get("Concept", "")).lower()]
                
        total = len(all_segments)
        # Paginate
        start = (page - 1) * limit
        end = start + limit
        paginated_data = all_segments[start:end]
    else:
        total = await col.count_documents(query)
        cursor = col.find(query).sort("_id", -1).skip((page - 1) * limit).limit(limit)
        docs = await cursor.to_list(length=limit)
        paginated_data = []
        for d in docs:
            d["_id"] = str(d["_id"])
            paginated_data.append(d)

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total > 0 else 1,
        "data": paginated_data
    }


@router.get("/{dataset_type}/export")
async def export_paginated_dataset(
    dataset_type: str,
    format: str = Query("csv", description="Export format: csv, json, xlsx"),
    search: Optional[str] = None,
    course_id: Optional[str] = None,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Export the dataset across all the teacher's courses, reusing Phase 9 ExportService.
    """
    from app.services.export_service import ExportService
    
    # We fetch page 1 with a very high limit to get all data
    # (In a real massive dataset, we'd stream, but for CogniTrace 10,000 is enough for a file)
    dataset_res = await get_paginated_dataset(
        dataset_type=dataset_type,
        page=1,
        limit=50000,
        search=search,
        course_id=course_id,
        current_teacher=current_teacher
    )
    
    data = dataset_res["data"]
    
    # Remove internal _id for export
    for d in data:
        if "_id" in d:
            del d["_id"]
        if "parent_id" in d:
            del d["parent_id"]
            
    # Determine fieldnames based on dataset type
    if dataset_type == "interactions":
        fieldnames = ["StudentID", "StudentName", "CourseSubject", "CourseName", "EventType", "EventTimestamp", "EventDuration", "PlaybackSpeed", "PauseReason"]
    elif dataset_type == "transcripts":
        fieldnames = ["CourseName", "TranscriptStart", "TranscriptEnd", "text", "start", "end"]
    elif dataset_type == "concepts":
        fieldnames = ["CourseName", "Concept", "ConceptStart", "ConceptEnd", "Prerequisite", "DifficultyLevel"]
    elif dataset_type == "mappings":
        fieldnames = ["StudentID", "StudentName", "CourseSubject", "CourseName", "EventType", "EventTimestamp", "Transcript", "Concept", "Prerequisite"]
    elif dataset_type == "difficulty":
        fieldnames = ["StudentID", "StudentName", "CourseSubject", "CourseName", "Concept", "ReplayCount", "PauseCount", "SeekBackwardCount", "SeekForwardCount", "UnderstandPauseCount", "DifficultyScore", "DifficultyLevel", "NeedsRevision"]
    else:
        fieldnames = []

    return ExportService.get_export_response(data, fieldnames, dataset_type, format.lower())


@router.delete("/{dataset_type}/record/{record_id}")
async def delete_dataset_record(
    dataset_type: str,
    record_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Safely delete an individual record.
    For transcripts/concepts, record_id is pseudo-ID `parent_id_index`.
    """
    if dataset_type not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Dataset type not found.")
        
    database = await get_database()
    teacher_id = current_teacher["identifier"]
    
    col = database[COLLECTIONS[dataset_type]]
    
    if dataset_type in ["transcripts", "concepts"]:
        try:
            parent_id, idx_str = record_id.split("_")
            idx = int(idx_str)
            
            # Since concepts might use teacher_id directly or we check course owner
            query = {"_id": ObjectId(parent_id)}
            doc = await col.find_one(query)
            if not doc:
                raise HTTPException(status_code=404, detail="Record not found.")
                
            course_id = doc.get("course_id")
            course = await database.courses.find_one({"_id": ObjectId(course_id), "teacher_id": teacher_id})
            if not course:
                raise HTTPException(status_code=403, detail="Unauthorized.")
            
            if dataset_type == "transcripts":
                # Check dependencies
                mapping_exists = await database.concept_event_mappings.find_one({"CourseName": doc["course_name"]})
                concept_exists = await database.concept_segments.find_one({"course_id": course_id, "status": "COMPLETED"})
                
                if mapping_exists or concept_exists:
                    raise HTTPException(status_code=400, detail="Transcript cannot be deleted because concept/mapping data depends on it.")
            
            segs = doc.get("segments", [])
            if 0 <= idx < len(segs):
                segs.pop(idx)
                await col.update_one({"_id": ObjectId(parent_id)}, {"$set": {"segments": segs}})
                return {"message": "Record deleted successfully."}
            else:
                raise HTTPException(status_code=404, detail="Segment index not found.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid record ID format.")
            
    else:
        if not ObjectId.is_valid(record_id):
            raise HTTPException(status_code=400, detail="Invalid record ID.")
            
        doc = await col.find_one({"_id": ObjectId(record_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Record not found.")
            
        # Verify ownership via courses
        course_name = doc.get("CourseName")
        course = await database.courses.find_one({"course_name": course_name, "teacher_id": teacher_id})
        if not course:
             raise HTTPException(status_code=403, detail="Unauthorized to delete this record.")
             
        await col.delete_one({"_id": ObjectId(record_id)})
        return {"message": "Record deleted successfully."}

@router.delete("/{dataset_type}/course/{course_id}")
async def delete_dataset_by_course(
    dataset_type: str,
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    if dataset_type not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Dataset type not found.")
        
    database = await get_database()
    teacher_id = current_teacher["identifier"]
    
    if not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid course ID.")
        
    course = await database.courses.find_one({"_id": ObjectId(course_id), "teacher_id": teacher_id})
    if not course:
        raise HTTPException(status_code=403, detail="Unauthorized or course not found.")
        
    course_name = course["course_name"]
    col = database[COLLECTIONS[dataset_type]]
    
    if dataset_type == "transcripts":
        # Check dependencies
        mapping_exists = await database.concept_event_mappings.find_one({"CourseName": course_name})
        concept_exists = await database.concept_segments.find_one({"course_id": course_id, "status": "COMPLETED"})
        if mapping_exists or concept_exists:
            raise HTTPException(status_code=400, detail="Transcript cannot be deleted because concept/mapping data depends on it.")
        
        await col.delete_one({"course_id": course_id})
        
    elif dataset_type == "concepts":
        await col.delete_one({"course_id": course_id})
        
    else:
        # Bulk delete by CourseName
        await col.delete_many({"CourseName": course_name})
        
    return {"message": "Dataset records for course deleted successfully."}

@router.delete("/{dataset_type}/student/{roll_number}/course/{course_id}")
async def delete_dataset_by_student_course(
    dataset_type: str,
    roll_number: str,
    course_id: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    if dataset_type in ["transcripts", "concepts"]:
        raise HTTPException(status_code=400, detail="Cannot delete student scope from global datasets.")
        
    if dataset_type not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Dataset type not found.")
        
    database = await get_database()
    teacher_id = current_teacher["identifier"]
    clean_roll = roll_number.strip().upper()
    
    if not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid course ID.")
        
    course = await database.courses.find_one({"_id": ObjectId(course_id), "teacher_id": teacher_id})
    if not course:
        raise HTTPException(status_code=403, detail="Unauthorized or course not found.")
        
    course_name = course["course_name"]
    col = database[COLLECTIONS[dataset_type]]
    
    await col.delete_many({"StudentID": clean_roll, "CourseName": course_name})
    
    return {"message": "Dataset records for student and course deleted successfully."}
