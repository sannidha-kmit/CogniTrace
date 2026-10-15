import math
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId

from app.core.research_config import research_settings
from app.db.mongodb import get_database
from app.schemas.evidence import GranularEvidenceRecord, ConceptEvidenceSummary
from app.services.mapping_service import MappingService, parse_timestamp_to_seconds

logger = logging.getLogger("cognitrace.evidence_engine")


class EvidenceEngine:
    """
    Evidence-Aware Concept-Level Interaction Modeling & Temporal Decay Engine.
    Calculates reliability-weighted, mapping-confident, temporally-decayed evidence
    for educational video telemetry events.
    """

    @classmethod
    def classify_interaction_type(cls, event: Dict[str, Any]) -> Tuple[str, str]:
        """
        Map raw telemetry EventType & metadata to normalized interaction categories
        and descriptive reason strings.
        """
        e_type = str(event.get("EventType", "")).upper().strip()
        reason = str(event.get("PauseReason", "")).lower().strip() if event.get("PauseReason") else ""
        speed = event.get("PlaybackSpeed")

        if e_type == "REPLAY":
            return "replay", "Student actively replayed video segment"
        elif e_type == "SEEK_BACKWARD":
            return "backward_seek", "Student rewound to review previous content"
        elif e_type == "SEEK_FORWARD":
            return "forward_seek", "Student skipped forward"
        elif e_type in ["PAUSE", "UNDERSTAND_PAUSE"]:
            if reason == "study":
                return "study_pause", "Student paused for active study/comprehension"
            elif reason == "other_work":
                return "other_work_pause", "Student paused for extraneous distraction/task"
            else:
                return "normal_pause", "Standard video playback pause"
        elif e_type == "SPEED_CHANGE":
            try:
                s_val = float(speed) if speed is not None else 1.0
                if s_val < 1.0:
                    return "speed_decrease", f"Student reduced playback speed to {s_val}x"
                elif s_val > 1.0:
                    return "speed_increase", f"Student accelerated playback speed to {s_val}x"
                else:
                    return "normal_pause", "Normal playback speed selected"
            except (ValueError, TypeError):
                return "normal_pause", "Unspecified speed change"

        return "normal_pause", "General interaction event"

    @classmethod
    def get_interaction_weight(cls, interaction_type: str) -> float:
        """
        Retrieve configurable reliability weight for an interaction type.
        Returns 1.0 if research_settings.evidence_weighting is disabled (for ablation).
        """
        if not research_settings.evidence_weighting:
            return 1.0
        return float(research_settings.interaction_weights.get(interaction_type, 0.5))

    @classmethod
    def calculate_mapping_confidence(
        cls,
        event_secs: float,
        concept_segment: Optional[Dict[str, Any]],
        transcript_matched: bool = True
    ) -> float:
        """
        Calculate concept mapping confidence between 0.0 and 1.0.
        Factors:
        - Centrality in concept interval: events near middle have higher confidence.
        - Transcript match presence.
        """
        if not concept_segment:
            return 0.50

        c_start = parse_timestamp_to_seconds(concept_segment.get("ConceptStart", 0))
        c_end = parse_timestamp_to_seconds(concept_segment.get("ConceptEnd", c_start + 1.0))
        duration = max(1.0, c_end - c_start)

        if c_start <= event_secs <= c_end:
            # Event falls inside concept interval
            # Calculate distance from closest boundary normalized by interval length
            dist_from_edge = min(event_secs - c_start, c_end - event_secs)
            relative_depth = min(1.0, (dist_from_edge / (duration / 2.0))) if duration > 0 else 1.0

            # Base confidence between 0.85 (at border) and 0.98 (at center)
            base_conf = 0.85 + (0.13 * relative_depth)
        else:
            # Event outside boundaries (edge fallback)
            dist_out = min(abs(event_secs - c_start), abs(event_secs - c_end))
            decay_factor = math.exp(-0.05 * dist_out)
            base_conf = 0.40 + (0.35 * decay_factor)

        if transcript_matched:
            base_conf = min(1.0, base_conf + 0.02)
        else:
            base_conf = max(0.20, base_conf - 0.10)

        return round(max(0.0, min(1.0, base_conf)), 4)

    @classmethod
    def calculate_temporal_weight(
        cls,
        event_time: datetime,
        reference_time: Optional[datetime] = None,
        lambda_param: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate exponential temporal decay weight: exp(-lambda * delta_t_hours).
        Returns (temporal_weight, delta_t_hours).
        Returns (1.0, delta_t) if temporal_decay is disabled in research_settings.
        """
        ref = reference_time or datetime.now(timezone.utc)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)

        delta_secs = max(0.0, (ref - event_time).total_seconds())
        delta_hours = delta_secs / 3600.0

        if not research_settings.temporal_decay:
            return 1.0, round(delta_hours, 4)

        l_param = lambda_param if lambda_param is not None else research_settings.temporal_decay_lambda
        temporal_weight = math.exp(-l_param * delta_hours)
        return round(max(0.0, min(1.0, temporal_weight)), 6), round(delta_hours, 4)

    @classmethod
    async def process_and_aggregate_concept_evidence(
        cls,
        student_id: str,
        course_id: str,
        persist_records: bool = True
    ) -> Dict[str, ConceptEvidenceSummary]:
        """
        Full Evidence Processing Pipeline:
        1. Query raw telemetry events for Student + Course.
        2. Query course concept segments.
        3. For each event:
           - Classify interaction & weight
           - Calculate mapping confidence
           - Apply temporal decay
           - Calculate evidence contribution: weight * confidence * temporal_weight
        4. Store granular intermediate audit records in MongoDB collection 'concept_evidence'.
        5. Aggregate total evidence per concept.
        """
        database = await get_database()
        clean_student = student_id.strip().upper()
        str_course_id = str(course_id)
        now = datetime.now(timezone.utc)

        # 1. Retrieve course document & video_id if available
        course_doc = None
        if ObjectId.is_valid(str_course_id):
            course_doc = await database.courses.find_one({"_id": ObjectId(str_course_id)})
        if not course_doc:
            course_doc = await database.courses.find_one({"_id": str_course_id})

        course_name = course_doc.get("course_name", "") if course_doc else ""
        video_id = course_doc.get("youtube_url") or course_doc.get("video_id") if course_doc else None

        # 2. Retrieve concept segments
        concept_doc = await database.concept_segments.find_one({"course_id": str_course_id})
        concept_items = concept_doc.get("segments", []) if (concept_doc and concept_doc.get("status") == "COMPLETED") else []

        # 3. Retrieve raw telemetry interaction events
        import re
        event_query: Dict[str, Any] = {
            "StudentID": {"$regex": f"^{re.escape(clean_student)}$", "$options": "i"},
            "$or": [
                {"CourseID": str_course_id}
            ]
        }
        if course_name:
            event_query["$or"].append({"CourseName": course_name})

        events = await database.interaction_events.find(event_query).sort("created_at", 1).to_list(length=2000)

        # Initialize concept containers
        concept_records: Dict[str, List[GranularEvidenceRecord]] = {}
        concept_raw_counts: Dict[str, Dict[str, int]] = {}
        concept_type_evidence: Dict[str, Dict[str, float]] = {}

        for item in concept_items:
            c_name = item.get("Concept", "").strip()
            if c_name:
                concept_records[c_name] = []
                concept_raw_counts[c_name] = {}
                concept_type_evidence[c_name] = {}

        if not concept_records:
            concept_records["Core Concepts"] = []
            concept_raw_counts["Core Concepts"] = {}
            concept_type_evidence["Core Concepts"] = {}

        granular_docs_to_persist = []
        cumulative_evidence_tracker: Dict[str, float] = {c: 0.0 for c in concept_records}

        for ev in events:
            event_id = str(ev.get("_id", ev.get("id", "")))
            ts_str = str(ev.get("EventTimestamp", "00:00"))
            event_secs = parse_timestamp_to_seconds(ts_str)
            event_created_at = ev.get("created_at") or now

            # Find matching concept
            matched_concept_doc = None
            if concept_items:
                matched_data = MappingService.find_matching_concept_segment(concept_items, event_secs)
                matched_name = matched_data.get("Concept", "Core Concepts")
                # find the segment dict
                for seg in concept_items:
                    if seg.get("Concept") == matched_name:
                        matched_concept_doc = seg
                        break
            else:
                matched_name = ev.get("Concept") or "Core Concepts"

            if matched_name not in concept_records:
                concept_records[matched_name] = []
                concept_raw_counts[matched_name] = {}
                concept_type_evidence[matched_name] = {}
                cumulative_evidence_tracker[matched_name] = 0.0

            concept_id = f"{str_course_id}:{matched_name}"

            # Step A: Classify & Weight Interaction
            itype, desc = cls.classify_interaction_type(ev)
            iweight = cls.get_interaction_weight(itype)

            # Step B: Mapping Confidence
            mconf = cls.calculate_mapping_confidence(
                event_secs=event_secs,
                concept_segment=matched_concept_doc,
                transcript_matched=bool(ev.get("Transcript"))
            )

            # Step C: Temporal Decay Weight
            tweight, delta_t = cls.calculate_temporal_weight(
                event_time=event_created_at,
                reference_time=now
            )

            # Step D: Granular Evidence Contribution
            evidence_contrib = round(iweight * mconf * tweight, 6)
            cumulative_evidence_tracker[matched_name] = round(
                cumulative_evidence_tracker[matched_name] + evidence_contrib, 6
            )

            record = GranularEvidenceRecord(
                student_id=clean_student,
                course_id=str_course_id,
                video_id=video_id,
                concept_id=concept_id,
                concept_name=matched_name,
                event_id=event_id,
                interaction_type=itype,
                interaction_weight=iweight,
                mapping_confidence=mconf,
                timestamp=event_secs,
                event_time=event_created_at,
                delta_t=delta_t,
                temporal_weight=tweight,
                evidence_contribution=evidence_contrib,
                cumulative_evidence=cumulative_evidence_tracker[matched_name],
                created_at=now
            )

            concept_records[matched_name].append(record)

            # Track breakdowns
            concept_raw_counts[matched_name][itype] = concept_raw_counts[matched_name].get(itype, 0) + 1
            concept_type_evidence[matched_name][itype] = round(
                concept_type_evidence[matched_name].get(itype, 0.0) + evidence_contrib, 4
            )

            if persist_records:
                granular_docs_to_persist.append(record.model_dump())

        # 4. Batch persist to 'concept_evidence' collection if enabled
        if persist_records and granular_docs_to_persist:
            try:
                # Store new granular audit entries
                await database.concept_evidence.insert_many(granular_docs_to_persist)
                logger.info(
                    "[EVIDENCE ENGINE] Persisted %d granular evidence records for Student=%s, Course=%s",
                    len(granular_docs_to_persist), clean_student, str_course_id
                )
            except Exception as err:
                logger.error("[EVIDENCE ENGINE] Error persisting concept_evidence records: %s", err)

        # 5. Summarize evidence per concept
        summaries: Dict[str, ConceptEvidenceSummary] = {}
        for c_name, recs in concept_records.items():
            total_ev = sum(r.evidence_contribution for r in recs)
            c_id = f"{str_course_id}:{c_name}"

            # Normalized evidence score: non-linear sigmoid-like saturation into [0.0, 1.0]
            # score = 1 - exp(-0.35 * total_ev)
            norm_ev = round(1.0 - math.exp(-0.35 * total_ev), 4) if total_ev > 0 else 0.0

            summaries[c_name] = ConceptEvidenceSummary(
                student_id=clean_student,
                course_id=str_course_id,
                concept_id=c_id,
                concept_name=c_name,
                total_evidence=round(total_ev, 4),
                normalized_evidence=norm_ev,
                raw_event_count=len(recs),
                interaction_breakdown={k: float(v) for k, v in concept_raw_counts.get(c_name, {}).items()},
                weighted_breakdown=concept_type_evidence.get(c_name, {}),
                records=recs
            )

        return summaries
