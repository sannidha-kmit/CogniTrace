import re
import logging
from typing import Optional, Dict, Any
from bson import ObjectId

from app.db.mongodb import get_database
from app.schemas.quiz import RevisionResource
from app.services.revision_link_service import RevisionLinkService

logger = logging.getLogger("cognitrace.quiz.learning_resource")


class LearningResourceService:
    """
    Service responsible for mapping course & concept identifiers to trusted educational video resources
    and exact video timestamp positions.
    Guarantees: Never hallucinates or randomly generates timestamps.
    """

    @classmethod
    async def get_revision_resource(
        cls,
        course_id: str,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        question_text: Optional[str] = None,
        correct_answer: Optional[str] = None,
        explanation: Optional[str] = None
    ) -> Optional[RevisionResource]:
        """
        Locate the educational video resource and trusted concept/transcript timestamp for a course.
        1. Retrieves video URL and course metadata from courses collection.
        2. Matches exact lecture transcript segment if question/answer context is provided.
        3. Falls back to concept timestamp boundaries from concept_segments collection.
        4. Formats canonical timestamp seconds and display string.
        5. Generates direct revision URL.
        """
        database = await get_database()
        clean_course_id = str(course_id)

        # 1. Fetch Course Document
        course_doc = None
        if ObjectId.is_valid(clean_course_id):
            course_doc = await database.courses.find_one({"_id": ObjectId(clean_course_id)})
        if not course_doc:
            course_doc = await database.courses.find_one({"_id": clean_course_id})

        if not course_doc:
            logger.info("[LEARNING RESOURCE] Course '%s' not found.", clean_course_id)
            return None

        video_url = course_doc.get("youtube_url", "").strip()
        if not video_url:
            logger.info("[LEARNING RESOURCE] Course '%s' has no associated video URL.", clean_course_id)
            return None

        course_title = course_doc.get("course_name", "Course Video Lecture")
        video_id = RevisionLinkService.extract_youtube_video_id(video_url)

        target_concept_name = concept_name
        if not target_concept_name and concept_id:
            if ":" in concept_id:
                target_concept_name = concept_id.split(":", 1)[1]
            else:
                target_concept_name = concept_id

        timestamp_seconds = None
        timestamp_display = None
        transcript_excerpt = None
        resource_title = course_title

        # 2. Try matching exact lecture transcript segment
        if question_text or correct_answer:
            try:
                tx_doc = await database.course_transcripts.find_one({"course_id": clean_course_id})
                if tx_doc and "segments" in tx_doc:
                    segments = tx_doc.get("segments", [])
                    stop_words = {
                        'in', 'the', 'of', 'what', 'is', 'a', 'an', 'to', 'that', 'which',
                        'following', 'statements', 'accurately', 'describes', 'as', 'defined',
                        'lecture', 'according', 'for', 'context', 'it', 'used', 'not', 'any',
                        'value', 'data', 'type', 'are', 'with', 'from', 'when', 'this'
                    }
                    combined = f"{question_text or ''} {correct_answer or ''} {explanation or ''}".lower()
                    words = [w for w in re.findall(r'\b[a-zA-Z0-9_]{3,}\b', combined) if w not in stop_words]
                    
                    best_seg = None
                    best_score = -1

                    for seg in segments:
                        stext = seg.get("text", "").lower()
                        score = sum(1 for w in words if w in stext)
                        
                        # Bonus for matching correct answer verbatim or close phrases
                        if correct_answer and correct_answer.strip().lower() in stext:
                            score += 8
                        
                        if score > best_score:
                            best_score = score
                            best_seg = seg

                    if best_seg and best_score >= 2:
                        raw_start = best_seg.get("start", 0)
                        timestamp_seconds = max(0, int(raw_start))
                        timestamp_display = RevisionLinkService.format_seconds_to_timestamp(timestamp_seconds)
                        transcript_excerpt = best_seg.get("text", "").strip()
                        resource_title = f"{course_title} — {target_concept_name or 'Segment'}"
                        logger.info(
                            "[LEARNING RESOURCE] Matched Transcript segment at %s (%ds, score=%d): %s",
                            timestamp_display, timestamp_seconds, best_score, transcript_excerpt[:50]
                        )
            except Exception as e:
                logger.warning("[LEARNING RESOURCE] Error matching transcript: %s", e)

        # 3. Fallback: Extract Concept Start Timestamp from concept_segments
        if timestamp_seconds is None:
            concept_doc = await database.concept_segments.find_one({"course_id": clean_course_id})
            if concept_doc and "segments" in concept_doc and target_concept_name:
                segments = concept_doc.get("segments", [])
                clean_target = target_concept_name.strip().lower()

                matched_seg = None
                # Exact match
                for s in segments:
                    s_name = s.get("Concept", "").strip().lower()
                    if s_name == clean_target:
                        matched_seg = s
                        break

                # Substring / partial match fallback
                if not matched_seg:
                    for s in segments:
                        s_name = s.get("Concept", "").strip().lower()
                        if clean_target in s_name or s_name in clean_target:
                            matched_seg = s
                            break

                if matched_seg:
                    raw_start = matched_seg.get("ConceptStart")
                    timestamp_seconds = RevisionLinkService.parse_timestamp_to_seconds(raw_start)
                    if timestamp_seconds is not None:
                        timestamp_display = RevisionLinkService.format_seconds_to_timestamp(timestamp_seconds)
                    c_display = matched_seg.get("Concept", target_concept_name)
                    resource_title = f"{course_title} — {c_display}"
                    logger.info(
                        "[LEARNING RESOURCE] Fallback matched Concept '%s' to timestamp %s (%ds)",
                        c_display, timestamp_display, timestamp_seconds or 0
                    )

        # 4. Final Fallback: Start at 0 seconds
        if timestamp_seconds is None:
            timestamp_seconds = 0
            timestamp_display = "00:00"

        # 5. Generate Revision URL
        revision_url = RevisionLinkService.create_revision_url(video_url, timestamp_seconds)

        return RevisionResource(
            video_id=video_id,
            video_title=resource_title,
            video_url=video_url,
            timestamp_seconds=timestamp_seconds,
            timestamp_display=timestamp_display,
            revision_url=revision_url,
            transcript_excerpt=transcript_excerpt
        )

