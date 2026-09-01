import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId

from app.core.quiz_config import quiz_settings
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
    RevisionResource
)
from app.services.adapters.feature_service_adapter import FeatureServiceAdapter
from app.services.adapters.ml_inference_service import ml_service
from app.services.adapters.question_bank_adapter import QuestionBankAdapter
from app.services.explanation_service import ExplanationService
from app.services.learning_resource_service import LearningResourceService
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
            concept_name=concept_name
        )

        learning_support = LearningSupport(
            concept_id=concept_id,
            concept_name=concept_name,
            explanation=explanation_text,
            explanation_status=explanation_status,
            revision=revision_resource
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
