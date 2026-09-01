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
from app.services.transcript_service import TranscriptService, format_seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("cognitrace.worker")

STALE_JOB_TIMEOUT_MINUTES = 10
worker_wakeup_event = asyncio.Event()


def trigger_worker_wakeup():
    """Signal worker to process queued jobs immediately."""
    worker_wakeup_event.set()


async def recover_stale_jobs():
    """Reset jobs stuck in PROCESSING for over STALE_JOB_TIMEOUT_MINUTES back to PENDING."""
    if db.client is None:
        return
    database = db.client[settings.MONGODB_DB_NAME]
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES)
    
    stale_result = await database.transcription_jobs.update_many(
        {
            "status": "PROCESSING",
            "updated_at": {"$lt": cutoff_time}
        },
        {
            "$set": {
                "status": "PENDING",
                "progress": 0,
                "stage": "QUEUED",
                "message": "Recovered from stale PROCESSING timeout.",
                "updated_at": datetime.now(timezone.utc),
                "error_message": "Recovered from stale PROCESSING timeout."
            }
        }
    )
    if stale_result.modified_count > 0:
        print(f"\n[TRANSCRIPT WORKER] Reset {stale_result.modified_count} stale job(s) from PROCESSING -> PENDING")


async def claim_next_job():
    """Atomically find and claim the next PENDING transcription job."""
    if db.client is None:
        return None
    database = db.client[settings.MONGODB_DB_NAME]
    now = datetime.now(timezone.utc)

    job = await database.transcription_jobs.find_one_and_update(
        {"status": "PENDING"},
        {
            "$set": {
                "status": "PROCESSING",
                "progress": 5,
                "stage": "DOWNLOADING",
                "message": "Claimed job. Preparing audio download...",
                "updated_at": now
            },
            "$inc": {"attempts": 1}
        },
        return_document=ReturnDocument.AFTER
    )
    return job


async def update_job_progress(
    course_id: str,
    status_str: str,
    progress_val: int,
    stage_str: str,
    msg_str: str,
    processed_sec: float = 0.0,
    total_sec: float = 0.0
):
    """
    Update transcription job in MongoDB with strictly non-decreasing progress and worker heartbeat.
    """
    if db.client is None:
        return
    database = db.client[settings.MONGODB_DB_NAME]
    now = datetime.now(timezone.utc)

    existing_job = await database.transcription_jobs.find_one({"course_id": course_id})
    existing_tx = await database.course_transcripts.find_one({"course_id": course_id})

    # Protect COMPLETED or FAILED states from being overwritten by delayed progress callbacks
    if existing_job and existing_job.get("status") in ["COMPLETED", "FAILED"] and status_str == "PROCESSING":
        return
    if existing_tx and existing_tx.get("status") in ["COMPLETED", "FAILED"] and status_str == "PROCESSING":
        return

    current_pct = existing_job.get("progress", 0) if existing_job else 0
    safe_pct = max(current_pct, min(100, progress_val))

    update_payload = {
        "status": status_str,
        "progress": safe_pct,
        "stage": stage_str,
        "message": msg_str,
        "processed_seconds": processed_sec,
        "total_duration_seconds": total_sec,
        "updated_at": now,
        "error_message": None
    }

    await database.transcription_jobs.update_one(
        {"course_id": course_id},
        {"$set": update_payload},
        upsert=True
    )
    await database.course_transcripts.update_one(
        {"course_id": course_id},
        {"$set": {"status": status_str, "progress": safe_pct, "stage": stage_str, "message": msg_str, "updated_at": now}},
        upsert=True
    )


async def process_single_job(job: dict):
    """Process a claimed transcription job with explicit progress stages and real percentage tracking."""
    course_id = job["course_id"]
    database = db.client[settings.MONGODB_DB_NAME]
    temp_audio_file = None
    now = datetime.now(timezone.utc)
    t_start_total = time.time()
    last_reported_pct = -1

    try:
        # Log job received
        print(f"[TRANSCRIPT WORKER] Job received: {course_id}")
        logger.info("[TRANSCRIPT WORKER] Job received: %s", course_id)

        course = await database.courses.find_one({"_id": ObjectId(course_id)})
        if not course:
            err_msg = "Course not found in database."
            print(f"[TRANSCRIPT ERROR] {err_msg}")
            await update_job_progress(course_id, "FAILED", 0, "FAILED", err_msg)
            return

        # Stage: DOWNLOADING
        print(f"[TRANSCRIPT WORKER] Status: DOWNLOADING (YouTube URL: {course['youtube_url']})")
        logger.info("[TRANSCRIPT WORKER] Status: DOWNLOADING (%s)", course['youtube_url'])

        if not course.get("youtube_url") or ("youtube" not in course["youtube_url"].lower() and "youtu.be" not in course["youtube_url"].lower()):
            raise ValueError("Course contains invalid YouTube URL.")

        await update_job_progress(course_id, "PROCESSING", 5, "DOWNLOADING", "Downloading YouTube audio stream...")

        # Capture main event loop for thread callbacks
        main_loop = asyncio.get_running_loop()

        # Progress Callback for Audio Extraction
        def audio_progress_cb(pct, stage, msg):
            asyncio.run_coroutine_threadsafe(
                update_job_progress(course_id, "PROCESSING", pct, stage, msg),
                main_loop
            )

        # Stage: EXTRACTING_AUDIO (run in thread pool to prevent blocking event loop)
        print(f"[TRANSCRIPT WORKER] Status: EXTRACTING_AUDIO")
        t_audio_start = time.time()
        
        temp_audio_file, duration_secs, size_mb = await asyncio.to_thread(
            TranscriptService.extract_audio,
            course["youtube_url"],
            audio_progress_cb
        )
        
        t_audio_end = time.time()
        audio_extract_time = round(t_audio_end - t_audio_start, 2)
        duration_fmt = format_seconds(duration_secs)

        print(f"[TRANSCRIPT WORKER] Audio extracted ({audio_extract_time}s, {duration_fmt}, {size_mb} MB)")
        await update_job_progress(
            course_id, "PROCESSING", 15, "EXTRACTING_AUDIO",
            f"Audio extracted ({duration_fmt}, {size_mb} MB). Loading Faster-Whisper...",
            processed_sec=0.0, total_sec=duration_secs
        )

        # Stage: TRANSCRIBING
        print(f"[TRANSCRIPT WORKER] Status: TRANSCRIBING (Model: '{settings.WHISPER_MODEL_SIZE}', Device: '{settings.WHISPER_DEVICE}')")
        logger.info("[WHISPER] Device: %s, Model: %s", settings.WHISPER_DEVICE.upper(), settings.WHISPER_MODEL_SIZE)

        await update_job_progress(
            course_id, "PROCESSING", 15, "TRANSCRIBING",
            f"Faster-Whisper model ready. Starting transcription (00:00 / {duration_fmt})...",
            processed_sec=0.0, total_sec=duration_secs
        )

        # Progress Callback for Transcription Stage (15% to 95%)
        def transcribe_progress_cb(proc_sec: float, tot_sec: float, msg: str):
            nonlocal last_reported_pct
            if tot_sec > 0:
                pct = 15 + int((proc_sec / tot_sec) * 80)
                pct = min(95, max(15, pct))
                if pct >= last_reported_pct + 2 or pct == 95:
                    last_reported_pct = pct
                    asyncio.run_coroutine_threadsafe(
                        update_job_progress(
                            course_id, "PROCESSING", pct, "TRANSCRIBING",
                            f"Transcribing audio: {format_seconds(proc_sec)} / {format_seconds(tot_sec)} ({pct}%)",
                            processed_sec=proc_sec, total_sec=tot_sec
                        ),
                        main_loop
                    )

        t_transcribe_start = time.time()
        # Run Whisper inference in worker thread pool so FastAPI main thread stays 100% responsive
        segments, lang = await asyncio.to_thread(
            TranscriptService.transcribe_audio_file,
            temp_audio_file,
            duration_secs,
            transcribe_progress_cb
        )
        t_transcribe_end = time.time()
        transcribe_time = round(t_transcribe_end - t_transcribe_start, 2)
        print(f"[TRANSCRIPT WORKER] Transcription completed in {transcribe_time}s ({len(segments)} segments, language: '{lang}')")

        # Stage: SAVING
        print(f"[TRANSCRIPT WORKER] Status: SAVING")
        await update_job_progress(
            course_id, "PROCESSING", 96, "SAVING",
            f"Saving {len(segments)} transcript segments to database...",
            processed_sec=duration_secs, total_sec=duration_secs
        )
        completed_time = datetime.now(timezone.utc)

        await database.course_transcripts.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "course_name": course["course_name"],
                    "subject": course["subject"],
                    "teacher_id": course["teacher_id"],
                    "teacher_name": course["teacher_name"],
                    "youtube_url": course["youtube_url"],
                    "status": "COMPLETED",
                    "progress": 100,
                    "stage": "COMPLETED",
                    "message": "Transcription complete.",
                    "processed_seconds": duration_secs,
                    "total_duration_seconds": duration_secs,
                    "language": lang or "en",
                    "segments": segments,
                    "error_message": None,
                    "updated_at": completed_time
                }
            },
            upsert=True
        )

        await database.transcription_jobs.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "status": "COMPLETED",
                    "progress": 100,
                    "stage": "COMPLETED",
                    "message": "Transcription complete.",
                    "processed_seconds": duration_secs,
                    "total_duration_seconds": duration_secs,
                    "updated_at": completed_time,
                    "error_message": None
                }
            }
        )

        # Automatic Concept Extraction Queueing
        print(f"[TRANSCRIPT WORKER] Automatically queuing concept extraction for {course_id}")
        await database.concept_extraction_jobs.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "course_id": course_id,
                    "teacher_id": course["teacher_id"],
                    "status": "PENDING",
                    "attempts": 0,
                    "error_message": None,
                    "created_at": completed_time,
                    "updated_at": completed_time
                }
            },
            upsert=True
        )

        await database.concept_segments.update_one(
            {"course_id": course_id},
            {
                "$set": {
                    "course_id": course_id,
                    "CourseSubject": course["subject"],
                    "CourseName": course["course_name"],
                    "teacher_id": course["teacher_id"],
                    "teacher_name": course["teacher_name"],
                    "status": "PENDING",
                    "segments": [],
                    "error_message": None,
                    "created_at": completed_time,
                    "updated_at": completed_time
                }
            },
            upsert=True
        )

        try:
            from app.workers.concept_worker import trigger_concept_worker_wakeup
            trigger_concept_worker_wakeup()
        except Exception as wake_err:
            print(f"[TRANSCRIPT WORKER] Failed to wake concept worker: {wake_err}")

        total_time = round(time.time() - t_start_total, 2)
        # Stage: COMPLETED
        print(f"[TRANSCRIPT WORKER] Status: COMPLETED (Total: {total_time}s, Segments: {len(segments)})")
        logger.info("[TRANSCRIPT WORKER] Completed course %s in %ss", course_id, total_time)

    except Exception as err:
        print(f"[TRANSCRIPT ERROR] Transcription failed for course {course_id}: {err}")
        logger.error("Error processing job %s: %s", course_id, err, exc_info=True)
        failed_time = datetime.now(timezone.utc)
        safe_err_msg = f"Transcript generation failed: {str(err)}"

        await database.course_transcripts.update_one(
            {"course_id": course_id},
            {"$set": {"status": "FAILED", "progress": 0, "stage": "FAILED", "error_message": safe_err_msg, "updated_at": failed_time}},
            upsert=True
        )
        await database.transcription_jobs.update_one(
            {"course_id": course_id},
            {"$set": {"status": "FAILED", "progress": 0, "stage": "FAILED", "error_message": safe_err_msg, "updated_at": failed_time}}
        )

    finally:
        # Temporary Audio File Cleanup
        if temp_audio_file and os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
                print(f"[CLEANUP] Deleted temporary audio file {temp_audio_file}")
            except Exception as clean_err:
                print(f"[WARNING] Failed to remove temp audio file {temp_audio_file}: {clean_err}")


async def run_worker_loop(run_once: bool = False):
    """
    Main transcript worker loop.
    Prints required startup logging and continuously processes PENDING jobs in queue.
    """
    print("[TRANSCRIPT WORKER] Starting...")
    logger.info("[TRANSCRIPT WORKER] Starting...")
    await connect_to_mongo()

    # Pre-load Faster-Whisper model ONCE at worker startup (if available)
    print(f"[WHISPER] Device: {settings.WHISPER_DEVICE.upper()}, Model: {settings.WHISPER_MODEL_SIZE}")
    try:
        TranscriptService.get_model()
        print("[TRANSCRIPT WORKER] Running")
        print("[TRANSCRIPT WORKER] Waiting for jobs")
        logger.info("[TRANSCRIPT WORKER] Running - Waiting for jobs")
    except RuntimeError as e:
        if "not installed" in str(e):
            print("[TRANSCRIPT WORKER] faster-whisper not installed — worker will skip transcription jobs.")
            logger.warning("[TRANSCRIPT WORKER] faster-whisper unavailable: %s", e)
            print("[TRANSCRIPT WORKER] Running (transcript jobs will be skipped)")
            print("[TRANSCRIPT WORKER] Waiting for jobs")
        else:
            print(f"[CRITICAL] Failed to load Faster-Whisper model: {e}")
            logger.error("[TRANSCRIPT WORKER] Model load failed: %s", e)
            # Don't return/close DB — let worker run anyway (jobs will fail gracefully)

    try:
        while True:
            await recover_stale_jobs()
            job = await claim_next_job()

            if job:
                await process_single_job(job)
                if run_once:
                    break
            else:
                if run_once:
                    break
                # Wait on wakeup event or timeout (2 seconds)
                try:
                    await asyncio.wait_for(worker_wakeup_event.wait(), timeout=2.0)
                    worker_wakeup_event.clear()
                except asyncio.TimeoutError:
                    pass
    except asyncio.CancelledError:
        print("[TRANSCRIPT WORKER] Task cancelled cleanly.")
    except KeyboardInterrupt:
        print("[TRANSCRIPT WORKER] Stopped by user.")
    finally:
        await close_mongo_connection()
        print("[TRANSCRIPT WORKER] Stopped")


if __name__ == "__main__":
    once_flag = "--once" in sys.argv
    asyncio.run(run_worker_loop(run_once=once_flag))
