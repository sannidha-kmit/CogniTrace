import re
import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.db.mongodb import get_database
from app.schemas.quiz import ConceptFeatureData
from app.services.mapping_service import MappingService, parse_timestamp_to_seconds

logger = logging.getLogger("cognitrace.quiz.feature_service")


def normalize_pause_reason(reason: Any) -> Optional[str]:
    """
    Normalize pause reason to 'study' or 'other_work'.
    Only 'study' maps to study_pause_count.
    Only 'other_work' maps to other_work_pause_count.
    Unknown / default / unrecognized pause reasons must NOT automatically be treated as study.
    """
    if not reason:
        return None
    r = str(reason).strip().lower()
    if r == "study":
        return "study"
    if r == "other_work":
        return "other_work"
    return None


class FeatureServiceAdapter:
    """
    Feature Service Adapter.
    Aggregates live student telemetry directly from MongoDB interaction_events into the
    exact six concept-level features required by the finalized Adaptive Quiz ML model:
    [backward_count, replay_count, study_pause_count, other_work_pause_count, forward_count, speed_increase_count]
    No CSV files required at runtime.
    """

    @classmethod
    async def get_concept_features(
        cls,
        student_id: str,
        course_id: str
    ) -> List[ConceptFeatureData]:
        """
        Retrieve concept-wise features for a given student and course from MongoDB.
        Performs:
        1. Retrieves course concepts from concept_segments.
        2. Retrieves student's telemetry events from interaction_events.
        3. Maps events to concepts by event timestamp.
        4. Calculates the six ML features per concept.
        """
        database = await get_database()
        clean_student = student_id.strip().upper()
        str_course_id = str(course_id)

        logger.info("[FEATURE ADAPTER] Aggregating concept features for Student=%s, Course=%s", clean_student, str_course_id)

        # 1. Retrieve course document
        course_doc = None
        if ObjectId.is_valid(str_course_id):
            course_doc = await database.courses.find_one({"_id": ObjectId(str_course_id)})
        if not course_doc:
            course_doc = await database.courses.find_one({"_id": str_course_id})

        course_name = course_doc.get("course_name", "") if course_doc else ""

        # 2. Retrieve concept segments (auto-extract if completed transcript exists)
        concept_doc = await database.concept_segments.find_one({"course_id": str_course_id})
        if not concept_doc or concept_doc.get("status") != "COMPLETED":
            tx_doc = await database.course_transcripts.find_one({"course_id": str_course_id})
            if tx_doc and tx_doc.get("status") == "COMPLETED" and tx_doc.get("segments"):
                from app.services.concept_service import ConceptService
                from datetime import datetime, timezone
                subj = course_doc.get("subject", "") if course_doc else ""
                cname = course_name or tx_doc.get("course_name", "")
                t_id = course_doc.get("teacher_id", "") if course_doc else ""
                t_name = course_doc.get("teacher_name", "") if course_doc else ""
                extracted = ConceptService.extract_concepts_from_transcript(
                    tx_doc["segments"],
                    subject_name=subj,
                    course_name=cname
                )
                if extracted:
                    now = datetime.now(timezone.utc)
                    await database.concept_segments.update_one(
                        {"course_id": str_course_id},
                        {
                            "$set": {
                                "course_id": str_course_id,
                                "CourseSubject": subj,
                                "CourseName": cname,
                                "teacher_id": t_id,
                                "teacher_name": t_name,
                                "status": "COMPLETED",
                                "segments": extracted,
                                "error_message": None,
                                "created_at": now,
                                "updated_at": now
                            }
                        },
                        upsert=True
                    )
                    concept_doc = await database.concept_segments.find_one({"course_id": str_course_id})

        concept_items = concept_doc.get("segments", []) if (concept_doc and concept_doc.get("status") == "COMPLETED") else []

        # 3. Retrieve student interaction events from MongoDB
        event_query: Dict[str, Any] = {
            "StudentID": {"$regex": f"^{re.escape(clean_student)}$", "$options": "i"},
            "$or": [
                {"CourseID": str_course_id}
            ]
        }
        if course_name:
            event_query["$or"].append({"CourseName": course_name})

        events_cursor = database.interaction_events.find(event_query).sort("created_at", 1)
        events = await events_cursor.to_list(length=1000)

        logger.info("[FEATURE ADAPTER] Found %d interaction events for Student=%s in Course=%s", len(events), clean_student, str_course_id)

        # 4. Map events to concepts
        concept_events_map: Dict[str, List[Dict[str, Any]]] = {}

        # Initialize all known concepts
        for item in concept_items:
            c_name = item.get("Concept", "").strip()
            if c_name and c_name not in concept_events_map:
                concept_events_map[c_name] = []

        # Also discover any distinct concepts from questions collection
        question_concepts = await database.questions.distinct("concept_name", {"course_id": str_course_id})
        for qc in question_concepts:
            if qc and qc not in concept_events_map:
                concept_events_map[qc] = []

        # Map each event to its matching concept
        for ev in events:
            ts_str = str(ev.get("EventTimestamp", "00:00"))
            ts_sec = parse_timestamp_to_seconds(ts_str)

            if concept_items:
                matched = MappingService.find_matching_concept_segment(concept_items, ts_sec)
                c_name = matched.get("Concept", "Core Concepts")
            else:
                c_name = ev.get("Concept") or "Core Concepts"

            if c_name not in concept_events_map:
                concept_events_map[c_name] = []
            concept_events_map[c_name].append(ev)

        # Fallback if no concepts found at all
        if not concept_events_map:
            concept_events_map["Core Concepts"] = events

        # 5. Aggregate the exact 6 features per concept
        concept_features_list: List[ConceptFeatureData] = []

        for c_name, ev_list in concept_events_map.items():
            backward_count = 0.0
            replay_count = 0.0
            study_pause_count = 0.0
            other_work_pause_count = 0.0
            forward_count = 0.0
            speed_increase_count = 0.0

            for ev in ev_list:
                e_type = str(ev.get("EventType", "")).upper()

                if e_type == "SEEK_BACKWARD":
                    backward_count += 1.0
                elif e_type == "REPLAY":
                    replay_count += 1.0
                elif e_type == "PAUSE":
                    norm_reason = normalize_pause_reason(ev.get("PauseReason"))
                    if norm_reason == "study":
                        study_pause_count += 1.0
                    elif norm_reason == "other_work":
                        other_work_pause_count += 1.0
                elif e_type == "SEEK_FORWARD":
                    forward_count += 1.0
                elif e_type == "SPEED_CHANGE":
                    speed_val = ev.get("PlaybackSpeed")
                    try:
                        if speed_val is not None and float(speed_val) > 1.0:
                            speed_increase_count += 1.0
                    except (ValueError, TypeError):
                        pass

            features_dict = {
                "backward_count": backward_count,
                "replay_count": replay_count,
                "study_pause_count": study_pause_count,
                "other_work_pause_count": other_work_pause_count,
                "forward_count": forward_count,
                "speed_increase_count": speed_increase_count
            }

            concept_id = f"{str_course_id}:{c_name}"
            concept_features_list.append(
                ConceptFeatureData(
                    concept_id=concept_id,
                    concept_name=c_name,
                    features=features_dict
                )
            )

        logger.info("[FEATURE ADAPTER] Computed 6 features for %d concepts for Student=%s", len(concept_features_list), clean_student)
        return concept_features_list
