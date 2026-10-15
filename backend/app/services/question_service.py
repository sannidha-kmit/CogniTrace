import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.db.mongodb import get_database
from app.services.claude_service import ClaudeService
from app.schemas.question import (
    GeneratedMCQ,
    TeacherQuestionResponse,
    StudentQuestionResponse,
    QuestionSubmissionResponse
)

logger = logging.getLogger(__name__)


def parse_timestamp_to_seconds(ts: Any) -> float:
    """Helper to convert MM:SS, HH:MM:SS or numeric values to seconds."""
    if isinstance(ts, (int, float)):
        return float(ts)
    if not ts or not isinstance(ts, str):
        return 0.0
    ts_str = ts.strip()
    try:
        parts = list(map(float, ts_str.split(":")))
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        pass
    return 0.0


def compute_question_hash(question_text: str) -> str:
    """
    Generate normalized SHA256 hash of question text for deterministic duplicate detection.
    Normalizes whitespace and converts to lowercase.
    """
    normalized = re.sub(r'\s+', ' ', question_text.strip().lower())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def derive_concept_ref(course_id: str, concept_name: str) -> str:
    """
    Derive stable, deterministic concept reference for Question Bank without altering concept_segments DB.
    Format: course_id:concept_name
    """
    clean_name = re.sub(r'\s+', '_', concept_name.strip())
    return f"{course_id}:{clean_name}"


class QuestionService:
    @staticmethod
    async def extract_transcript_for_concept(
        course_id: str,
        concept_identifier: str
    ) -> Tuple[str, str, str]:
        """
        Locate concept segment and extract corresponding transcript text.
        Returns (concept_ref, concept_name, transcript_text).
        """
        database = await get_database()

        # 1. Retrieve course_transcripts document
        tx_doc = await database.course_transcripts.find_one({"course_id": course_id})
        if not tx_doc or tx_doc.get("status") != "COMPLETED":
            raise ValueError("Transcript is required and must be COMPLETED before generating questions.")

        tx_segments = tx_doc.get("segments", [])
        if not tx_segments:
            raise ValueError("Course transcript contains no segments.")

        # 2. Retrieve concept_segments document
        concept_doc = await database.concept_segments.find_one({"course_id": course_id})
        if not concept_doc or concept_doc.get("status") != "COMPLETED":
            # Auto-extract concepts if transcript is COMPLETED
            if tx_doc and tx_doc.get("status") == "COMPLETED" and tx_segments:
                course_doc = None
                if ObjectId.is_valid(course_id):
                    course_doc = await database.courses.find_one({"_id": ObjectId(course_id)})
                if not course_doc:
                    course_doc = await database.courses.find_one({"_id": str(course_id)})

                subj = course_doc.get("subject", "") if course_doc else ""
                cname = course_doc.get("course_name", "") if course_doc else ""
                t_id = course_doc.get("teacher_id", "") if course_doc else ""
                t_name = course_doc.get("teacher_name", "") if course_doc else ""

                from app.services.concept_service import ConceptService
                extracted_concepts = ConceptService.extract_concepts_from_transcript(
                    tx_segments,
                    subject_name=subj,
                    course_name=cname
                )
                if extracted_concepts:
                    now = datetime.now(timezone.utc)
                    await database.concept_segments.update_one(
                        {"course_id": course_id},
                        {
                            "$set": {
                                "course_id": course_id,
                                "CourseSubject": subj,
                                "CourseName": cname,
                                "teacher_id": t_id,
                                "teacher_name": t_name,
                                "status": "COMPLETED",
                                "segments": extracted_concepts,
                                "error_message": None,
                                "created_at": now,
                                "updated_at": now
                            }
                        },
                        upsert=True
                    )
                    concept_doc = await database.concept_segments.find_one({"course_id": course_id})

        raw_concepts = concept_doc.get("segments", []) if concept_doc else []
        if not raw_concepts:
            concept_name = concept_identifier.strip() or "General Concepts"
            raw_concepts = [{"Concept": concept_name, "ConceptStart": "00:00", "ConceptEnd": "99:99:99"}]

        # 3. Match all requested concept segments (concepts may span multiple intervals)
        matched_segments = []
        if concept_identifier.isdigit():
            idx = int(concept_identifier)
            if 0 <= idx < len(raw_concepts):
                matched_segments = [raw_concepts[idx]]
        if not matched_segments:
            # Exact match (case insensitive)
            matched_segments = [
                c for c in raw_concepts
                if c.get("Concept", "").strip().lower() == concept_identifier.strip().lower()
            ]
        if not matched_segments:
            # Substring match
            matched_segments = [
                c for c in raw_concepts
                if concept_identifier.strip().lower() in c.get("Concept", "").strip().lower()
            ]

        if not matched_segments:
            # Fallback: if concept is in course or questions, create a general span
            concept_name = concept_identifier.strip()
            matched_segments = [{"Concept": concept_name, "ConceptStart": "00:00", "ConceptEnd": "99:99:99"}]

        concept_name = matched_segments[0].get("Concept", concept_identifier.strip())
        concept_ref = derive_concept_ref(course_id, concept_name)

        # 4. Filter transcript text across all matched concept timestamp ranges
        extracted_texts = []
        for c in matched_segments:
            c_start_sec = parse_timestamp_to_seconds(c.get("ConceptStart", "00:00"))
            c_end_sec = parse_timestamp_to_seconds(c.get("ConceptEnd", "99:99:99"))

            for s in tx_segments:
                s_start = parse_timestamp_to_seconds(s.get("start", s.get("TranscriptStart", 0)))
                s_end = parse_timestamp_to_seconds(s.get("end", s.get("TranscriptEnd", 0)))

                # Segment falls strictly within concept timestamp range or overlaps
                if s_end > c_start_sec and s_start < c_end_sec:
                    t = s.get("text", "").strip()
                    if t and t not in extracted_texts:
                        extracted_texts.append(t)

        # STRICT REQUIREMENT: Only the transcript segments belonging to that concept are sent
        raw_transcript_text = " ".join([t for t in extracted_texts if t])
        from app.services.claude_service import clean_educational_transcript
        transcript_text = clean_educational_transcript(raw_transcript_text)
        if not transcript_text.strip():
            transcript_text = ""

        return concept_ref, concept_name, transcript_text

    @staticmethod
    async def generate_and_store_questions(
        course_id: str,
        concept_identifier: str,
        count: int = 3,
        target_difficulty: Optional[str] = None,
        course_name: Optional[str] = None,
        pause_count: Optional[int] = None,
        pause_timestamps: Optional[List[str]] = None,
        quiz_priority: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> List[TeacherQuestionResponse]:
        """
        Flow:
        course_id -> find transcript -> find concept -> extract concept-specific transcript text
        -> send to Gemini with ML-derived priority & confidence -> validate schema -> check duplicates
        -> store in MongoDB questions collection.
        """
        database = await get_database()

        # 1. Extract transcript text strictly for concept
        concept_ref, concept_name, transcript_text = await QuestionService.extract_transcript_for_concept(
            course_id, concept_identifier
        )

        if not transcript_text.strip():
            logger.warning("No educational transcript content found for concept '%s' in course '%s'.", concept_name, course_id)
            return []

        # 2. Call Gemini API to generate questions with ML priority and confidence context
        mcqs: List[GeneratedMCQ] = await ClaudeService.generate_mcqs_from_transcript(
            transcript_text=transcript_text,
            concept_name=concept_name,
            count=count,
            target_difficulty=target_difficulty,
            course_name=course_name,
            pause_count=pause_count,
            pause_timestamps=pause_timestamps,
            quiz_priority=quiz_priority,
            confidence=confidence
        )

        # 3. Validate and store non-duplicate, approved questions in MongoDB questions collection
        from app.services.question_validation_service import QuestionValidationService
        stored_questions: List[TeacherQuestionResponse] = []
        now = datetime.now(timezone.utc)
        seen_hashes = set()

        for mcq in mcqs:
            q_hash = compute_question_hash(mcq.question)

            if q_hash in seen_hashes:
                logger.info("Skipping intra-request duplicate question: %s", mcq.question[:40])
                continue
            seen_hashes.add(q_hash)

            # Duplicate check in database
            existing = await database.questions.find_one({
                "course_id": course_id,
                "question_hash": q_hash
            })

            if existing:
                logger.info("Skipping duplicate question: %s", mcq.question[:40])
                stored_questions.append(
                    TeacherQuestionResponse(
                        id=str(existing["_id"]),
                        course_id=existing["course_id"],
                        concept_ref=existing["concept_ref"],
                        concept_name=existing["concept_name"],
                        question=existing["question"],
                        options=existing["options"],
                        correct_answer=existing["correct_answer"],
                        difficulty=existing["difficulty"],
                        explanation=existing["explanation"],
                        created_at=existing.get("created_at", now)
                    )
                )
                continue

            # Run Question Validation Layer
            val_res = await QuestionValidationService.validate_mcq(
                mcq=mcq,
                course_id=course_id,
                concept_name=concept_name,
                target_difficulty=target_difficulty,
                transcript_text=transcript_text
            )

            if val_res.status == "rejected":
                logger.warning(
                    "[QUESTION VALIDATION] Rejected generated question '%s': %s (score=%.2f)",
                    mcq.question[:40], ", ".join(val_res.rejection_reasons), val_res.validation_score
                )
                continue

            q_doc = {
                "course_id": course_id,
                "concept_ref": concept_ref,
                "concept_name": concept_name,
                "question": mcq.question,
                "question_hash": q_hash,
                "options": mcq.options,
                "correct_answer": mcq.correct_answer,
                "difficulty": mcq.difficulty,
                "explanation": mcq.explanation,
                "learning_point": mcq.learning_point,
                "source_evidence": mcq.source_evidence,
                "validation_score": val_res.validation_score,
                "validation_status": val_res.status,
                "created_at": now,
                "updated_at": now
            }

            try:
                res = await database.questions.insert_one(q_doc)
                q_id = str(res.inserted_id)
                stored_questions.append(
                    TeacherQuestionResponse(
                        id=q_id,
                        course_id=course_id,
                        concept_ref=concept_ref,
                        concept_name=concept_name,
                        question=mcq.question,
                        options=mcq.options,
                        correct_answer=mcq.correct_answer,
                        difficulty=mcq.difficulty,
                        explanation=mcq.explanation,
                        created_at=now
                    )
                )
            except DuplicateKeyError:
                logger.warning("Duplicate key caught on insert: %s", mcq.question[:40])
                dup = await database.questions.find_one({"course_id": course_id, "question_hash": q_hash})
                if dup:
                    stored_questions.append(
                        TeacherQuestionResponse(
                            id=str(dup["_id"]),
                            course_id=dup["course_id"],
                            concept_ref=dup["concept_ref"],
                            concept_name=dup["concept_name"],
                            question=dup["question"],
                            options=dup["options"],
                            correct_answer=dup["correct_answer"],
                            difficulty=dup["difficulty"],
                            explanation=dup["explanation"],
                            created_at=dup.get("created_at", now)
                        )
                    )

        return stored_questions

    @staticmethod
    async def get_questions_for_teacher(
        course_id: str,
        concept_ref: Optional[str] = None,
        difficulty: Optional[str] = None,
        count: Optional[int] = None
    ) -> List[TeacherQuestionResponse]:
        """Retrieve questions for teacher including correct_answer and explanation."""
        database = await get_database()
        query: Dict[str, Any] = {"course_id": course_id}

        if concept_ref:
            query["$or"] = [
                {"concept_ref": concept_ref},
                {"concept_name": {"$regex": re.escape(concept_ref), "$options": "i"}}
            ]
        if difficulty:
            query["difficulty"] = difficulty.strip().upper()

        cursor = database.questions.find(query).sort("created_at", -1)
        if count and count > 0:
            cursor = cursor.limit(count)

        results = []
        async for doc in cursor:
            results.append(
                TeacherQuestionResponse(
                    id=str(doc["_id"]),
                    course_id=doc["course_id"],
                    concept_ref=doc["concept_ref"],
                    concept_name=doc.get("concept_name", "Concept"),
                    question=doc["question"],
                    options=doc["options"],
                    correct_answer=doc["correct_answer"],
                    difficulty=doc["difficulty"],
                    explanation=doc["explanation"],
                    created_at=doc.get("created_at", datetime.now(timezone.utc))
                )
            )
        return results

    @staticmethod
    async def get_questions_for_student(
        course_id: str,
        concept_ref: Optional[str] = None,
        difficulty: Optional[str] = None,
        count: Optional[int] = None
    ) -> List[StudentQuestionResponse]:
        """
        STUDENT SECURITY METHOD:
        Retrieves questions for student consumption.
        EXCLUDES correct_answer and explanation completely from response to prevent leakage.
        """
        database = await get_database()
        query: Dict[str, Any] = {"course_id": course_id}

        if concept_ref:
            query["$or"] = [
                {"concept_ref": concept_ref},
                {"concept_name": {"$regex": re.escape(concept_ref), "$options": "i"}}
            ]
        if difficulty:
            query["difficulty"] = difficulty.strip().upper()

        cursor = database.questions.find(query).sort("created_at", -1)
        if count and count > 0:
            cursor = cursor.limit(count)

        results = []
        async for doc in cursor:
            results.append(
                StudentQuestionResponse(
                    id=str(doc["_id"]),
                    course_id=doc["course_id"],
                    concept_ref=doc["concept_ref"],
                    concept_name=doc.get("concept_name", "Concept"),
                    question=doc["question"],
                    options=doc["options"],
                    difficulty=doc["difficulty"]
                )
            )
        return results

    @staticmethod
    async def submit_student_answer(
        question_id: str,
        selected_option: str
    ) -> QuestionSubmissionResponse:
        """Process student answer submission and return correctness and explanation after submission."""
        database = await get_database()
        if not ObjectId.is_valid(question_id):
            raise ValueError("Invalid question ID format.")

        question = await database.questions.find_one({"_id": ObjectId(question_id)})
        if not question:
            raise ValueError("Question not found.")

        is_correct = (selected_option.strip() == question["correct_answer"].strip())

        return QuestionSubmissionResponse(
            question_id=question_id,
            is_correct=is_correct,
            correct_answer=question["correct_answer"],
            explanation=question["explanation"]
        )

    @staticmethod
    async def auto_generate_for_student_telemetry(
        course_id: str,
        student_id: str
    ) -> List[StudentQuestionResponse]:
        """
        ACTUAL STUDENT FLOW INTEGRATION:
        1. Queries interaction_events for student's pause telemetry for the course.
        2. Derives total pause count and maps to question count N.
        3. Identifies concept segments associated with pause timestamps.
        4. Triggers Claude generation for target concept segments using extracted transcript text.
        5. Returns student-safe questions (excludes correct_answer & explanation).
        """
        database = await get_database()

        # First check if transcript and concepts are ready
        tx_doc = await database.course_transcripts.find_one({"course_id": course_id})
        if not tx_doc or tx_doc.get("status") != "COMPLETED":
            tx_status = tx_doc.get("status", "NOT_STARTED") if tx_doc else "NOT_STARTED"
            raise ValueError(
                f"Course transcript is not ready (status: {tx_status}). "
                "The teacher must generate the transcript before questions can be created."
            )

        concept_doc = await database.concept_segments.find_one({"course_id": course_id})
        if not concept_doc or concept_doc.get("status") != "COMPLETED":
            if tx_doc and tx_doc.get("status") == "COMPLETED" and tx_doc.get("segments"):
                course_doc = None
                if ObjectId.is_valid(course_id):
                    course_doc = await database.courses.find_one({"_id": ObjectId(course_id)})
                if not course_doc:
                    course_doc = await database.courses.find_one({"_id": str(course_id)})

                subj = course_doc.get("subject", "") if course_doc else ""
                cname = course_doc.get("course_name", "") if course_doc else ""
                t_id = course_doc.get("teacher_id", "") if course_doc else ""
                t_name = course_doc.get("teacher_name", "") if course_doc else ""

                from app.services.concept_service import ConceptService
                extracted_concepts = ConceptService.extract_concepts_from_transcript(
                    tx_doc["segments"],
                    subject_name=subj,
                    course_name=cname
                )
                if extracted_concepts:
                    now = datetime.now(timezone.utc)
                    await database.concept_segments.update_one(
                        {"course_id": course_id},
                        {
                            "$set": {
                                "course_id": course_id,
                                "CourseSubject": subj,
                                "CourseName": cname,
                                "teacher_id": t_id,
                                "teacher_name": t_name,
                                "status": "COMPLETED",
                                "segments": extracted_concepts,
                                "error_message": None,
                                "created_at": now,
                                "updated_at": now
                            }
                        },
                        upsert=True
                    )
                    concept_doc = await database.concept_segments.find_one({"course_id": course_id})

        raw_concepts = concept_doc.get("segments", []) if concept_doc else []
        if not raw_concepts:
            raw_concepts = [{"Concept": "Core Concepts", "ConceptStart": "00:00", "ConceptEnd": "99:99:99"}]

        # 1. Fetch telemetry events for student & course (PAUSE and SEEK_BACKWARD)
        cursor = database.interaction_events.find({
            "CourseID": course_id,
            "StudentID": student_id,
            "EventType": {"$in": ["PAUSE", "SEEK_BACKWARD"]}
        })
        pause_events = await cursor.to_list(length=100)
        pause_count = len(pause_events)
        target_q_count = map_pause_count_to_question_count(pause_count)

        logger.info(
            "[QUESTION SERVICE] Student %s has %d PAUSE events for course %s. Target: %d questions/concept.",
            student_id, pause_count, course_id, target_q_count
        )

        # 2. Match pause timestamps to concepts
        target_concept_names = set()
        for event in pause_events:
            event_ts = event.get("EventTimestamp", "00:00")
            ts_sec = parse_timestamp_to_seconds(event_ts)
            for c in raw_concepts:
                c_start = parse_timestamp_to_seconds(c.get("ConceptStart", "00:00"))
                c_end = parse_timestamp_to_seconds(c.get("ConceptEnd", "99:99:99"))
                if c_start <= ts_sec <= c_end:
                    c_name = c.get("Concept")
                    if c_name:
                        target_concept_names.add(c_name)

        # Fallback to course concepts if student hasn't paused or no specific segment matched
        if not target_concept_names:
            target_concept_names = {c.get("Concept") for c in raw_concepts if c.get("Concept")}
            if not target_concept_names:
                target_concept_names = {"Core Concepts"}

        # 3. Get course name from course doc or concept_doc
        course_doc = await database.courses.find_one({"_id": ObjectId(course_id)})
        course_name = course_doc.get("course_name", "") if course_doc else concept_doc.get("CourseName", "")
        pause_timestamps = [e.get("EventTimestamp", "00:00") for e in pause_events if e.get("EventTimestamp")]

        # 4. Generate & store questions for target concepts if needed
        for c_name in target_concept_names:
            existing_q_count = await database.questions.count_documents({
                "course_id": course_id,
                "concept_name": c_name
            })
            
            if existing_q_count >= target_q_count:
                logger.info(
                    "[QUESTION SERVICE] Concept '%s' already has %d questions (target %d). Skipping generation.",
                    c_name, existing_q_count, target_q_count
                )
                continue
                
            needed = target_q_count - existing_q_count
            logger.info("[QUESTION SERVICE] Generating %d new questions for concept: '%s'", needed, c_name)
            await QuestionService.generate_and_store_questions(
                course_id=course_id,
                concept_identifier=c_name,
                count=needed,
                course_name=course_name,
                pause_count=pause_count,
                pause_timestamps=pause_timestamps
            )

        # 5. Return student-safe questions
        return await QuestionService.get_questions_for_student(course_id)


def map_pause_count_to_question_count(pause_count: int) -> int:
    """
    Configurable deterministic mapping from student pause count to number of questions.
    0-1 pauses -> 2 questions per concept
    2-4 pauses -> 3 questions per concept
    5-7 pauses -> 4 questions per concept
    8+ pauses  -> 5 questions per concept
    """
    if pause_count <= 1:
        return 2
    elif pause_count <= 4:
        return 3
    elif pause_count <= 7:
        return 4
    else:
        return 5
