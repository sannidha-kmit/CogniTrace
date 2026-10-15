import re
import random
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
    Supports randomized sampling and avoids recently answered questions for student variety.
    """

    @classmethod
    async def get_questions(
        cls,
        course_id: str,
        concept_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        count: int = 3,
        excluded_ids: Optional[List[str]] = None,
        student_id: Optional[str] = None
    ) -> List[InternalQuizQuestion]:
        """
        Fetch questions from Member 2 Question Bank for the specified course and concept.
        Excludes already selected question IDs to prevent duplicate questions in the same quiz.
        Uses randomized candidate sampling to ensure fresh quiz experiences.
        """
        database = await get_database()
        clean_course_id = str(course_id)
        excluded_set = set(excluded_ids or [])

        # If student_id is provided, find previously answered questions by this student to prioritize fresh ones
        recently_seen_ids = set()
        if student_id:
            try:
                past_sessions = await database.quiz_sessions.find({
                    "student_id": student_id.strip().upper(),
                    "course_id": clean_course_id
                }).sort("started_at", -1).limit(10).to_list(length=10)
                for ps in past_sessions:
                    for q in ps.get("questions", []):
                        if q.get("question_id"):
                            recently_seen_ids.add(q["question_id"])
            except Exception as e:
                logger.debug("Could not fetch past session questions: %s", e)

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

        raw_cursor = database.questions.find(query)
        raw_questions = await raw_cursor.to_list(length=300)

        # Shuffle candidates to ensure variety
        random.shuffle(raw_questions)

        # Sort so fresh (unseen by student) questions strictly come first
        raw_questions.sort(key=lambda d: 1 if str(d["_id"]) in recently_seen_ids else 0)

        selected: List[InternalQuizQuestion] = []

        from app.services.claude_service import is_valid_conceptual_question
        from app.schemas.question import GeneratedMCQ

        for doc in raw_questions:
            q_id = str(doc["_id"])
            if q_id in excluded_set:
                continue

            try:
                mcq_check = GeneratedMCQ(
                    question=doc.get("question", ""),
                    options=doc.get("options", []),
                    correct_answer=doc.get("correct_answer", ""),
                    difficulty=doc.get("difficulty", "MEDIUM"),
                    explanation=doc.get("explanation", "Conceptual question explanation."),
                    concept=doc.get("concept_name", concept_filter_name or "General Concept")
                )
                if not is_valid_conceptual_question(mcq_check):
                    continue
            except Exception:
                continue

            selected.append(
                InternalQuizQuestion(
                    question_id=q_id,
                    concept_id=doc.get("concept_ref", f"{clean_course_id}:{doc.get('concept_name', 'General')}"),
                    concept_name=doc.get("concept_name", concept_filter_name or "General Concept"),
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

        # 2. Fallback query across other difficulties if not enough questions found for this concept
        if len(selected) < count and concept_filter_name:
            fallback_query: Dict[str, Any] = {
                "course_id": clean_course_id,
                "$or": [
                    {"concept_ref": concept_id},
                    {"concept_name": {"$regex": f"^{re.escape(concept_filter_name)}$", "$options": "i"}},
                    {"concept_name": {"$regex": re.escape(concept_filter_name), "$options": "i"}}
                ]
            }
            fallback_cursor = database.questions.find(fallback_query)
            fallback_questions = await fallback_cursor.to_list(length=300)
            random.shuffle(fallback_questions)
            fallback_questions.sort(key=lambda d: 1 if str(d["_id"]) in recently_seen_ids else 0)

            for doc in fallback_questions:
                q_id = str(doc["_id"])
                if q_id in excluded_set:
                    continue

                try:
                    mcq_check = GeneratedMCQ(
                        question=doc.get("question", ""),
                        options=doc.get("options", []),
                        correct_answer=doc.get("correct_answer", ""),
                        difficulty=doc.get("difficulty", "MEDIUM"),
                        explanation=doc.get("explanation", "Conceptual question explanation."),
                        concept=doc.get("concept_name", concept_filter_name or "General Concept")
                    )
                    if not is_valid_conceptual_question(mcq_check):
                        continue
                except Exception:
                    continue

                selected.append(
                    InternalQuizQuestion(
                        question_id=q_id,
                        concept_id=doc.get("concept_ref", f"{clean_course_id}:{doc.get('concept_name', 'General')}"),
                        concept_name=doc.get("concept_name", concept_filter_name or "General Concept"),
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

        # 3. Final fallback across any course questions only if no concept was specified or absolutely no concept questions exist
        if len(selected) < count and not concept_filter_name:
            any_cursor = database.questions.find({"course_id": clean_course_id})
            any_questions = await any_cursor.to_list(length=200)
            random.shuffle(any_questions)
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
