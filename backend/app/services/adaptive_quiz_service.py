import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId

from app.core.quiz_config import quiz_settings
from app.db.mongodb import get_database
from app.schemas.quiz import (
    QuizPriorityEnum,
    QuizSessionStatus,
    ConceptPriority,
    SafeQuizQuestion,
    InternalQuizQuestion,
    StartQuizResponse,
    CurrentQuestionResponse,
    SubmitAnswerResponse,
    FinishQuizResponse,
    QuizResultResponse,
    ConceptResultBreakdown,
    LearningSupport,
    RevisionResource,
    AdaptiveQuizResponse,
    AdaptiveQuizQuestionItem,
    BulkSubmitRequest,
    BulkSubmitResponse,
    QuestionResult,
    ConceptPerformance,
    ConceptMapNode,
    ConceptMapData
)
from app.services.adapters.feature_service_adapter import FeatureServiceAdapter
from app.services.adapters.ml_inference_service import ml_service
from app.services.adapters.question_bank_adapter import QuestionBankAdapter
from app.services.explanation_service import ExplanationService
from app.services.learning_resource_service import LearningResourceService
from app.services.question_service import QuestionService
from app.repositories.quiz_session_repository import QuizSessionRepository


logger = logging.getLogger("cognitrace.quiz.service")


class AdaptiveQuizService:
    """
    Central Adaptive Quiz Service Orchestrator (Member 3).
    Coordinates Feature Service (Member 5) -> ML Inference (Member 1) ->
    Concept Priorities -> Question Allocation -> Question Bank (Member 2) ->
    Quiz Session Management & Deterministic Difficulty Adaptation.
    """

    @classmethod
    def calculate_question_allocation(
        cls,
        priorities: List[ConceptPriority],
        total_questions: int
    ) -> List[ConceptPriority]:
        """
        Deterministic Question Allocation Algorithm.
        Allocates `total_questions` across concepts proportionally based on priority weights.
        Handles edge cases: single concept, rounding remainders, zero concepts.
        """
        if not priorities:
            return []

        if len(priorities) == 1:
            priorities[0].allocated_count = total_questions
            return priorities

        # 1. Sum up baseline weights for present concepts
        weights = [quiz_settings.ALLOCATION_WEIGHTS.get(p.priority.value, 0.2) for p in priorities]
        total_weight = sum(weights) or 1.0

        allocated_counts = []
        for w in weights:
            count = int(round((w / total_weight) * total_questions))
            # Ensure at least 1 question per concept if total_questions permits
            count = max(1, count)
            allocated_counts.append(count)

        # 2. Adjust for rounding differences so sum(allocated_counts) == total_questions
        current_sum = sum(allocated_counts)
        diff = total_questions - current_sum

        # Sort indices by priority (HIGH first, then MEDIUM, then LOW)
        priority_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        indexed_priorities = sorted(
            range(len(priorities)),
            key=lambda i: (priority_rank.get(priorities[i].priority.value, 0), priorities[i].score),
            reverse=True
        )

        idx_ptr = 0
        while diff != 0 and idx_ptr < len(priorities) * 2:
            target_idx = indexed_priorities[idx_ptr % len(priorities)]
            if diff > 0:
                allocated_counts[target_idx] += 1
                diff -= 1
            elif diff < 0:
                if allocated_counts[target_idx] > 1:
                    allocated_counts[target_idx] -= 1
                    diff += 1
            idx_ptr += 1

        # Assign final allocated counts
        for i, p in enumerate(priorities):
            p.allocated_count = allocated_counts[i]

        return priorities

    @classmethod
    async def start_quiz(
        cls,
        student_id: str,
        course_id: str,
        total_questions: Optional[int] = None
    ) -> StartQuizResponse:
        """
        Start an adaptive quiz session.
        Full Flow:
        Features -> ML Inference -> Concept Priority -> Question Allocation -> Question Bank -> Session Created.
        """
        clean_student = student_id.strip().upper()
        q_total = total_questions or quiz_settings.DEFAULT_TOTAL_QUESTIONS
        q_total = max(quiz_settings.MIN_TOTAL_QUESTIONS, min(quiz_settings.MAX_TOTAL_QUESTIONS, q_total))

        logger.info(
            "[ADAPTIVE QUIZ] Starting quiz for Student=%s, Course=%s, TotalQuestions=%d",
            clean_student, course_id, q_total
        )

        # 1. Member 5: Retrieve concept features
        concept_features_list = await FeatureServiceAdapter.get_concept_features(clean_student, course_id)

        # 2. Member 1: ML Model inference to derive concept priorities
        priorities: List[ConceptPriority] = []
        for cf in concept_features_list:
            prediction = ml_service.predict(cf.features)
            priorities.append(
                ConceptPriority(
                    concept_id=cf.concept_id,
                    concept_name=cf.concept_name,
                    priority=prediction.priority,
                    score=prediction.score
                )
            )

        # Sort priorities (HIGH -> MEDIUM -> LOW, then by score descending)
        priority_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        priorities.sort(key=lambda p: (priority_rank.get(p.priority.value, 0), p.score), reverse=True)

        # 3. Question Allocation across concepts
        priorities = cls.calculate_question_allocation(priorities, q_total)

        # 4. Member 2: Retrieve questions from Question Bank
        quiz_questions: List[InternalQuizQuestion] = []
        used_question_ids = []

        current_diff = quiz_settings.INITIAL_DIFFICULTY

        for p in priorities:
            if p.allocated_count <= 0:
                continue

            fetched = await QuestionBankAdapter.get_questions(
                course_id=course_id,
                concept_id=p.concept_id,
                difficulty=current_diff,
                count=p.allocated_count,
                excluded_ids=used_question_ids
            )
            for q in fetched[:p.allocated_count]:
                quiz_questions.append(q)
                used_question_ids.append(q.question_id)

        # If question bank was short on questions, retrieve additional questions from course to reach total
        if len(quiz_questions) < q_total:
            needed = q_total - len(quiz_questions)
            extra_questions = await QuestionBankAdapter.get_questions(
                course_id=course_id,
                concept_id=None,
                difficulty=None,
                count=needed,
                excluded_ids=used_question_ids
            )
            for eq in extra_questions[:needed]:
                quiz_questions.append(eq)
                used_question_ids.append(eq.question_id)

        if len(quiz_questions) > q_total:
            quiz_questions = quiz_questions[:q_total]


        if not quiz_questions:
            raise ValueError(
                "No questions are currently available in the Question Bank for this course. "
                "Questions must be generated by the teacher first."
            )

        actual_total = len(quiz_questions)

        # 5. Initialize persistent MongoDB Quiz Session
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        session_doc = {
            "quiz_session_id": session_id,
            "student_id": clean_student,
            "course_id": str(course_id),
            "status": "active",
            "started_at": now,
            "completed_at": None,
            "current_question_index": 0,
            "total_questions": actual_total,
            "answered_questions": 0,
            "correct_count": 0,
            "wrong_count": 0,
            "score": 0.0,
            "current_difficulty": current_diff,
            "concept_priorities": [p.model_dump() for p in priorities],
            "allocation_plan": {p.concept_name: p.allocated_count for p in priorities},
            "questions": [q.model_dump() for q in quiz_questions],
            "history": []
        }

        await QuizSessionRepository.create_session(session_doc)

        # 6. Format Safe First Question (no correct answer, no explanation)
        first_q = quiz_questions[0]
        safe_first_q = SafeQuizQuestion(
            quiz_session_id=session_id,
            question_id=first_q.question_id,
            concept_id=first_q.concept_id,
            concept_name=first_q.concept_name,
            question_text=first_q.question_text,
            options=first_q.options,
            difficulty=first_q.difficulty,
            question_number=1,
            total_questions=actual_total
        )

        return StartQuizResponse(
            quiz_session_id=session_id,
            course_id=str(course_id),
            student_id=clean_student,
            status=QuizSessionStatus.ACTIVE,
            current_question=safe_first_q,
            question_number=1,
            total_questions=actual_total,
            started_at=now
        )

    @classmethod
    async def get_current_question(
        cls,
        quiz_session_id: str,
        student_id: str
    ) -> CurrentQuestionResponse:
        """
        Retrieve the current safe question for the session.
        Guarantees that `correct_answer` and `explanation` are NOT leaked to the student.
        """
        clean_student = student_id.strip().upper()
        session = await QuizSessionRepository.get_session(quiz_session_id, clean_student)

        if not session:
            raise ValueError("Quiz session not found or you do not have permission to access it.")

        if session.get("status") != "active":
            raise ValueError("Quiz session has already been completed.")

        questions = session.get("questions", [])
        total = len(questions)
        answered = session.get("answered_questions", 0)

        # Find first unanswered question
        current_idx = None
        for i, q in enumerate(questions):
            if not q.get("answered", False):
                current_idx = i
                break

        if current_idx is None or current_idx >= total:
            # All answered - auto complete
            now = datetime.now(timezone.utc)
            await QuizSessionRepository.finish_session(quiz_session_id, clean_student, now)
            raise ValueError("All questions in this quiz have been answered. The quiz is now completed.")

        target_q = questions[current_idx]
        safe_q = SafeQuizQuestion(
            quiz_session_id=quiz_session_id,
            question_id=target_q["question_id"],
            concept_id=target_q["concept_id"],
            concept_name=target_q.get("concept_name", "General"),
            question_text=target_q["question_text"],
            options=target_q["options"],
            difficulty=target_q.get("difficulty", "MEDIUM"),
            question_number=current_idx + 1,
            total_questions=total
        )

        return CurrentQuestionResponse(
            quiz_session_id=quiz_session_id,
            question=safe_q,
            question_number=current_idx + 1,
            total_questions=total,
            answered_questions=answered,
            status=QuizSessionStatus.ACTIVE
        )

    @classmethod
    async def submit_answer(
        cls,
        quiz_session_id: str,
        student_id: str,
        question_id: str,
        selected_answer: str
    ) -> SubmitAnswerResponse:
        """
        Validate and record student answer submission.
        Evaluates correctness on the backend and adjusts difficulty deterministically.
        """
        clean_student = student_id.strip().upper()
        session = await QuizSessionRepository.get_session(quiz_session_id, clean_student)

        if not session:
            raise ValueError("Quiz session not found or you do not have permission to access it.")

        if session.get("status") != "active":
            raise ValueError("Cannot submit answers to an already completed quiz session.")

        questions = session.get("questions", [])
        total_questions = len(questions)

        # Locate target question in session
        target_q = None
        target_idx = None
        for i, q in enumerate(questions):
            if q.get("question_id") == question_id:
                target_q = q
                target_idx = i
                break

        if not target_q:
            raise ValueError("The specified question does not belong to this quiz session.")

        if target_q.get("answered", False):
            raise ValueError("This question has already been answered.")

        clean_submission = selected_answer.strip()

        # Backend correctness evaluation
        correct_answer = target_q.get("correct_answer", "").strip()
        is_correct = (clean_submission.lower() == correct_answer.lower())

        # Difficulty Adaptation
        current_diff = target_q.get("difficulty", session.get("current_difficulty", "MEDIUM")).upper()
        if is_correct:
            next_diff = quiz_settings.DIFFICULTY_TRANSITIONS_CORRECT.get(current_diff, "HARD")
        else:
            next_diff = quiz_settings.DIFFICULTY_TRANSITIONS_WRONG.get(current_diff, "EASY")

        answered_count = session.get("answered_questions", 0) + 1
        correct_count = session.get("correct_count", 0) + (1 if is_correct else 0)
        wrong_count = session.get("wrong_count", 0) + (0 if is_correct else 1)
        score_pct = round((correct_count / total_questions) * 100.0, 2)

        is_completed = (answered_count >= total_questions)

        # -----------------------------------------------------------------
        # Post-Answer Learning Support: AI Explanation + Video Timestamp Revision
        # -----------------------------------------------------------------
        concept_id = target_q.get("concept_id", "General")
        concept_name = target_q.get("concept_name", "General Concept")
        course_id = session.get("course_id", "")

        # 1. AI Explanation (uses trusted backend is_correct, never lets AI guess correctness)
        explanation_text, explanation_status = await ExplanationService.generate_explanation(
            question_text=target_q.get("question_text", ""),
            student_answer=clean_submission,
            correct_answer=correct_answer,
            concept_name=concept_name,
            is_correct=is_correct,
            existing_explanation=target_q.get("explanation")
        )

        # 2. Learning Video & Timestamp Resource
        revision_resource = await LearningResourceService.get_revision_resource(
            course_id=course_id,
            concept_id=concept_id,
            concept_name=concept_name,
            question_text=target_q.get("question_text", ""),
            correct_answer=correct_answer,
            explanation=explanation_text or target_q.get("explanation")
        )

        learning_support = LearningSupport(
            concept_id=concept_id,
            concept_name=concept_name,
            explanation=explanation_text,
            explanation_status=explanation_status,
            revision=revision_resource
        )

        # -----------------------------------------------------------------
        # Closed-Loop State Update: Update Concept-Level Mastery & Priority
        # -----------------------------------------------------------------
        from app.services.student_state_service import StudentConceptStateService
        await StudentConceptStateService.record_quiz_answer_outcome(
            student_id=clean_student,
            course_id=course_id,
            concept_name=concept_name,
            is_correct=is_correct,
            question_id=question_id,
            difficulty=current_diff
        )

        # Persist submission atomically with learning support metadata
        await QuizSessionRepository.record_answer_submission(
            quiz_session_id=quiz_session_id,
            student_id=clean_student,
            question_id=question_id,
            selected_option=clean_submission,
            is_correct=is_correct,
            current_difficulty=current_diff,
            next_difficulty=next_diff,
            answered_questions=answered_count,
            correct_count=correct_count,
            wrong_count=wrong_count,
            current_score=score_pct,
            is_completed=is_completed,
            learning_support=learning_support.model_dump()
        )

        remaining = max(0, total_questions - answered_count)

        feedback_msg = "Correct! Well done." if is_correct else "Incorrect."

        return SubmitAnswerResponse(
            quiz_session_id=quiz_session_id,
            question_id=question_id,
            is_correct=is_correct,
            answered_questions=answered_count,
            remaining_questions=remaining,
            total_questions=total_questions,
            current_score=score_pct,
            is_completed=is_completed,
            feedback=feedback_msg,
            correct_answer=correct_answer,
            explanation=explanation_text or target_q.get("explanation"),
            learning_support=learning_support
        )


    @classmethod
    async def finish_quiz(
        cls,
        quiz_session_id: str,
        student_id: str
    ) -> FinishQuizResponse:
        """
        Manually or automatically finalize a quiz session.
        Prevents further answer submissions.
        """
        clean_student = student_id.strip().upper()
        session = await QuizSessionRepository.get_session(quiz_session_id, clean_student)

        if not session:
            raise ValueError("Quiz session not found or you do not have permission to access it.")

        now = datetime.now(timezone.utc)
        if session.get("status") != "completed":
            await QuizSessionRepository.finish_session(quiz_session_id, clean_student, now)
            session = await QuizSessionRepository.get_session(quiz_session_id, clean_student)

        total = session.get("total_questions", 0)
        answered = session.get("answered_questions", 0)
        correct = session.get("correct_count", 0)
        wrong = session.get("wrong_count", 0)
        score_pct = round((correct / total * 100.0), 2) if total > 0 else 0.0

        return FinishQuizResponse(
            quiz_session_id=quiz_session_id,
            student_id=clean_student,
            course_id=session.get("course_id", ""),
            status=QuizSessionStatus.COMPLETED,
            total_questions=total,
            answered_questions=answered,
            correct_answers=correct,
            wrong_answers=wrong,
            score_percentage=score_pct,
            completed_at=session.get("completed_at", now)
        )

    @classmethod
    async def get_quiz_result(
        cls,
        quiz_session_id: str,
        student_id: str
    ) -> QuizResultResponse:
        """
        Retrieve comprehensive quiz results with concept-wise accuracy breakdown.
        """
        clean_student = student_id.strip().upper()
        session = await QuizSessionRepository.get_session(quiz_session_id, clean_student)

        if not session:
            raise ValueError("Quiz session not found or you do not have permission to access it.")

        questions = session.get("questions", [])
        total = session.get("total_questions", len(questions))
        answered = session.get("answered_questions", 0)
        correct = session.get("correct_count", 0)
        wrong = session.get("wrong_count", 0)
        score_pct = round((correct / total * 100.0), 2) if total > 0 else 0.0

        # Calculate Concept-Wise Breakdown
        concept_stats: Dict[str, Dict[str, Any]] = {}
        for q in questions:
            c_id = q.get("concept_id", "General")
            c_name = q.get("concept_name", "General Concept")
            if c_id not in concept_stats:
                concept_stats[c_id] = {
                    "concept_id": c_id,
                    "concept_name": c_name,
                    "total": 0,
                    "correct": 0
                }
            concept_stats[c_id]["total"] += 1
            if q.get("is_correct") is True:
                concept_stats[c_id]["correct"] += 1

        priorities_map = {
            p.get("concept_id"): p.get("priority", "MEDIUM")
            for p in session.get("concept_priorities", [])
        }

        breakdowns: List[ConceptResultBreakdown] = []
        for c_id, stat in concept_stats.items():
            tot = stat["total"]
            corr = stat["correct"]
            acc = round((corr / tot * 100.0), 2) if tot > 0 else 0.0
            breakdowns.append(
                ConceptResultBreakdown(
                    concept_id=c_id,
                    concept_name=stat["concept_name"],
                    priority=priorities_map.get(c_id, "MEDIUM"),
                    total_questions=tot,
                    correct_answers=corr,
                    accuracy_percentage=acc
                )
            )

        return QuizResultResponse(
            quiz_session_id=quiz_session_id,
            student_id=clean_student,
            course_id=session.get("course_id", ""),
            status=QuizSessionStatus(session.get("status", "active")),
            total_questions=total,
            answered_questions=answered,
            correct_answers=correct,
            wrong_answers=wrong,
            score_percentage=score_pct,
            started_at=session.get("started_at", datetime.now(timezone.utc)),
            completed_at=session.get("completed_at"),
            concept_breakdown=breakdowns
        )

    @staticmethod
    def _priority_to_target_difficulty(priority: QuizPriorityEnum) -> Optional[str]:
        """
        Map ML priority level to a target question difficulty.
        HIGH priority (student struggles) → EASY/MEDIUM questions to build confidence
        LOW priority (student understands) → HARD questions to challenge
        """
        mapping = {
            "HIGH": "EASY",
            "MEDIUM": "MEDIUM",
            "LOW": "HARD"
        }
        return mapping.get(priority.value, None)

    @classmethod
    async def generate_full_adaptive_quiz(
        cls,
        student_id: str,
        course_id: str,
        course_name: str
    ) -> AdaptiveQuizResponse:
        """
        Generate a complete adaptive quiz with DYNAMIC question generation.
        Flow:
        1. Feature Service → concept telemetry features
        2. ML Inference → concept priorities (HIGH/MEDIUM/LOW)
        3. Concept Map → build from concept segments + difficulty + prerequisites
        4. Dynamic Generation → for concepts lacking enough questions, generate
           new ones via AI (Gemini) using the course transcript
        5. Question Bank → retrieve questions (now includes freshly generated ones)
        6. Session → persist quiz session in MongoDB
        7. Return quiz with concept map visualization data
        """
        clean_student = student_id.strip().upper()
        database = await get_database()

        logger.info(
            "[ADAPTIVE QUIZ] Generating dynamic adaptive quiz for Student=%s, Course=%s",
            clean_student, course_id
        )

        # ── Ensure concept segments exist if transcript is completed ──
        concept_doc = await database.concept_segments.find_one({"course_id": str(course_id)})
        if not concept_doc or concept_doc.get("status") != "COMPLETED":
            tx_doc = await database.course_transcripts.find_one({"course_id": str(course_id)})
            if tx_doc and tx_doc.get("status") == "COMPLETED" and tx_doc.get("segments"):
                course_doc = None
                if ObjectId.is_valid(course_id):
                    course_doc = await database.courses.find_one({"_id": ObjectId(course_id)})
                if not course_doc:
                    course_doc = await database.courses.find_one({"_id": str(course_id)})

                subj = course_doc.get("subject", "") if course_doc else ""
                cname = course_doc.get("course_name", course_name) if course_doc else course_name
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
                        {"course_id": str(course_id)},
                        {
                            "$set": {
                                "course_id": str(course_id),
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

        # ── Step 1: Feature Service — Retrieve concept telemetry features ──
        concept_features_list = await FeatureServiceAdapter.get_concept_features(clean_student, course_id)

        # ── Step 2: ML Inference — Concept priorities ──
        priorities: List[ConceptPriority] = []
        features_by_concept: Dict[str, Dict[str, float]] = {}
        for cf in concept_features_list:
            prediction = ml_service.predict(cf.features)
            priorities.append(
                ConceptPriority(
                    concept_id=cf.concept_id,
                    concept_name=cf.concept_name,
                    priority=prediction.priority,
                    score=prediction.score
                )
            )
            features_by_concept[cf.concept_name] = cf.features

        # Sort priorities (HIGH -> MEDIUM -> LOW, then by confidence score descending)
        priority_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        priorities.sort(key=lambda p: (priority_rank.get(p.priority.value, 0), p.score), reverse=True)

        # ── Step 3: Build Concept Map from concept segments + difficulty records ──
        concept_doc = await database.concept_segments.find_one({"course_id": str(course_id)})
        concept_segments = []
        prerequisite_map: Dict[str, str] = {}
        difficulty_level_map: Dict[str, str] = {}
        if concept_doc and concept_doc.get("status") == "COMPLETED":
            concept_segments = concept_doc.get("segments", [])
            for seg in concept_segments:
                c_name = seg.get("Concept", "")
                if c_name:
                    prerequisite_map[c_name] = seg.get("Prerequisite", "None")
                    difficulty_level_map[c_name] = seg.get("DifficultyLevel", "Easy")

        # Fetch difficulty scores from Phase 8 difficulty collection
        diff_cursor = database.difficulty.find({
            "StudentID": clean_student,
            "CourseID": str(course_id)
        })
        diff_records = await diff_cursor.to_list(length=500)
        difficulty_score_map: Dict[str, float] = {}
        for rec in diff_records:
            c_name = rec.get("Concept", "")
            if c_name:
                difficulty_score_map[c_name] = float(rec.get("DifficultyScore", 0.0))

        # ── Step 4: Dynamic Question Generation (Student Telemetry & Concept-Driven) ──
        # Fetch student's real interaction telemetry events for this course
        events_cursor = database.interaction_events.find({
            "StudentID": {"$regex": f"^{re.escape(clean_student)}$", "$options": "i"},
            "CourseID": str(course_id)
        }).sort("created_at", 1)
        student_events = await events_cursor.to_list(length=1000)

        # Fetch question IDs already answered by student in recent sessions to avoid repeats
        recently_seen_ids = set()
        past_sessions = await database.quiz_sessions.find({
            "student_id": clean_student,
            "course_id": str(course_id)
        }).sort("started_at", -1).limit(10).to_list(length=10)
        for ps in past_sessions:
            for q in ps.get("questions", []):
                if q.get("question_id"):
                    recently_seen_ids.add(q["question_id"])

        # Build concept timestamp intervals for precise event-to-concept mapping
        from app.services.mapping_service import parse_timestamp_to_seconds
        concept_time_ranges: Dict[str, List[tuple[float, float]]] = {}
        for seg in concept_segments:
            c_name = seg.get("Concept", "")
            if c_name:
                c_start = parse_timestamp_to_seconds(seg.get("ConceptStart", "00:00"))
                c_end = parse_timestamp_to_seconds(seg.get("ConceptEnd", "99:99:99"))
                if c_name not in concept_time_ranges:
                    concept_time_ranges[c_name] = []
                concept_time_ranges[c_name].append((c_start, c_end))

        # Extract per-concept student pause & interaction telemetry
        concept_telemetry_map: Dict[str, Dict[str, Any]] = {}
        for ev in student_events:
            e_type = ev.get("EventType", "")
            e_ts = str(ev.get("EventTimestamp", "00:00"))
            e_sec = parse_timestamp_to_seconds(e_ts)

            for c_name, ranges in concept_time_ranges.items():
                for (c_start, c_end) in ranges:
                    if c_start <= e_sec <= c_end:
                        if c_name not in concept_telemetry_map:
                            concept_telemetry_map[c_name] = {"pause_count": 0, "timestamps": []}
                        if e_type in ["PAUSE", "SEEK_BACKWARD", "REPLAY", "UNDERSTAND_PAUSE"]:
                            concept_telemetry_map[c_name]["pause_count"] += 1
                            concept_telemetry_map[c_name]["timestamps"].append(e_ts)

        concept_gen_counts: Dict[str, int] = {}  # track dynamic questions generated

        for p in priorities:
            needed_count = quiz_settings.PRIORITY_QUESTION_COUNTS.get(p.priority.value, 0)
            if needed_count <= 0:
                continue

            target_diff = cls._priority_to_target_difficulty(p.priority)
            concept_telemetry = concept_telemetry_map.get(p.concept_name, {"pause_count": 0, "timestamps": []})
            p_pause_count = concept_telemetry["pause_count"]
            p_pause_timestamps = concept_telemetry["timestamps"]

            # Count available unseen questions for this student
            unseen_query: Dict[str, Any] = {
                "course_id": str(course_id),
                "concept_name": {"$regex": f"^{re.escape(p.concept_name)}$", "$options": "i"}
            }
            if recently_seen_ids:
                from bson import ObjectId
                valid_ids = [ObjectId(qid) for qid in recently_seen_ids if ObjectId.is_valid(qid)]
                if valid_ids:
                    unseen_query["_id"] = {"$nin": valid_ids}

            unseen_count = await database.questions.count_documents(unseen_query)

            # Generate fresh questions if unseen questions are low OR student has active telemetry on this concept
            should_generate = (unseen_count < needed_count) or (p_pause_count > 0) or (p.priority.value == "HIGH")

            if should_generate:
                generate_count = max(needed_count - unseen_count, 1)
                logger.info(
                    "[DYNAMIC GENERATION] Student=%s Concept='%s' (priority=%s, pauses=%d, unseen=%d/%d). "
                    "Generating %d fresh dynamic questions tailored to interaction data.",
                    clean_student, p.concept_name, p.priority.value, p_pause_count, unseen_count, needed_count,
                    generate_count
                )

                try:
                    await QuestionService.generate_and_store_questions(
                        course_id=course_id,
                        concept_identifier=p.concept_name,
                        count=needed_count,
                        target_difficulty=target_diff,
                        course_name=course_name,
                        pause_count=p_pause_count,
                        pause_timestamps=p_pause_timestamps,
                        quiz_priority=p.priority.value,
                        confidence=p.score
                    )
                    concept_gen_counts[p.concept_name] = needed_count
                except ValueError as gen_err:
                    logger.warning(
                        "[DYNAMIC GENERATION] Could not generate questions for concept '%s': %s",
                        p.concept_name, str(gen_err)
                    )
                    concept_gen_counts[p.concept_name] = 0
                except Exception as gen_err:
                    logger.error(
                        "[DYNAMIC GENERATION] Unexpected error generating questions for '%s': %s",
                        p.concept_name, str(gen_err)
                    )
                    concept_gen_counts[p.concept_name] = 0
            else:
                concept_gen_counts[p.concept_name] = 0

        # ── Step 5: Question Bank — Retrieve questions (includes freshly generated) ──
        quiz_questions: List[InternalQuizQuestion] = []
        used_question_ids = []

        for p in priorities:
            count = quiz_settings.PRIORITY_QUESTION_COUNTS.get(p.priority.value, 0)
            if count <= 0:
                continue

            target_diff = cls._priority_to_target_difficulty(p.priority)

            fetched = await QuestionBankAdapter.get_questions(
                course_id=course_id,
                concept_id=p.concept_id,
                difficulty=target_diff,
                count=count,
                excluded_ids=used_question_ids,
                student_id=clean_student
            )
            for q in fetched[:count]:
                quiz_questions.append(q)
                used_question_ids.append(q.question_id)

        # Fallback to any course questions if prioritized concept match returned 0
        if not quiz_questions:
            all_course_questions = await database.questions.find({"course_id": str(course_id)}).to_list(length=20)
            for doc in all_course_questions:
                q_id = str(doc["_id"])
                if q_id not in used_question_ids:
                    quiz_questions.append(
                        InternalQuizQuestion(
                            question_id=q_id,
                            concept_id=doc.get("concept_ref", f"{course_id}:{doc.get('concept_name', 'General')}"),
                            concept_name=doc.get("concept_name", "General Concept"),
                            question_text=doc.get("question", ""),
                            options=doc.get("options", []),
                            correct_answer=doc.get("correct_answer", ""),
                            difficulty=doc.get("difficulty", "MEDIUM"),
                            explanation=doc.get("explanation", "")
                        )
                    )
                    used_question_ids.append(q_id)
                    if len(quiz_questions) >= 5:
                        break

        actual_total = len(quiz_questions)

        if not quiz_questions:
            raise ValueError(
                "No questions are currently available for this course. "
                "Please ensure the teacher has generated the transcript and concepts first."
            )

        # ── Step 6: Build Concept Map Nodes ──
        concept_map_nodes: List[ConceptMapNode] = []
        total_dyn_generated = 0

        for p in priorities:
            q_count_for_concept = sum(
                1 for q in quiz_questions if q.concept_name == p.concept_name
            )
            dyn_count = concept_gen_counts.get(p.concept_name, 0)
            total_dyn_generated += dyn_count

            node = ConceptMapNode(
                concept_id=p.concept_id,
                concept_name=p.concept_name,
                priority=p.priority.value,
                priority_score=p.score,
                difficulty_level=difficulty_level_map.get(p.concept_name, "Easy"),
                difficulty_score=difficulty_score_map.get(p.concept_name, 0.0),
                question_count=q_count_for_concept,
                dynamically_generated=dyn_count,
                prerequisite=prerequisite_map.get(p.concept_name, None),
                interaction_metrics=features_by_concept.get(p.concept_name, None)
            )
            concept_map_nodes.append(node)

        high_count = sum(1 for n in concept_map_nodes if n.priority == "HIGH")
        medium_count = sum(1 for n in concept_map_nodes if n.priority == "MEDIUM")
        low_count = sum(1 for n in concept_map_nodes if n.priority == "LOW")

        concept_map = ConceptMapData(
            nodes=concept_map_nodes,
            total_concepts=len(concept_map_nodes),
            high_priority_count=high_count,
            medium_priority_count=medium_count,
            low_priority_count=low_count,
            dynamically_generated_total=total_dyn_generated
        )

        # ── Step 7: Initialize persistent Session ──
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        session_doc = {
            "quiz_session_id": session_id,
            "quiz_type": "full_adaptive",
            "student_id": clean_student,
            "course_id": str(course_id),
            "course_name": course_name,
            "status": "active",
            "started_at": now,
            "completed_at": None,
            "total_questions": actual_total,
            "answered_questions": 0,
            "correct_count": 0,
            "wrong_count": 0,
            "score": 0.0,
            "concept_priorities": [p.model_dump() for p in priorities],
            "concept_map": concept_map.model_dump(),
            "questions": [q.model_dump() for q in quiz_questions],
            "history": []
        }

        await QuizSessionRepository.create_session(session_doc)

        # ── Step 8: Format Safe Questions (with difficulty) ──
        safe_items = []
        for q in quiz_questions:
            safe_items.append(
                AdaptiveQuizQuestionItem(
                    question_id=q.question_id,
                    question=q.question_text,
                    options=q.options,
                    concept=q.concept_name,
                    difficulty=q.difficulty
                )
            )

        logger.info(
            "[ADAPTIVE QUIZ] Quiz ready: %d questions, %d concepts, %d dynamically generated",
            actual_total, len(concept_map_nodes), total_dyn_generated
        )

        return AdaptiveQuizResponse(
            quiz_session_id=session_id,
            course_id=str(course_id),
            course_name=course_name,
            total_questions=actual_total,
            questions=safe_items,
            concept_map=concept_map
        )

    @classmethod
    async def submit_full_adaptive_quiz(
        cls,
        student_id: str,
        course_id: str,
        submission: BulkSubmitRequest
    ) -> BulkSubmitResponse:
        """
        Validate and score all answers submitted at once.
        """
        clean_student = student_id.strip().upper()
        session = await QuizSessionRepository.get_session(submission.quiz_session_id, clean_student)

        if not session:
            raise ValueError("Quiz session not found or access denied.")
            
        if session.get("course_id") != course_id:
            raise ValueError("Quiz session does not match course ID.")

        if session.get("status") != "active":
            raise ValueError("Quiz already submitted.")

        questions = session.get("questions", [])
        total_questions = len(questions)

        q_dict = {q["question_id"]: q for q in questions}
        
        correct_count = 0
        wrong_count = 0
        results = []
        concept_stats = {}

        # Evaluate
        for ans_item in submission.answers:
            q_id = ans_item.question_id
            selected = ans_item.selected_answer.strip()
            
            target_q = q_dict.get(q_id)
            if not target_q:
                continue

            c_name = target_q.get("concept_name", "General Concept")
            if c_name not in concept_stats:
                concept_stats[c_name] = {"total": 0, "correct": 0, "wrong": 0}

            correct_ans = target_q.get("correct_answer", "").strip()
            is_correct = (selected.lower() == correct_ans.lower())
            
            concept_stats[c_name]["total"] += 1

            if is_correct:
                correct_count += 1
                concept_stats[c_name]["correct"] += 1
            else:
                wrong_count += 1
                concept_stats[c_name]["wrong"] += 1
                
            explanation_text, _ = await ExplanationService.generate_explanation(
                question_text=target_q.get("question_text", ""),
                student_answer=selected,
                correct_answer=correct_ans,
                concept_name=c_name,
                is_correct=is_correct,
                existing_explanation=target_q.get("explanation")
            )

            # Retrieve video timestamp and revision resource matching transcript
            rev_res = await LearningResourceService.get_revision_resource(
                course_id=course_id,
                concept_id=target_q.get("concept_id"),
                concept_name=c_name,
                question_text=target_q.get("question_text", ""),
                correct_answer=correct_ans,
                explanation=explanation_text or target_q.get("explanation")
            )

            ts_sec = rev_res.timestamp_seconds if rev_res else None
            ts_disp = rev_res.timestamp_display if rev_res else None
            tx_excerpt = rev_res.transcript_excerpt if rev_res else None
            vid_url = rev_res.video_url if rev_res else None
            rev_url = rev_res.revision_url if rev_res else None

            # Update Closed-Loop Concept State
            from app.services.student_state_service import StudentConceptStateService
            await StudentConceptStateService.record_quiz_answer_outcome(
                student_id=clean_student,
                course_id=course_id,
                concept_name=c_name,
                is_correct=is_correct,
                question_id=q_id,
                difficulty=target_q.get("difficulty", "MEDIUM")
            )

            results.append(
                QuestionResult(
                    question_id=q_id,
                    question=target_q.get("question_text", ""),
                    options=target_q.get("options", []),
                    selected_answer=selected,
                    correct_answer=correct_ans,
                    is_correct=is_correct,
                    concept=c_name,
                    explanation=explanation_text or target_q.get("explanation"),
                    timestamp_seconds=ts_sec,
                    timestamp_display=ts_disp,
                    transcript_excerpt=tx_excerpt,
                    video_url=vid_url,
                    revision_url=rev_url
                )
            )

        score_pct = round((correct_count / total_questions * 100.0), 2) if total_questions > 0 else 0.0

        # Construct ConceptPerformance
        concept_perf_list = []
        for c_name, stats in concept_stats.items():
            tot = stats["total"]
            corr = stats["correct"]
            c_acc = round((corr / tot * 100.0), 2) if tot > 0 else 0.0
            concept_perf_list.append(
                ConceptPerformance(
                    concept=c_name,
                    total_questions=tot,
                    correct=corr,
                    wrong=stats["wrong"],
                    accuracy_percentage=c_acc
                )
            )

        # Update Session
        now = datetime.now(timezone.utc)
        await QuizSessionRepository.update_session(
            quiz_session_id=submission.quiz_session_id,
            student_id=clean_student,
            update_dict={
                "status": "completed",
                "completed_at": now,
                "answered_questions": len(submission.answers),
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "score": score_pct
            }
        )

        return BulkSubmitResponse(
            quiz_session_id=submission.quiz_session_id,
            course_id=course_id,
            course_name=session.get("course_name", ""),
            total_questions=total_questions,
            correct_count=correct_count,
            wrong_count=wrong_count,
            score_percentage=score_pct,
            results=results,
            concept_performance=concept_perf_list
        )
