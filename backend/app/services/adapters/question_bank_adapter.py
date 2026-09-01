import re
import logging
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app.db.mongodb import get_database
from app.schemas.quiz import InternalQuizQuestion

logger = logging.getLogger("cognitrace.quiz.question_bank")


class QuestionBankAdapter:
    """
    Member 2 Question Bank Service Adapter.
    Retrieves questions from Question Bank with course_id, concept_id, difficulty, and count.
    Provides backend with internal question data (including correct_answer) for secure evaluation.
    """

    @classmethod
    async def get_questions(
        cls,
        course_id: str,
        concept_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        count: int = 3,
        excluded_ids: Optional[List[str]] = None
    ) -> List[InternalQuizQuestion]:
        """
        Fetch questions from Member 2 Question Bank for the specified course and concept.
        Excludes already selected question IDs to prevent duplicate questions in the same quiz.
        """
        database = await get_database()
        clean_course_id = str(course_id)
        excluded_set = set(excluded_ids or [])

        # Extract concept name from concept_ref or concept_id (e.g. course_id:ConceptName -> ConceptName)
        concept_filter_name = None
        if concept_id:
            if ":" in concept_id:
                concept_filter_name = concept_id.split(":", 1)[1]
            else:
                concept_filter_name = concept_id

        # 1. Primary query: match course_id + concept + difficulty
        query: Dict[str, Any] = {"course_id": clean_course_id}
        if concept_filter_name:
            query["$or"] = [
                {"concept_ref": concept_id},
                {"concept_name": {"$regex": f"^{re.escape(concept_filter_name)}$", "$options": "i"}},
                {"concept_name": {"$regex": re.escape(concept_filter_name), "$options": "i"}}
            ]
        if difficulty:
            query["difficulty"] = difficulty.upper().strip()

        cursor = database.questions.find(query).sort("created_at", -1)
        raw_questions = await cursor.to_list(length=100)

        selected: List[InternalQuizQuestion] = []

        for doc in raw_questions:
            q_id = str(doc["_id"])
            if q_id in excluded_set:
                continue

            selected.append(
                InternalQuizQuestion(
                    question_id=q_id,
                    concept_id=doc.get("concept_ref", f"{clean_course_id}:{doc.get('concept_name', 'General')}"),
                    concept_name=doc.get("concept_name", "General Concept"),
                    question_text=doc.get("question", ""),
                    options=doc.get("options", []),
                    correct_answer=doc.get("correct_answer", ""),
                    difficulty=doc.get("difficulty", "MEDIUM"),
                    explanation=doc.get("explanation", "")
                )
            )
            excluded_set.add(q_id)
            if len(selected) >= count:
                break

        # 2. Fallback query across other difficulties if not enough questions found
        if len(selected) < count:
            fallback_query: Dict[str, Any] = {"course_id": clean_course_id}
            if concept_filter_name:
                fallback_query["$or"] = [
                    {"concept_ref": concept_id},
                    {"concept_name": {"$regex": re.escape(concept_filter_name), "$options": "i"}}
                ]
            fallback_cursor = database.questions.find(fallback_query).sort("created_at", -1)
            fallback_questions = await fallback_cursor.to_list(length=100)

            for doc in fallback_questions:
                q_id = str(doc["_id"])
                if q_id in excluded_set:
                    continue

                selected.append(
                    InternalQuizQuestion(
                        question_id=q_id,
                        concept_id=doc.get("concept_ref", f"{clean_course_id}:{doc.get('concept_name', 'General')}"),
                        concept_name=doc.get("concept_name", "General Concept"),
                        question_text=doc.get("question", ""),
                        options=doc.get("options", []),
                        correct_answer=doc.get("correct_answer", ""),
                        difficulty=doc.get("difficulty", "MEDIUM"),
                        explanation=doc.get("explanation", "")
                    )
                )
                excluded_set.add(q_id)
                if len(selected) >= count:
                    break

        # 3. Final fallback across any course questions if concept has zero questions
        if len(selected) < count:
            any_cursor = database.questions.find({"course_id": clean_course_id}).sort("created_at", -1)
            any_questions = await any_cursor.to_list(length=100)
            for doc in any_questions:
                q_id = str(doc["_id"])
                if q_id in excluded_set:
                    continue

                selected.append(
                    InternalQuizQuestion(
                        question_id=q_id,
                        concept_id=doc.get("concept_ref", f"{clean_course_id}:{doc.get('concept_name', 'General')}"),
                        concept_name=doc.get("concept_name", "General Concept"),
                        question_text=doc.get("question", ""),
                        options=doc.get("options", []),
                        correct_answer=doc.get("correct_answer", ""),
                        difficulty=doc.get("difficulty", "MEDIUM"),
                        explanation=doc.get("explanation", "")
                    )
                )
                excluded_set.add(q_id)
                if len(selected) >= count:
                    break

        logger.info(
            "[MEMBER 2 QUESTION BANK] Retrieved %d questions for Course=%s, Concept=%s, Difficulty=%s",
            len(selected), clean_course_id, concept_id, difficulty
        )
        return selected
