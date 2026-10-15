import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.services.mapping_service import parse_timestamp_to_seconds

logger = logging.getLogger("cognitrace.difficulty_service")


class DifficultyService:
    """
    CogniTrace Phase 8 Service.
    Derives student difficulty scores strictly from Phase 5 (Interaction Telemetry)
    and Phase 7 (Concept-Event Mappings).
    """

    @staticmethod
    def calculate_difficulty_metrics(
        replay_count: int,
        pause_count: int,
        seek_backward_count: int,
        seek_forward_count: int,
        understand_pause_count: int
    ) -> Dict[str, Any]:
        """
        Deterministic difficulty calculation formula:
        - SEEK_BACKWARD: increases difficulty (weight 2.0)
        - REPLAY / repeated revisit: increases difficulty (weight 2.0)
        - PAUSE with PauseReason = STUDY (understand_pause_count): increases difficulty (weight 3.0)
        - SEEK_FORWARD: neutral / skip signal, weight 0.0 (does NOT increase difficulty)
        - Playback SPEED INCREASE: neutral / consumption speed, weight 0.0 (does NOT increase difficulty)
        - PAUSE with OTHER_WORK / general pause: neutral non-learning, weight 0.0 (does NOT increase difficulty)

        Score = (ReplayCount × 2.0) + (SeekBackwardCount × 2.0) + (UnderstandPauseCount × 3.0)
        """
        score = (
            (replay_count * 2.0)
            + (seek_backward_count * 2.0)
            + (understand_pause_count * 3.0)
        )

        level = "Easy"
        needs_revision = False

        if score >= 7.0:
            level = "High"
            needs_revision = True
        elif score >= 3.0:
            level = "Medium"
            needs_revision = False
        else:
            level = "Easy"
            needs_revision = False

        return {
            "DifficultyScore": float(score),
            "DifficultyLevel": level,
            "NeedsRevision": needs_revision
        }

    @classmethod
    async def generate_difficulty_dataset(
        cls,
        database: Any,
        roll_number: str,
        teacher_subject: str,
        teacher_course_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate and idempotently upsert the Phase 8 difficulty dataset for a student.
        Propagates CourseID for unambiguous course identification.
        """
        clean_roll = roll_number.strip().upper()
        import re

        # 1. Fetch Phase 7 concept-event mappings
        mapping_query = {
            "StudentID": {"$regex": f"^{re.escape(clean_roll)}$", "$options": "i"},
            "$or": [
                {"CourseName": {"$in": teacher_course_names}},
                {"CourseSubject": teacher_subject}
            ]
        }
        mappings_cursor = database.concept_event_mappings.find(mapping_query)
        mappings = await mappings_cursor.to_list(length=5000)

        if not mappings:
            return []

        # 2. Fetch all raw Phase 5 events to join `PauseReason`
        events_cursor = database.interaction_events.find(mapping_query)
        raw_events = await events_cursor.to_list(length=5000)

        # Create lookup dictionaries for raw events by (CourseID/CourseName, EventType, EventTimestamp)
        raw_event_lookup = {}
        for ev in raw_events:
            c_id = ev.get("CourseID")
            c_name = ev.get("CourseName")
            e_type = ev.get("EventType")
            e_ts = ev.get("EventTimestamp")
            
            if c_id:
                key_id = (str(c_id), e_type, e_ts)
                if key_id not in raw_event_lookup:
                    raw_event_lookup[key_id] = []
                raw_event_lookup[key_id].append(ev)
                
            if c_name:
                key_name = (str(c_name), e_type, e_ts)
                if key_name not in raw_event_lookup:
                    raw_event_lookup[key_name] = []
                raw_event_lookup[key_name].append(ev)

        # 3. Group mappings by StudentID + CourseID + CourseName + Concept
        # Format: { (course_id, course_name, concept): [mapped_events...] }
        grouped_mappings: Dict[tuple, List[Dict[str, Any]]] = {}
        for m in mappings:
            c_name = m.get("CourseName")
            c_id = m.get("CourseID")
            concept = m.get("Concept")
            # Exclude mappings that couldn't find a concept (defensive)
            if not concept or concept == "Uncategorized Concept":
                continue

            if not c_id:
                # Look up course_id if not present in legacy mapping document
                course_doc = await database.courses.find_one({
                    "course_name": c_name,
                    "subject": teacher_subject
                })
                if course_doc:
                    c_id = str(course_doc["_id"])
            
            group_key = (c_id or c_name, c_name, concept)
            if group_key not in grouped_mappings:
                grouped_mappings[group_key] = []
            grouped_mappings[group_key].append(m)

        # 4. Calculate metrics for each group
        difficulty_records = []
        now = datetime.now(timezone.utc)

        for (c_id, c_name, concept), mapped_events in grouped_mappings.items():
            replay_count = 0
            pause_count = 0
            seek_backward_count = 0
            seek_forward_count = 0
            understand_pause_count = 0

            # To prevent double counting SEEK_BACKWARD and REPLAY at the exact same timestamp
            # (which happens during progress bar jump in frontend)
            replay_timestamps = set()

            # First pass: collect REPLAY timestamps
            for m in mapped_events:
                if m.get("EventType") == "REPLAY":
                    replay_timestamps.add(m.get("EventTimestamp"))
                    replay_count += 1

            # Second pass: count other events
            for m in mapped_events:
                e_type = m.get("EventType")
                e_ts = m.get("EventTimestamp")

                if e_type == "PAUSE":
                    pause_count += 1
                    # Look up PauseReason from Phase 5 using CourseID or CourseName
                    lookup_key = (str(c_id), "PAUSE", e_ts)
                    matched_raw_events = raw_event_lookup.get(lookup_key)
                    if not matched_raw_events:
                        matched_raw_events = raw_event_lookup.get((str(c_name), "PAUSE", e_ts), [])

                    if matched_raw_events:
                        raw_ev = matched_raw_events[0]
                        reason = str(raw_ev.get("PauseReason", "")).strip()
                        # Strict STUDY pause check: STUDY or legacy 'understand' keyword
                        if reason.upper() == "STUDY" or "understand" in reason.lower():
                            understand_pause_count += 1

                elif e_type == "SEEK_FORWARD":
                    seek_forward_count += 1

                elif e_type == "SEEK_BACKWARD":
                    # Only count if no REPLAY event exists at this exact timestamp
                    if e_ts not in replay_timestamps:
                        seek_backward_count += 1

            # Calculate final metrics with corrected formula
            metrics = cls.calculate_difficulty_metrics(
                replay_count=replay_count,
                pause_count=pause_count,
                seek_backward_count=seek_backward_count,
                seek_forward_count=seek_forward_count,
                understand_pause_count=understand_pause_count
            )

            student_name = mapped_events[0].get("StudentName", "Student")

            # 5. Assemble exact dataset record
            diff_data = {
                "StudentID": clean_roll,
                "StudentName": student_name,
                "CourseID": str(c_id) if c_id else None,
                "CourseSubject": teacher_subject,
                "CourseName": c_name,
                "Concept": concept,
                "ReplayCount": replay_count,
                "PauseCount": pause_count,
                "SeekBackwardCount": seek_backward_count,
                "SeekForwardCount": seek_forward_count,
                "UnderstandPauseCount": understand_pause_count,
                "DifficultyScore": metrics["DifficultyScore"],
                "DifficultyLevel": metrics["DifficultyLevel"],
                "NeedsRevision": metrics["NeedsRevision"],
                "updated_at": now
            }

            # 6. Idempotent Upsert into difficulty collection using StudentID + CourseID + Concept
            if c_id:
                match_filter = {
                    "StudentID": diff_data["StudentID"],
                    "CourseID": str(c_id),
                    "Concept": diff_data["Concept"]
                }
            else:
                match_filter = {
                    "StudentID": diff_data["StudentID"],
                    "CourseSubject": diff_data["CourseSubject"],
                    "CourseName": diff_data["CourseName"],
                    "Concept": diff_data["Concept"]
                }

            result = await database.difficulty.find_one_and_update(
                match_filter,
                {"$set": diff_data, "$setOnInsert": {"created_at": now}},
                upsert=True,
                return_document=True
            )

            # Clean output dictionary with exact dataset fields + id
            output_item = {
                "id": str(result["_id"]),
                "StudentID": result["StudentID"],
                "StudentName": result["StudentName"],
                "CourseID": result.get("CourseID", str(c_id) if c_id else None),
                "CourseSubject": result["CourseSubject"],
                "CourseName": result["CourseName"],
                "Concept": result["Concept"],
                "ReplayCount": result["ReplayCount"],
                "PauseCount": result["PauseCount"],
                "SeekBackwardCount": result["SeekBackwardCount"],
                "SeekForwardCount": result["SeekForwardCount"],
                "UnderstandPauseCount": result["UnderstandPauseCount"],
                "DifficultyScore": result["DifficultyScore"],
                "DifficultyLevel": result["DifficultyLevel"],
                "NeedsRevision": result["NeedsRevision"]
            }
            difficulty_records.append(output_item)

        return difficulty_records
