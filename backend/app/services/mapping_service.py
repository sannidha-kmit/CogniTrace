import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("cognitrace.mapping_service")


def parse_timestamp_to_seconds(ts_val: Any) -> float:
    """
    Parse formatted timestamp string (e.g. '00:43', '01:15', '01:02:15') or numeric value into float seconds.
    """
    if ts_val is None:
        return 0.0
    if isinstance(ts_val, (int, float)):
        return float(ts_val)

    s_str = str(ts_val).strip()
    if not s_str:
        return 0.0

    # Remove 's' suffix if present (e.g., '43s')
    if s_str.endswith('s') or s_str.endswith('S'):
        s_str = s_str[:-1].strip()

    try:
        if ':' in s_str:
            parts = s_str.split(':')
            if len(parts) == 2:
                mins, secs = parts
                return float(mins) * 60.0 + float(secs)
            elif len(parts) == 3:
                hrs, mins, secs = parts
                return float(hrs) * 3600.0 + float(mins) * 60.0 + float(secs)
        return float(s_str)
    except Exception:
        logger.warning("Failed to parse timestamp string '%s', defaulting to 0.0s", ts_val)
        return 0.0


class MappingService:
    """
    CogniTrace Phase 7 Service.
    Connects student interaction telemetry events (Phase 5) to course transcripts (Phase 4)
    and course concept segments (Phase 6) based on event timestamps.
    """

    @staticmethod
    def find_matching_transcript_text(segments: List[Dict[str, Any]], event_secs: float) -> str:
        """
        Find matching transcript segment text using range: Start <= event_secs < End.
        """
        if not segments:
            return "Transcript segment unavailable."

        # Search for exact range match
        for seg in segments:
            start_sec = float(seg.get("start", 0.0))
            end_sec = float(seg.get("end", start_sec + 1.0))
            if start_sec <= event_secs < end_sec:
                return seg.get("text", "").strip()

        # Edge case: if event is beyond final segment, return last segment text
        sorted_segs = sorted(segments, key=lambda s: float(s.get("start", 0.0)))
        if event_secs >= float(sorted_segs[-1].get("start", 0.0)):
            return sorted_segs[-1].get("text", "").strip()

        # Edge case: if event is before first segment, return first segment text
        return sorted_segs[0].get("text", "").strip()

    @staticmethod
    def find_matching_concept_segment(concept_items: List[Dict[str, Any]], event_secs: float) -> Dict[str, str]:
        """
        Find matching concept segment using boundary rule: ConceptStart <= event_secs < ConceptEnd.
        """
        if not concept_items:
            return {
                "Concept": "Uncategorized Concept",
                "Prerequisite": "None"
            }

        sorted_concepts = sorted(
            concept_items,
            key=lambda c: parse_timestamp_to_seconds(c.get("ConceptStart", 0))
        )

        for item in sorted_concepts:
            c_start = parse_timestamp_to_seconds(item.get("ConceptStart", 0))
            c_end = parse_timestamp_to_seconds(item.get("ConceptEnd", c_start + 1.0))
            
            # Boundary Rule: Start <= EventTimestamp < End
            if c_start <= event_secs < c_end:
                return {
                    "Concept": item.get("Concept", "Uncategorized Concept"),
                    "Prerequisite": item.get("Prerequisite", "None")
                }

        # Edge case: if event timestamp exceeds last concept range
        if event_secs >= parse_timestamp_to_seconds(sorted_concepts[-1].get("ConceptStart", 0)):
            return {
                "Concept": sorted_concepts[-1].get("Concept", "Uncategorized Concept"),
                "Prerequisite": sorted_concepts[-1].get("Prerequisite", "None")
            }

        return {
            "Concept": sorted_concepts[0].get("Concept", "Uncategorized Concept"),
            "Prerequisite": sorted_concepts[0].get("Prerequisite", "None")
        }

    @classmethod
    async def map_events_to_concepts(
        cls,
        database: Any,
        roll_number: str,
        teacher_subject: str,
        teacher_course_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Process and generate concept-event mappings for a student's interaction events.
        Idempotent: updates existing mapping documents without creating duplicates.
        Propagates CourseID for unambiguous course identification.
        """
        clean_roll = roll_number.strip().upper()

        # 1. Query REAL interaction telemetry events for student
        query = {
            "StudentID": clean_roll,
            "CourseSubject": teacher_subject,
            "CourseName": {"$in": teacher_course_names}
        }
        events_cursor = database.interaction_events.find(query).sort("created_at", 1)
        events = await events_cursor.to_list(length=1000)

        if not events:
            return []

        mapped_records = []
        now = datetime.now(timezone.utc)

        for ev in events:
            c_name = ev.get("CourseName")
            c_subject = ev.get("CourseSubject", teacher_subject)
            ts_str = str(ev.get("EventTimestamp", "00:00"))
            event_type = ev.get("EventType", "PAUSE")
            event_secs = parse_timestamp_to_seconds(ts_str)

            # 2. Get course document (by CourseID if present, otherwise by course_name + subject)
            course = None
            ev_course_id = ev.get("CourseID")
            if ev_course_id:
                try:
                    from bson import ObjectId
                    course = await database.courses.find_one({"_id": ObjectId(ev_course_id)})
                except Exception:
                    pass
            
            if not course:
                course = await database.courses.find_one({
                    "course_name": c_name,
                    "subject": c_subject
                })

            if not course:
                logger.warning("Course '%s' not found for event mapping", c_name)
                continue

            course_id_str = str(course["_id"])

            # 3. Retrieve Course Transcript (Phase 4)
            tx_doc = await database.course_transcripts.find_one({"course_id": course_id_str})
            tx_segments = tx_doc.get("segments", []) if (tx_doc and tx_doc.get("status") == "COMPLETED") else []
            matched_transcript_text = cls.find_matching_transcript_text(tx_segments, event_secs)

            # 4. Retrieve Course Concepts (Phase 6)
            concept_doc = await database.concept_segments.find_one({"course_id": course_id_str})
            concept_items = concept_doc.get("segments", []) if (concept_doc and concept_doc.get("status") == "COMPLETED") else []
            matched_concept_data = cls.find_matching_concept_segment(concept_items, event_secs)

            # 5. Assemble exact dataset record with CourseID
            mapping_data = {
                "StudentID": ev.get("StudentID", clean_roll),
                "StudentName": ev.get("StudentName", "Student"),
                "CourseID": course_id_str,
                "CourseSubject": c_subject,
                "CourseName": c_name,
                "EventType": event_type,
                "EventTimestamp": ts_str,
                "Transcript": matched_transcript_text,
                "Concept": matched_concept_data["Concept"],
                "Prerequisite": matched_concept_data["Prerequisite"],
                "updated_at": now
            }

            # 6. Idempotent Upsert into concept_event_mappings collection
            match_filter = {
                "StudentID": mapping_data["StudentID"],
                "CourseID": course_id_str,
                "EventType": mapping_data["EventType"],
                "EventTimestamp": mapping_data["EventTimestamp"]
            }

            result = await database.concept_event_mappings.find_one_and_update(
                match_filter,
                {"$set": mapping_data, "$setOnInsert": {"created_at": now}},
                upsert=True,
                return_document=True
            )

            # Clean output dictionary
            output_item = {
                "id": str(result["_id"]),
                "StudentID": result["StudentID"],
                "StudentName": result["StudentName"],
                "CourseID": result.get("CourseID", course_id_str),
                "CourseSubject": result["CourseSubject"],
                "CourseName": result["CourseName"],
                "EventType": result["EventType"],
                "EventTimestamp": result["EventTimestamp"],
                "Transcript": result["Transcript"],
                "Concept": result["Concept"],
                "Prerequisite": result["Prerequisite"]
            }
            mapped_records.append(output_item)

        return mapped_records
