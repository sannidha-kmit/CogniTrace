from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.db.mongodb import get_database
from app.schemas.attention import (
    AttentionTelemetryCreate,
    AttentionTelemetryResponse,
    AttentionSummaryResponse,
    AttentionThresholdSettings,
    DistractionEventTypeEnum,
    AttentionStateEnum
)


class AttentionService:
    @staticmethod
    def get_default_settings() -> AttentionThresholdSettings:
        return AttentionThresholdSettings()

    @staticmethod
    async def record_telemetry(
        req: AttentionTelemetryCreate,
        current_student: dict
    ) -> AttentionTelemetryResponse:
        """
        Record a single derived attention telemetry event in MongoDB.
        Ensures strict privacy: ONLY derived numerical scores, durations, and state enums are saved.
        NO RAW CAMERA IMAGES OR AUDIO SAMPLES ARE EVER PROCESSED OR STORED ON SERVER.
        """
        if not ObjectId.is_valid(req.course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format."
            )

        database = await get_database()
        course = await database.courses.find_one({"_id": ObjectId(req.course_id)})

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target course not found."
            )

        # Enforce student academic year matching course year
        if course.get("year") != current_student.get("year"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You cannot record telemetry for courses outside your academic year."
            )

        student_id = current_student["identifier"]
        student_name = current_student.get("name", "")
        course_id_str = str(course["_id"])
        course_subject = course.get("subject", "")
        course_name = course.get("course_name", "")
        now = datetime.now(timezone.utc)

        head_pose_dict = req.head_pose.model_dump() if req.head_pose else None

        # Privacy-Preserving Event Document
        event_doc = {
            "StudentID": student_id,
            "StudentName": student_name,
            "CourseID": course_id_str,
            "CourseSubject": course_subject,
            "CourseName": course_name,
            "video_timestamp": req.video_timestamp,
            "attention_state": req.attention_state.value if hasattr(req.attention_state, "value") else str(req.attention_state),
            "distraction_score": float(req.distraction_score),
            "distraction_duration": float(req.distraction_duration),
            "event_type": req.event_type.value if hasattr(req.event_type, "value") else str(req.event_type),
            "confidence": float(req.confidence),
            "head_pose": head_pose_dict,
            "noise_level": req.noise_level.value if hasattr(req.noise_level, "value") else str(req.noise_level) if req.noise_level else None,
            "environmental_distraction": bool(req.environmental_distraction),
            "behavioral_distraction": bool(req.behavioral_distraction),
            "notification_triggered": bool(req.notification_triggered),
            "created_at": now
        }

        result = await database.student_attention_events.insert_one(event_doc)
        event_id = str(result.inserted_id)

        return AttentionTelemetryResponse(
            id=event_id,
            StudentID=student_id,
            StudentName=student_name,
            CourseID=course_id_str,
            CourseSubject=course_subject,
            CourseName=course_name,
            video_timestamp=req.video_timestamp,
            attention_state=event_doc["attention_state"],
            distraction_score=req.distraction_score,
            distraction_duration=req.distraction_duration,
            event_type=event_doc["event_type"],
            confidence=req.confidence,
            head_pose=head_pose_dict,
            noise_level=event_doc["noise_level"],
            environmental_distraction=req.environmental_distraction,
            behavioral_distraction=req.behavioral_distraction,
            notification_triggered=req.notification_triggered,
            created_at=now
        )

    @staticmethod
    async def record_batch_telemetry(
        events: List[AttentionTelemetryCreate],
        current_student: dict
    ) -> Dict[str, Any]:
        """
        Record multiple derived attention events in bulk.
        """
        if not events:
            return {"inserted_count": 0}

        database = await get_database()
        student_id = current_student["identifier"]
        student_name = current_student.get("name", "")
        now = datetime.now(timezone.utc)

        # Cache course checks
        course_cache = {}
        docs = []

        for req in events:
            if req.course_id not in course_cache:
                if not ObjectId.is_valid(req.course_id):
                    continue
                course = await database.courses.find_one({"_id": ObjectId(req.course_id)})
                if not course or course.get("year") != current_student.get("year"):
                    continue
                course_cache[req.course_id] = course

            course = course_cache[req.course_id]
            head_pose_dict = req.head_pose.model_dump() if req.head_pose else None

            doc = {
                "StudentID": student_id,
                "StudentName": student_name,
                "CourseID": str(course["_id"]),
                "CourseSubject": course.get("subject", ""),
                "CourseName": course.get("course_name", ""),
                "video_timestamp": req.video_timestamp,
                "attention_state": req.attention_state.value if hasattr(req.attention_state, "value") else str(req.attention_state),
                "distraction_score": float(req.distraction_score),
                "distraction_duration": float(req.distraction_duration),
                "event_type": req.event_type.value if hasattr(req.event_type, "value") else str(req.event_type),
                "confidence": float(req.confidence),
                "head_pose": head_pose_dict,
                "noise_level": req.noise_level.value if hasattr(req.noise_level, "value") else str(req.noise_level) if req.noise_level else None,
                "environmental_distraction": bool(req.environmental_distraction),
                "behavioral_distraction": bool(req.behavioral_distraction),
                "notification_triggered": bool(req.notification_triggered),
                "created_at": now
            }
            docs.append(doc)

        if docs:
            result = await database.student_attention_events.insert_many(docs)
            return {"inserted_count": len(result.inserted_ids)}
        return {"inserted_count": 0}

    @staticmethod
    async def get_student_course_summary(
        course_id: str,
        student_id: str
    ) -> AttentionSummaryResponse:
        """
        Calculate aggregated attention metrics for a student on a specific course.
        """
        database = await get_database()
        if not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID.")

        course = await database.courses.find_one({"_id": ObjectId(course_id)})
        course_name = course.get("course_name", "Unknown Course") if course else "Unknown Course"

        cursor = database.student_attention_events.find({
            "CourseID": course_id,
            "StudentID": student_id
        })
        events = await cursor.to_list(length=2000)

        if not events:
            return AttentionSummaryResponse(
                student_id=student_id,
                course_id=course_id,
                course_name=course_name,
                total_events=0,
                focused_ratio=1.0,
                distraction_event_count=0,
                avg_distraction_score=0.0,
                total_distraction_seconds=0.0,
                dominant_distraction_type=None,
                high_noise_incidents=0
            )

        total_events = len(events)
        focused_events = [e for e in events if e.get("attention_state") in [AttentionStateEnum.FOCUSED.value, AttentionStateEnum.RECOVERED.value]]
        distraction_events = [e for e in events if e.get("attention_state") in [
            AttentionStateEnum.POSSIBLE_DISTRACTION.value,
            AttentionStateEnum.SUSTAINED_DISTRACTION.value,
            AttentionStateEnum.HIGH_DISTRACTION.value
        ]]
        high_noise = [e for e in events if e.get("noise_level") == "NOISY" or e.get("environmental_distraction") is True]

        scores = [e.get("distraction_score", 0.0) for e in events]
        avg_score = sum(scores) / total_events if total_events > 0 else 0.0

        durations = [e.get("distraction_duration", 0.0) for e in distraction_events]
        total_dist_secs = sum(durations)

        # Dominant distraction event type
        type_counts: Dict[str, int] = {}
        for e in distraction_events:
            et = e.get("event_type", "LOOKING_AWAY")
            type_counts[et] = type_counts.get(et, 0) + 1

        dominant_type = max(type_counts, key=type_counts.get) if type_counts else None

        return AttentionSummaryResponse(
            student_id=student_id,
            course_id=course_id,
            course_name=course_name,
            total_events=total_events,
            focused_ratio=round(len(focused_events) / total_events, 3) if total_events > 0 else 1.0,
            distraction_event_count=len(distraction_events),
            avg_distraction_score=round(avg_score, 2),
            total_distraction_seconds=round(total_dist_secs, 1),
            dominant_distraction_type=dominant_type,
            high_noise_incidents=len(high_noise)
        )
