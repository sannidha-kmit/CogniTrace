from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from typing import List, Optional
from bson import ObjectId

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.student import InteractionEventResponse
from app.schemas.mapping import ConceptEventMappingResponse
from app.schemas.difficulty import DifficultyDatasetResponse
from app.services.mapping_service import MappingService
from app.services.difficulty_service import DifficultyService
from app.services.export_service import ExportService

router = APIRouter()


@router.get("/students")
async def get_students_for_teacher(
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve students belonging strictly to the authenticated teacher's academic year.
    Sorted alphanumerically by Roll Number (StudentID).
    """
    database = await get_database()
    teacher_year = current_teacher["year"]

    cursor = database.students.find({"year": teacher_year}).sort("roll_number", 1)
    students = await cursor.to_list(length=500)

    # Alphanumeric natural sort on roll_number
    sorted_students = sorted(students, key=lambda s: s.get("roll_number", ""))

    return [
        {
            "roll_number": s["roll_number"],
            "name": s["name"],
            "year": s["year"]
        }
        for s in sorted_students
    ]


@router.get("/students/{roll_number}/courses")
async def get_courses_for_student_dataset(
    roll_number: str,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve courses created by the authenticated teacher for which the selected student has interaction telemetry.
    Enforces strict year authorization and teacher subject/course ownership.
    """
    database = await get_database()
    clean_roll = roll_number.strip().upper()
    teacher_id = current_teacher["identifier"]
    teacher_year = current_teacher["year"]

    # Verify student exists and belongs to teacher's academic year
    student = await database.students.find_one({"roll_number": clean_roll})
    if not student or student["year"] != teacher_year:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student does not belong to your authorized academic year."
        )

    # Get teacher's courses
    cursor = database.courses.find({
        "teacher_id": teacher_id,
        "year": teacher_year
    }).sort("created_at", -1)
    teacher_courses = await cursor.to_list(length=200)

    teacher_course_names = [c["course_name"] for c in teacher_courses]
    if not teacher_course_names:
        return []

    # Find distinct course names student has interaction events for
    watched_names = await database.interaction_events.distinct(
        "CourseName",
        {
            "StudentID": clean_roll,
            "CourseSubject": current_teacher["subject"],
            "CourseName": {"$in": teacher_course_names}
        }
    )

    result_courses = [
        {
            "id": str(c["_id"]),
            "course_name": c["course_name"],
            "subject": c["subject"],
            "has_events": c["course_name"] in watched_names
        }
        for c in teacher_courses
    ]

    return result_courses


@router.get("/students/{roll_number}/interactions", response_model=List[InteractionEventResponse])
async def get_student_interaction_dataset(
    roll_number: str,
    course_id: Optional[str] = Query(None, description="Filter by Course ID"),
    event_type: Optional[str] = Query(None, description="Filter by Event Type (e.g. PAUSE, REPLAY)"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve interaction telemetry dataset for a student.
    STRICT BACKEND TEACHER SUBJECT ISOLATION ENFORCED:
    Teacher A sees ONLY interaction events for courses created by Teacher A in Teacher A's subject.
    Teacher B CANNOT see Teacher A's student interaction events.
    """
    database = await get_database()
    clean_roll = roll_number.strip().upper()
    teacher_id = current_teacher["identifier"]
    teacher_year = current_teacher["year"]
    teacher_subject = current_teacher["subject"]

    # 1. Verify student exists and belongs to teacher's academic year
    student = await database.students.find_one({"roll_number": clean_roll})
    if not student or student["year"] != teacher_year:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student does not belong to your authorized academic year."
        )

    # 2. Get teacher's courses to enforce strict ownership filter
    cursor = database.courses.find({
        "teacher_id": teacher_id,
        "year": teacher_year,
        "subject": teacher_subject
    })
    teacher_courses = await cursor.to_list(length=200)
    teacher_course_names = [c["course_name"] for c in teacher_courses]

    if not teacher_course_names:
        return []

    # 3. Construct interaction_events query strictly filtered to teacher's subject & courses
    mongo_query = {
        "StudentID": clean_roll,
        "CourseSubject": teacher_subject,
        "CourseName": {"$in": teacher_course_names}
    }

    # Optional course_id filter
    if course_id and course_id.strip() and course_id != "ALL":
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format."
            )
        target_course = await database.courses.find_one({"_id": ObjectId(course_id)})
        if not target_course or target_course["teacher_id"] != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view dataset events for your own courses."
            )
        mongo_query["$or"] = [
            {"CourseID": str(course_id)},
            {"CourseName": target_course["course_name"]}
        ]

    # Optional event_type filter
    if event_type and event_type.strip() and event_type.upper() != "ALL":
        mongo_query["EventType"] = event_type.strip().upper()

    events_cursor = database.interaction_events.find(mongo_query).sort("created_at", -1)
    events = await events_cursor.to_list(length=1000)

    return [
        InteractionEventResponse(
            id=str(e["_id"]),
            StudentID=e["StudentID"],
            StudentName=e["StudentName"],
            CourseID=e.get("CourseID"),
            CourseSubject=e["CourseSubject"],
            CourseName=e["CourseName"],
            EventType=e["EventType"],
            EventTimestamp=e["EventTimestamp"],
            EventDuration=e.get("EventDuration"),
            PlaybackSpeed=e.get("PlaybackSpeed"),
            PauseReason=e.get("PauseReason")
        )
        for e in events
    ]


@router.get("/students/{roll_number}/concept-mappings", response_model=List[ConceptEventMappingResponse])
async def get_student_concept_mappings(
    roll_number: str,
    course_id: Optional[str] = Query(None, description="Filter by Course ID"),
    event_type: Optional[str] = Query(None, description="Filter by Event Type"),
    concept: Optional[str] = Query(None, description="Filter by Concept Name"),
    search: Optional[str] = Query(None, description="Search text in Concept or Transcript"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve CogniTrace Phase 7 Concept-Event Mapping dataset for a student.
    Connects student interaction telemetry events to Phase 4 transcripts and Phase 6 concepts.
    Enforces strict teacher academic year, subject, and course authorization.
    """
    database = await get_database()
    clean_roll = roll_number.strip().upper()
    teacher_id = current_teacher["identifier"]
    teacher_year = current_teacher["year"]
    teacher_subject = current_teacher["subject"]

    # 1. Verify student exists and belongs to teacher's academic year
    student = await database.students.find_one({"roll_number": clean_roll})
    if not student or student["year"] != teacher_year:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student does not belong to your authorized academic year."
        )

    # 2. Get teacher's courses to enforce strict ownership filter
    cursor = database.courses.find({
        "teacher_id": teacher_id,
        "year": teacher_year,
        "subject": teacher_subject
    })
    teacher_courses = await cursor.to_list(length=200)
    teacher_course_names = [c["course_name"] for c in teacher_courses]

    if not teacher_course_names:
        return []

    # 3. Run Phase 7 mapping service on demand to process any new unmapped events
    mapped_items = await MappingService.map_events_to_concepts(
        database, clean_roll, teacher_subject, teacher_course_names
    )

    # 4. Filter results based on query parameters
    filtered = mapped_items

    # Filter by target course_id if provided
    if course_id and course_id.strip() and course_id != "ALL":
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format."
            )
        target_course = await database.courses.find_one({"_id": ObjectId(course_id)})
        if not target_course or target_course["teacher_id"] != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view dataset events for your own courses."
            )
        target_c_name = target_course["course_name"]
        target_c_id = str(target_course["_id"])
        filtered = [m for m in filtered if m.get("CourseID") == target_c_id or m["CourseName"] == target_c_name]

    # Filter by event_type if provided
    if event_type and event_type.strip() and event_type.upper() != "ALL":
        target_et = event_type.strip().upper()
        filtered = [m for m in filtered if m["EventType"].upper() == target_et]

    # Filter by concept if provided
    if concept and concept.strip() and concept.upper() != "ALL":
        target_c = concept.strip().lower()
        filtered = [m for m in filtered if target_c in m["Concept"].lower()]

    # Filter by search string if provided
    if search and search.strip():
        q_str = search.strip().lower()
        filtered = [
            m for m in filtered
            if q_str in m["Concept"].lower()
            or q_str in m["Transcript"].lower()
            or q_str in m["CourseName"].lower()
            or q_str in m["EventType"].lower()
        ]

    return [ConceptEventMappingResponse(**m) for m in filtered]


@router.get("/students/{roll_number}/difficulty", response_model=List[DifficultyDatasetResponse])
async def get_student_difficulty(
    roll_number: str,
    course_id: Optional[str] = Query(None, description="Filter by Course ID"),
    difficulty_level: Optional[str] = Query(None, description="Filter by Difficulty Level"),
    needs_revision: Optional[bool] = Query(None, description="Filter by Needs Revision"),
    search: Optional[str] = Query(None, description="Search text in Concept or Course Name"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve CogniTrace Phase 8 Difficulty dataset for a student.
    Derives deterministic difficulty metrics from interaction telemetry and concept mappings.
    Enforces strict teacher academic year, subject, and course authorization.
    """
    database = await get_database()
    clean_roll = roll_number.strip().upper()
    teacher_id = current_teacher["identifier"]
    teacher_year = current_teacher["year"]
    teacher_subject = current_teacher["subject"]

    # 1. Verify student exists and belongs to teacher's academic year
    student = await database.students.find_one({"roll_number": clean_roll})
    if not student or student["year"] != teacher_year:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student does not belong to your authorized academic year."
        )

    # 2. Get teacher's courses to enforce strict ownership filter
    cursor = database.courses.find({
        "teacher_id": teacher_id,
        "year": teacher_year,
        "subject": teacher_subject
    })
    teacher_courses = await cursor.to_list(length=200)
    teacher_course_names = [c["course_name"] for c in teacher_courses]

    if not teacher_course_names:
        return []

    # 3. First ensure Phase 7 mappings are up to date
    await MappingService.map_events_to_concepts(
        database, clean_roll, teacher_subject, teacher_course_names
    )

    # 4. Run Phase 8 difficulty generation service on demand
    difficulty_items = await DifficultyService.generate_difficulty_dataset(
        database, clean_roll, teacher_subject, teacher_course_names
    )

    # 5. Filter results based on query parameters
    filtered = difficulty_items

    # Filter by target course_id if provided
    if course_id and course_id.strip() and course_id != "ALL":
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format."
            )
        target_course = await database.courses.find_one({"_id": ObjectId(course_id)})
        if not target_course or target_course["teacher_id"] != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view dataset events for your own courses."
            )
        target_c_name = target_course["course_name"]
        target_c_id = str(target_course["_id"])
        filtered = [m for m in filtered if m.get("CourseID") == target_c_id or m["CourseName"] == target_c_name]

    # Filter by difficulty_level if provided
    if difficulty_level and difficulty_level.strip() and difficulty_level.upper() != "ALL":
        target_dl = difficulty_level.strip().title()
        filtered = [m for m in filtered if m["DifficultyLevel"] == target_dl]

    # Filter by needs_revision if provided
    if needs_revision is not None:
        filtered = [m for m in filtered if m["NeedsRevision"] is needs_revision]

    # Filter by search string if provided
    if search and search.strip():
        q_str = search.strip().lower()
        filtered = [
            m for m in filtered
            if q_str in m["Concept"].lower()
            or q_str in m["CourseName"].lower()
        ]

    return [DifficultyDatasetResponse(**m) for m in filtered]


@router.get("/students/{roll_number}/interactions/export")
async def export_student_interaction_dataset(
    roll_number: str,
    course_id: Optional[str] = Query(None, description="Filter by Course ID"),
    event_type: Optional[str] = Query(None, description="Filter by Event Type"),
    format: str = Query("csv", description="Export format: csv, json, xlsx"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Export Phase 5 Interaction Telemetry.
    """
    results = await get_student_interaction_dataset(roll_number, course_id, event_type, current_teacher)
    data = [r.model_dump(exclude={"id"}) for r in results]
    fieldnames = [
        "StudentID", "StudentName", "CourseSubject", "CourseName", 
        "EventType", "EventTimestamp", "EventDuration", "PlaybackSpeed", "PauseReason"
    ]
    return ExportService.get_export_response(data, fieldnames, "interaction_telemetry", format.lower())


@router.get("/students/{roll_number}/concept-mappings/export")
async def export_student_concept_mappings(
    roll_number: str,
    course_id: Optional[str] = Query(None, description="Filter by Course ID"),
    event_type: Optional[str] = Query(None, description="Filter by Event Type"),
    concept: Optional[str] = Query(None, description="Filter by Concept Name"),
    search: Optional[str] = Query(None, description="Search text in Concept or Transcript"),
    format: str = Query("csv", description="Export format: csv, json, xlsx"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Export Phase 7 Concept-Event Mapping Dataset.
    """
    results = await get_student_concept_mappings(roll_number, course_id, event_type, concept, search, current_teacher)
    data = [r.model_dump(exclude={"id"}) for r in results]
    fieldnames = [
        "StudentID", "StudentName", "CourseSubject", "CourseName", 
        "EventType", "EventTimestamp", "Transcript", "Concept", "Prerequisite"
    ]
    return ExportService.get_export_response(data, fieldnames, "concept_event_mapping", format.lower())


@router.get("/students/{roll_number}/difficulty/export")
async def export_student_difficulty(
    roll_number: str,
    course_id: Optional[str] = Query(None, description="Filter by Course ID"),
    difficulty_level: Optional[str] = Query(None, description="Filter by Difficulty Level"),
    needs_revision: Optional[bool] = Query(None, description="Filter by Needs Revision"),
    search: Optional[str] = Query(None, description="Search text in Concept or Course Name"),
    format: str = Query("csv", description="Export format: csv, json, xlsx"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Export Phase 8 Difficulty Dataset.
    """
    results = await get_student_difficulty(roll_number, course_id, difficulty_level, needs_revision, search, current_teacher)
    data = [r.model_dump(exclude={"id"}) for r in results]
    fieldnames = [
        "StudentID", "StudentName", "CourseSubject", "CourseName", "Concept",
        "ReplayCount", "PauseCount", "SeekBackwardCount", "SeekForwardCount", "UnderstandPauseCount",
        "DifficultyScore", "DifficultyLevel", "NeedsRevision"
    ]
    return ExportService.get_export_response(data, fieldnames, "difficulty", format.lower())
