import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.db.mongodb import get_database

logger = logging.getLogger("cognitrace.quiz.repository")


class QuizSessionRepository:
    """
    MongoDB Repository for Quiz Session persistence.
    Enforces StudentID + CourseID identity and ownership on every query.
    """

    @classmethod
    async def create_session(cls, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a new quiz session document into quiz_sessions collection."""
        database = await get_database()
        if "created_at" not in session_data:
            session_data["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in session_data:
            session_data["updated_at"] = datetime.now(timezone.utc)

        await database.quiz_sessions.insert_one(session_data)
        logger.info(
            "[QUIZ REPO] Created session '%s' for Student=%s, Course=%s",
            session_data["quiz_session_id"], session_data["student_id"], session_data["course_id"]
        )
        return session_data

    @classmethod
    async def get_session(
        cls,
        quiz_session_id: str,
        student_id: str,
        course_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Ownership-aware query for a quiz session.
        Matches quiz_session_id and verified student_id.
        """
        database = await get_database()
        query: Dict[str, Any] = {
            "quiz_session_id": quiz_session_id,
            "student_id": student_id.strip().upper()
        }
        if course_id:
            query["course_id"] = str(course_id)

        session = await database.quiz_sessions.find_one(query)
        return session

    @classmethod
    async def get_active_session_for_student_course(
        cls,
        student_id: str,
        course_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find any existing active session for student and course."""
        database = await get_database()
        query = {
            "student_id": student_id.strip().upper(),
            "course_id": str(course_id),
            "status": "active"
        }
        return await database.quiz_sessions.find_one(query)

    @classmethod
    async def update_session(
        cls,
        quiz_session_id: str,
        student_id: str,
        update_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Atomically update fields on an authorized quiz session."""
        database = await get_database()
        update_dict["updated_at"] = datetime.now(timezone.utc)

        updated = await database.quiz_sessions.find_one_and_update(
            {"quiz_session_id": quiz_session_id, "student_id": student_id.strip().upper()},
            {"$set": update_dict},
            return_document=True
        )
        return updated

    @classmethod
    async def record_answer_submission(
        cls,
        quiz_session_id: str,
        student_id: str,
        question_id: str,
        selected_option: str,
        is_correct: bool,
        current_difficulty: str,
        next_difficulty: str,
        answered_questions: int,
        correct_count: int,
        wrong_count: int,
        current_score: float,
        is_completed: bool = False,
        learning_support: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically update the specific question inside session.questions,
        append to answer history with learning support details, and update session counters.
        """
        database = await get_database()
        now = datetime.now(timezone.utc)

        history_item = {
            "question_id": question_id,
            "selected_option": selected_option,
            "is_correct": is_correct,
            "difficulty": current_difficulty,
            "answered_at": now,
            "learning_support": learning_support
        }

        update_payload: Dict[str, Any] = {
            "$set": {
                "questions.$[elem].answered": True,
                "questions.$[elem].selected_option": selected_option,
                "questions.$[elem].is_correct": is_correct,
                "questions.$[elem].answered_at": now,
                "questions.$[elem].learning_support": learning_support,
                "current_difficulty": next_difficulty,
                "answered_questions": answered_questions,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "score": current_score,
                "current_question_index": answered_questions,
                "updated_at": now
            },
            "$push": {
                "history": history_item
            }
        }


        if is_completed:
            update_payload["$set"]["status"] = "completed"
            update_payload["$set"]["completed_at"] = now

        result = await database.quiz_sessions.find_one_and_update(
            {
                "quiz_session_id": quiz_session_id,
                "student_id": student_id.strip().upper(),
                "status": "active"
            },
            update_payload,
            array_filters=[{"elem.question_id": question_id}],
            return_document=True
        )
        return result

    @classmethod
    async def finish_session(
        cls,
        quiz_session_id: str,
        student_id: str,
        completed_at: datetime
    ) -> Optional[Dict[str, Any]]:
        """Mark session as completed."""
        database = await get_database()
        result = await database.quiz_sessions.find_one_and_update(
            {
                "quiz_session_id": quiz_session_id,
                "student_id": student_id.strip().upper(),
                "status": "active"
            },
            {
                "$set": {
                    "status": "completed",
                    "completed_at": completed_at,
                    "updated_at": completed_at
                }
            },
            return_document=True
        )
        return result
