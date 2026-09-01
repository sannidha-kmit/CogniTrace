import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.db.mongodb import get_database
from app.schemas.quiz import ConceptFeatureData

logger = logging.getLogger("cognitrace.quiz.feature_service")


class FeatureServiceAdapter:
    """
    Member 5 Feature Service Adapter.
    Consumes student telemetry & concept-wise interaction features without duplicating aggregation logic.
    """

    @classmethod
    async def get_concept_features(
        cls,
        student_id: str,
        course_id: str
    ) -> List[ConceptFeatureData]:
        """
        Retrieve concept-wise features for a given student and course.
        Maps existing Phase 8 difficulty/interaction features into structured feature objects.
        """
        database = await get_database()
        clean_student = student_id.strip().upper()

        logger.info("[MEMBER 5 ADAPTER] Fetching concept features for Student=%s, Course=%s", clean_student, course_id)

        # 1. First look up pre-aggregated Phase 8 difficulty collection
        diff_cursor = database.difficulty.find({
            "StudentID": clean_student,
            "CourseID": str(course_id)
        })
        diff_records = await diff_cursor.to_list(length=500)

        concept_features_map: Dict[str, ConceptFeatureData] = {}

        for rec in diff_records:
            c_name = rec.get("Concept", "General")
            c_id = f"{course_id}:{c_name}"
            features = {
                "replay_count": float(rec.get("ReplayCount", 0)),
                "pause_count": float(rec.get("PauseCount", 0)),
                "seek_backward_count": float(rec.get("SeekBackwardCount", 0)),
                "seek_forward_count": float(rec.get("SeekForwardCount", 0)),
                "understand_pause_count": float(rec.get("UnderstandPauseCount", 0)),
                "difficulty_score": float(rec.get("DifficultyScore", 0.0))
            }
            concept_features_map[c_name] = ConceptFeatureData(
                concept_id=c_id,
                concept_name=c_name,
                features=features
            )

        # 2. Discover all course concepts from concept_segments / questions if any concepts have 0 interactions
        concept_doc = await database.concept_segments.find_one({"course_id": str(course_id)})
        all_concepts: List[str] = []

        if concept_doc and "segments" in concept_doc:
            all_concepts = [s.get("Concept", "").strip() for s in concept_doc.get("segments", []) if s.get("Concept")]

        # Also check distinct concepts in questions collection for this course
        question_concepts = await database.questions.distinct("concept_name", {"course_id": str(course_id)})
        for qc in question_concepts:
            if qc and qc not in all_concepts:
                all_concepts.append(qc)

        # Populate neutral baseline features for concepts with no telemetry yet
        for c_name in all_concepts:
            if c_name not in concept_features_map:
                c_id = f"{course_id}:{c_name}"
                concept_features_map[c_name] = ConceptFeatureData(
                    concept_id=c_id,
                    concept_name=c_name,
                    features={
                        "replay_count": 0.0,
                        "pause_count": 0.0,
                        "seek_backward_count": 0.0,
                        "seek_forward_count": 0.0,
                        "understand_pause_count": 0.0,
                        "difficulty_score": 0.0
                    }
                )

        # Fallback if no concept segments exist in course at all: create generic concept
        if not concept_features_map:
            c_name = "Core Concepts"
            concept_features_map[c_name] = ConceptFeatureData(
                concept_id=f"{course_id}:{c_name}",
                concept_name=c_name,
                features={
                    "replay_count": 0.0,
                    "pause_count": 0.0,
                    "seek_backward_count": 0.0,
                    "seek_forward_count": 0.0,
                    "understand_pause_count": 0.0,
                    "difficulty_score": 0.0
                }
            )

        return list(concept_features_map.values())
