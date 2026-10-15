import math
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId

from app.core.research_config import research_settings
from app.db.mongodb import get_database
from app.schemas.student_state import ConceptStateResponse, StudentCourseConceptStatesResponse
from app.services.evidence_engine import EvidenceEngine
from app.services.adapters.ml_inference_service import ml_service
from app.services.adapters.feature_service_adapter import FeatureServiceAdapter

logger = logging.getLogger("cognitrace.student_state_service")


class StudentConceptStateService:
    """
    Manages persistent concept-level student states: StudentID + CourseID + ConceptID.
    Combines behavioral evidence, assessment performance (interpretable mastery / BKT baseline),
    and ML prediction into an integrated research-grade priority score.
    """

    @classmethod
    def calculate_mastery_score(
        cls,
        correct_answers: int,
        total_attempts: int
    ) -> Tuple[Optional[float], bool, float]:
        """
        Extensible Mastery Calculation.
        Handles zero attempts safely (does NOT treat 0 attempts as 0% mastery).
        Returns (mastery_score, is_known, knowledge_gap).
        """
        if total_attempts <= 0:
            # 0 attempts -> unknown / neutral prior state
            prior = research_settings.default_prior_mastery
            return None, False, round(1.0 - prior, 4)

        score = float(correct_answers) / float(total_attempts)
        score = max(0.0, min(1.0, score))
        knowledge_gap = max(0.0, min(1.0, 1.0 - score))
        return round(score, 4), True, round(knowledge_gap, 4)

    @classmethod
    def determine_target_difficulty(cls, mastery_score: Optional[float]) -> str:
        """
        Adaptive Difficulty Mapping Policy:
        - Low mastery (< LOW_MASTERY_THRESHOLD): EASY
        - Medium mastery (between thresholds): MEDIUM
        - High mastery (> HIGH_MASTERY_THRESHOLD): HARD
        - Unknown mastery: MEDIUM
        """
        if mastery_score is None:
            return "MEDIUM"

        if mastery_score < research_settings.low_mastery_threshold:
            return "EASY"
        elif mastery_score > research_settings.high_mastery_threshold:
            return "HARD"
        else:
            return "MEDIUM"

    @classmethod
    def compute_combined_priority(
        cls,
        normalized_behavioral_evidence: float,
        knowledge_gap: float,
        ml_score: float
    ) -> Tuple[float, str]:
        """
        Compute integrated research priority:
        Priority = alpha * norm_behavioral + beta * knowledge_gap + gamma * ml_score
        Returns (priority_score, priority_label).
        """
        alpha = research_settings.alpha_behavioral
        beta = research_settings.beta_knowledge_gap
        gamma = research_settings.gamma_ml_priority

        priority_score = (
            (alpha * normalized_behavioral_evidence) +
            (beta * knowledge_gap) +
            (gamma * ml_score)
        )
        priority_score = round(max(0.0, min(1.0, priority_score)), 4)

        if priority_score >= 0.65:
            label = "HIGH"
        elif priority_score >= 0.35:
            label = "MEDIUM"
        else:
            label = "LOW"

        return priority_score, label

    @classmethod
    async def get_or_initialize_student_concept_state(
        cls,
        student_id: str,
        course_id: str,
        concept_id: str,
        concept_name: str
    ) -> Dict[str, Any]:
        """
        Retrieve existing concept state from MongoDB or initialize a fresh state.
        Maintains historical identity on StudentID + CourseID + ConceptID.
        """
        database = await get_database()
        clean_student = student_id.strip().upper()
        str_course_id = str(course_id)
        now = datetime.now(timezone.utc)

        state_doc = await database.student_concept_state.find_one({
            "student_id": clean_student,
            "course_id": str_course_id,
            "concept_id": concept_id
        })

        if not state_doc:
            state_doc = {
                "student_id": clean_student,
                "course_id": str_course_id,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "evidence_score": 0.0,
                "normalized_behavioral_evidence": 0.0,
                "interaction_evidence": {},
                "raw_event_counts": {},
                "quiz_attempts": 0,
                "correct_answers": 0,
                "incorrect_answers": 0,
                "mastery_score": None,
                "is_mastery_known": False,
                "knowledge_gap": 0.5,
                "recent_performance": [],
                "ml_priority": "MEDIUM",
                "ml_score": 0.5,
                "research_priority_score": 0.5,
                "final_priority_label": "MEDIUM",
                "target_difficulty": "MEDIUM",
                "created_at": now,
                "last_updated": now,
                "history": []
            }
            await database.student_concept_state.insert_one(state_doc)

        return state_doc

    @classmethod
    async def sync_and_get_all_concept_states(
        cls,
        student_id: str,
        course_id: str
    ) -> StudentCourseConceptStatesResponse:
        """
        Synchronize latest behavioral evidence, ML predictions, and quiz attempt history
        into the concept-level student state.
        """
        database = await get_database()
        clean_student = student_id.strip().upper()
        str_course_id = str(course_id)
        now = datetime.now(timezone.utc)

        # 1. Fetch Course details
        course_doc = None
        if ObjectId.is_valid(str_course_id):
            course_doc = await database.courses.find_one({"_id": ObjectId(str_course_id)})
        if not course_doc:
            course_doc = await database.courses.find_one({"_id": str_course_id})
        course_name = course_doc.get("course_name", "") if course_doc else ""

        # 2. Retrieve Evidence Summaries from EvidenceEngine
        evidence_summaries = await EvidenceEngine.process_and_aggregate_concept_evidence(
            student_id=clean_student,
            course_id=str_course_id,
            persist_records=False  # read/aggregate during sync
        )

        # 3. Retrieve ML Concept Features & Base ML Predictions
        concept_features_list = await FeatureServiceAdapter.get_concept_features(clean_student, str_course_id)
        ml_predictions: Dict[str, Tuple[str, float]] = {}
        for cf in concept_features_list:
            pred = ml_service.predict(cf.features)
            ml_predictions[cf.concept_name] = (pred.priority.value, pred.score)

        # 4. For each concept, update or create student_concept_state
        all_concepts = list(evidence_summaries.keys())
        for cf in concept_features_list:
            if cf.concept_name not in all_concepts:
                all_concepts.append(cf.concept_name)

        if not all_concepts:
            all_concepts = ["Core Concepts"]

        concept_responses: List[ConceptStateResponse] = []
        mastery_values = []
        total_ev_sum = 0.0

        for c_name in all_concepts:
            c_id = f"{str_course_id}:{c_name}"
            ev_summary = evidence_summaries.get(c_name)
            total_ev = ev_summary.total_evidence if ev_summary else 0.0
            norm_ev = ev_summary.normalized_evidence if ev_summary else 0.0
            ev_breakdown = ev_summary.weighted_breakdown if ev_summary else {}
            raw_counts = ev_summary.interaction_breakdown if ev_summary else {}

            total_ev_sum += total_ev

            ml_p_label, ml_p_score = ml_predictions.get(c_name, ("MEDIUM", 0.5))

            # Fetch current state from DB
            current_state = await cls.get_or_initialize_student_concept_state(
                student_id=clean_student,
                course_id=str_course_id,
                concept_id=c_id,
                concept_name=c_name
            )

            # Recalculate Mastery
            attempts = current_state.get("quiz_attempts", 0)
            correct = current_state.get("correct_answers", 0)
            incorrect = current_state.get("incorrect_answers", 0)
            mastery, is_known, gap = cls.calculate_mastery_score(correct, attempts)
            if is_known and mastery is not None:
                mastery_values.append(mastery)

            # Combined Priority Calculation
            priority_score, priority_label = cls.compute_combined_priority(
                normalized_behavioral_evidence=norm_ev,
                knowledge_gap=gap,
                ml_score=ml_p_score
            )

            # Target Difficulty
            target_diff = cls.determine_target_difficulty(mastery)

            # Update DB document
            update_fields = {
                "evidence_score": total_ev,
                "normalized_behavioral_evidence": norm_ev,
                "interaction_evidence": ev_breakdown,
                "raw_event_counts": raw_counts,
                "mastery_score": mastery,
                "is_mastery_known": is_known,
                "knowledge_gap": gap,
                "ml_priority": ml_p_label,
                "ml_score": ml_p_score,
                "research_priority_score": priority_score,
                "final_priority_label": priority_label,
                "target_difficulty": target_diff,
                "last_updated": now
            }

            await database.student_concept_state.update_one(
                {"student_id": clean_student, "course_id": str_course_id, "concept_id": c_id},
                {"$set": update_fields}
            )

            concept_responses.append(
                ConceptStateResponse(
                    student_id=clean_student,
                    course_id=str_course_id,
                    concept_id=c_id,
                    concept_name=c_name,
                    evidence_score=total_ev,
                    normalized_behavioral_evidence=norm_ev,
                    interaction_evidence=ev_breakdown,
                    raw_event_counts={k: int(v) for k, v in raw_counts.items()},
                    quiz_attempts=attempts,
                    correct_answers=correct,
                    incorrect_answers=incorrect,
                    mastery_score=mastery,
                    is_mastery_known=is_known,
                    knowledge_gap=gap,
                    recent_performance=current_state.get("recent_performance", []),
                    ml_priority=ml_p_label,
                    ml_score=ml_p_score,
                    research_priority_score=priority_score,
                    final_priority_label=priority_label,
                    target_difficulty=target_diff,
                    last_updated=now
                )
            )

        # Sort concepts by research priority score descending
        concept_responses.sort(key=lambda x: x.research_priority_score, reverse=True)

        avg_mastery = round(sum(mastery_values) / len(mastery_values), 4) if mastery_values else None

        return StudentCourseConceptStatesResponse(
            student_id=clean_student,
            course_id=str_course_id,
            course_name=course_name,
            concepts=concept_responses,
            overall_mastery_average=avg_mastery,
            total_evidence_sum=round(total_ev_sum, 4),
            last_updated=now
        )

    @classmethod
    async def record_quiz_answer_outcome(
        cls,
        student_id: str,
        course_id: str,
        concept_name: str,
        is_correct: bool,
        question_id: str,
        difficulty: str
    ) -> ConceptStateResponse:
        """
        Closed-Loop Update:
        Called immediately after student answers a question.
        Updates quiz attempts, correctness, recalculates mastery, knowledge gap, and priority.
        Maintains non-destructive trial history.
        """
        database = await get_database()
        clean_student = student_id.strip().upper()
        str_course_id = str(course_id)
        c_id = f"{str_course_id}:{concept_name}"
        now = datetime.now(timezone.utc)

        current_state = await cls.get_or_initialize_student_concept_state(
            student_id=clean_student,
            course_id=str_course_id,
            concept_id=c_id,
            concept_name=concept_name
        )

        attempts = current_state.get("quiz_attempts", 0) + 1
        correct = current_state.get("correct_answers", 0) + (1 if is_correct else 0)
        incorrect = current_state.get("incorrect_answers", 0) + (0 if is_correct else 1)

        recent_perf = current_state.get("recent_performance", []) + [is_correct]
        if len(recent_perf) > 10:
            recent_perf = recent_perf[-10:]

        mastery, is_known, gap = cls.calculate_mastery_score(correct, attempts)
        norm_ev = current_state.get("normalized_behavioral_evidence", 0.0)
        ml_score = current_state.get("ml_score", 0.5)

        priority_score, priority_label = cls.compute_combined_priority(
            normalized_behavioral_evidence=norm_ev,
            knowledge_gap=gap,
            ml_score=ml_score
        )
        target_diff = cls.determine_target_difficulty(mastery)

        trial_log = {
            "trial_number": attempts,
            "question_id": question_id,
            "difficulty": difficulty,
            "is_correct": is_correct,
            "updated_mastery": mastery,
            "timestamp": now
        }

        update_dict = {
            "quiz_attempts": attempts,
            "correct_answers": correct,
            "incorrect_answers": incorrect,
            "mastery_score": mastery,
            "is_mastery_known": is_known,
            "knowledge_gap": gap,
            "recent_performance": recent_perf,
            "research_priority_score": priority_score,
            "final_priority_label": priority_label,
            "target_difficulty": target_diff,
            "last_updated": now
        }

        await database.student_concept_state.update_one(
            {"student_id": clean_student, "course_id": str_course_id, "concept_id": c_id},
            {
                "$set": update_dict,
                "$push": {"history": trial_log}
            }
        )

        logger.info(
            "[CLOSED-LOOP STATE] Student=%s Concept='%s' Answered=%s -> New Mastery=%.2f, Priority=%.2f (%s), TargetDiff=%s",
            clean_student, concept_name, is_correct, mastery or 0.0, priority_score, priority_label, target_diff
        )

        return ConceptStateResponse(
            student_id=clean_student,
            course_id=str_course_id,
            concept_id=c_id,
            concept_name=concept_name,
            evidence_score=current_state.get("evidence_score", 0.0),
            normalized_behavioral_evidence=norm_ev,
            interaction_evidence=current_state.get("interaction_evidence", {}),
            raw_event_counts=current_state.get("raw_event_counts", {}),
            quiz_attempts=attempts,
            correct_answers=correct,
            incorrect_answers=incorrect,
            mastery_score=mastery,
            is_mastery_known=is_known,
            knowledge_gap=gap,
            recent_performance=recent_perf,
            ml_priority=current_state.get("ml_priority", "MEDIUM"),
            ml_score=ml_score,
            research_priority_score=priority_score,
            final_priority_label=priority_label,
            target_difficulty=target_diff,
            last_updated=now
        )
