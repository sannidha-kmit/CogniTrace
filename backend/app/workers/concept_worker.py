import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from pymongo import ReturnDocument

# Ensure app imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db
from app.services.concept_service import ConceptService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("cognitrace.concept_worker")

STALE_JOB_TIMEOUT_MINUTES = 10
concept_worker_wakeup_event = asyncio.Event()


def trigger_concept_worker_wakeup():
    """Signal concept worker to process queued jobs immediately."""
    concept_worker_wakeup_event.set()


async def recover_stale_concept_jobs():
    """Reset jobs stuck in PROCESSING for over STALE_JOB_TIMEOUT_MINUTES back to PENDING."""
    if db.client is None:
        return
    database = db.client[settings.MONGODB_DB_NAME]
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES)
    
    stale_result = await database.concept_extraction_jobs.update_many(
        {
            "status": "PROCESSING",
            "updated_at": {"$lt": cutoff_time}
        },
        {
            "$set": {
                "status": "PENDING",
                "updated_at": datetime.now(timezone.utc),
                "error_message": "Recovered from stale PROCESSING timeout."
            }
        }
    )
    if stale_result.modified_count > 0:
        print(f"\n[CONCEPT WORKER] Reset {stale_result.modified_count} stale concept job(s) from PROCESSING -> PENDING")


async def claim_next_concept_job():
    """Atomically find and claim the next PENDING concept extraction job."""
    if db.client is None:
        return None
    database = db.client[settings.MONGODB_DB_NAME]
    now = datetime.now(timezone.utc)

    job = await database.concept_extraction_jobs.find_one_and_update(
        {"status": "PENDING"},
        {
            "$set": {
                "status": "PROCESSING",
                "updated_at": now
            },
            "$inc": {"attempts": 1}
        },
        return_document=ReturnDocument.AFTER
    )
    return job


async def process_single_concept_job(job: dict):
    """Process a claimed concept extraction job."""
    course_id = job["course_id"]
    database = db.client[settings.MONGODB_DB_NAME]
    now = datetime.now(timezone.utc)
    t_start = time.time()

    print(f"[CONCEPT WORKER] Job received: {course_id}")
    logger.info("[CONCEPT WORKER] Job received: %s", course_id)

    try:
        course = await database.courses.find_one({"_id": ObjectId(course_id)})
        if not course:
            err_msg = "Course not found."
            print(f"[CONCEPT ERROR] {err_msg}")
            await database.concept_extraction_jobs.update_one(
                {"course_id": course_id},
                {"$set": {"status": "FAILED", "error_message": err_msg, "updated_at": now}}
            )
            return

        tx_doc = await database.course_transcripts.find_one({"course_id": course_id})

        if not tx_doc or tx_doc.get("status") != "COMPLETED" or not tx_doc.get("segments"):
            err_msg = "Transcript is required before concept extraction. No completed transcript found."
            print(f"[CONCEPT ERROR] {err_msg}")
            await database.concept_extraction_jobs.update_one(
                {"course_id": course_id},
                {"$set": {"status": "FAILED", "error_message": err_msg, "updated_at": now}}
            )
            await database.concept_segments.update_one(
                {"course_id": course_id},
                {"$set": {"status": "FAILED", "error_message": err_msg, "updated_at": now}},
                upsert=True
            )
            return

        segments = tx_doc["segments"]
        print(f"[CONCEPT WORKER] Extracting concepts from {len(segments)} transcript segments...")
        
        extracted_concepts = await asyncio.to_thread(
            ConceptService.extract_concepts_from_transcript,
            segments,
            course["subject"],
            course["course_name"]
        )

        completed_time = datetime.now(timezone.utc)

        await database.concept_segments.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "course_id": course_id,
                    "CourseSubject": course["subject"],
                    "CourseName": course["course_name"],
                    "teacher_id": course["teacher_id"],
                    "teacher_name": course["teacher_name"],
                    "status": "COMPLETED",
                    "segments": extracted_concepts,
                    "error_message": None,
                    "created_at": completed_time,
                    "updated_at": completed_time
                }
            },
            upsert=True
        )

        await database.concept_extraction_jobs.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "status": "COMPLETED",
                    "updated_at": completed_time,
                    "error_message": None
                }
            }
        )

        elapsed = round(time.time() - t_start, 2)
        print(f"[CONCEPT WORKER] Status: COMPLETED ({len(extracted_concepts)} concepts, {elapsed}s)")
        logger.info("[CONCEPT WORKER] Completed course %s in %ss", course_id, elapsed)

    except Exception as err:
        print(f"[CONCEPT ERROR] Concept extraction failed for course {course_id}: {err}")
        failed_time = datetime.now(timezone.utc)
        safe_err_msg = f"Concept extraction failed: {str(err)}"

        await database.concept_extraction_jobs.update_one(
            {"course_id": course_id},
            {"$set": {"status": "FAILED", "error_message": safe_err_msg, "updated_at": failed_time}}
        )
        await database.concept_segments.update_one(
            {"course_id": course_id},
            {"$set": {"status": "FAILED", "error_message": safe_err_msg, "updated_at": failed_time}},
            upsert=True
        )


async def run_concept_worker_loop(run_once: bool = False):
    """
    Main concept extraction worker loop.
    Continuously polls and claims PENDING jobs in concept_extraction_jobs queue.
    """
    print("[CONCEPT WORKER] Starting...")
    logger.info("[CONCEPT WORKER] Starting...")
    await connect_to_mongo()
    print("[CONCEPT WORKER] Running")
    print("[CONCEPT WORKER] Waiting for jobs")

    try:
        while True:
            await recover_stale_concept_jobs()
            job = await claim_next_concept_job()

            if job:
                await process_single_concept_job(job)
                if run_once:
                    break
            else:
                if run_once:
                    break
                try:
                    await asyncio.wait_for(concept_worker_wakeup_event.wait(), timeout=2.0)
                    concept_worker_wakeup_event.clear()
                except asyncio.TimeoutError:
                    pass
    except asyncio.CancelledError:
        print("[CONCEPT WORKER] Task cancelled cleanly.")
    except KeyboardInterrupt:
        print("[CONCEPT WORKER] Stopped by user.")
    finally:
        await close_mongo_connection()
        print("[CONCEPT WORKER] Stopped")


if __name__ == "__main__":
    once_flag = "--once" in sys.argv
    asyncio.run(run_concept_worker_loop(run_once=once_flag))
