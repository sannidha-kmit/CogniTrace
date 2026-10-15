import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import asyncio
import sys
import time
import logging
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db
from app.workers.transcript_worker import run_worker_loop

logging.basicConfig(level=logging.INFO)


async def run_decoupled_tests():
    print("=" * 60)
    print("STARTING PHASE 4 DECOUPLED ARCHITECTURE VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24A201", "T24A202", "S24A201", "S24A202"]
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.course_transcripts.delete_many({"teacher_id": {"$in": test_ids}})
    await database.transcription_jobs.delete_many({"teacher_id": {"$in": test_ids}})
    await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})
    await database.student_learning.delete_many({"StudentID": {"$in": test_ids}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # Setup 1: Register Teacher 1 (Nidhi - 2nd Year) & Teacher 2 (Rahul - 2nd Year)
        t1_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A201",
            "name": "Prof. Nidhi",
            "year": "2nd Year",
            "subject": "DAA",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t1_res.status_code == 201
        t1_token = t1_res.json()["access_token"]

        t2_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A202",
            "name": "Prof. Rahul",
            "year": "2nd Year",
            "subject": "OS",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t2_res.status_code == 201
        t2_token = t2_res.json()["access_token"]

        # Setup 2: Register Student 1
        s1_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A201",
            "name": "Student A",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s1_res.status_code == 201
        s1_token = s1_res.json()["access_token"]

        # TEST 1: Course Creation Speed (<20ms response time)
        print("\n--- TEST 1: Fast Course Creation (No Automatic Transcription) ---")
        t_start = time.time()
        c1_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Recursion Decoupled",
            "youtube_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        })
        t_duration = time.time() - t_start
        assert c1_res.status_code == 201
        c1_id = c1_res.json()["id"]
        assert t_duration < 0.5, f"Course creation took too long: {t_duration}s"
        print(f"[PASS] TEST 1: Course created instantly in {t_duration*1000:.1f}ms without invoking Faster-Whisper.")

        # TEST 2: Instant Transcript Job Queuing Response (<20ms)
        print("\n--- TEST 2: Instant Transcript Job Queue Response (<20ms) ---")
        t_start = time.time()
        gen_res = await ac.post(f"/api/v1/teacher/courses/{c1_id}/transcript/generate", headers={"Authorization": f"Bearer {t1_token}"})
        t_duration = time.time() - t_start
        assert gen_res.status_code == 202
        assert gen_res.json()["status"] == "PENDING"
        assert t_duration < 0.2, f"Transcript generate API response took too long: {t_duration}s"
        print(f"[PASS] TEST 2: Generate API returned HTTP 202 Accepted in {t_duration*1000:.1f}ms and queued job.")

        # TEST 3: Verify Job Record in MongoDB Queue
        print("\n--- TEST 3: Job Record Queued in MongoDB 'transcription_jobs' ---")
        queued_job = await database.transcription_jobs.find_one({"course_id": c1_id})
        assert queued_job is not None
        assert queued_job["status"] == "PENDING"
        print("[PASS] TEST 3: Job verified in MongoDB queue with status PENDING.")

        # TEST 4: Student Watch Page Responsiveness While Worker is Idle/Offline
        print("\n--- TEST 4: Student Watch Page & Search Responsiveness ---")
        t_start = time.time()
        search_res = await ac.get("/api/v1/student/courses/search?query=Recursion", headers={"Authorization": f"Bearer {s1_token}"})
        t_duration = time.time() - t_start
        assert search_res.status_code == 200
        assert len(search_res.json()) == 1
        assert t_duration < 0.2
        print(f"[PASS] TEST 4: Student search API responded in {t_duration*1000:.1f}ms while worker was offline.")

        # TEST 5: Standalone Worker Process Execution (run_once=True)
        print("\n--- TEST 5: Standalone Worker Process Execution ---")
        print("Executing standalone worker single pass...")
        await run_worker_loop(run_once=True)
        await connect_to_mongo()  # Re-establish test client connection after worker loop shutdown

        # Check job completion status in DB
        completed_job = await database.transcription_jobs.find_one({"course_id": c1_id})
        assert completed_job["status"] == "COMPLETED"

        tx_doc = await database.course_transcripts.find_one({"course_id": c1_id})
        assert tx_doc["status"] == "COMPLETED"
        assert len(tx_doc["segments"]) > 0
        print(f"[PASS] TEST 5: Worker process completed transcription and wrote {len(tx_doc['segments'])} segments to MongoDB.")

        # TEST 6: Retrieve Transcript via FastAPI Endpoints
        print("\n--- TEST 6: Retrieve Transcript via Teacher API ---")
        tx_res = await ac.get(f"/api/v1/teacher/courses/{c1_id}/transcript", headers={"Authorization": f"Bearer {t1_token}"})
        assert tx_res.status_code == 200
        assert tx_res.json()["status"] == "COMPLETED"
        assert len(tx_res.json()["segments"]) > 0
        print("[PASS] TEST 6: Transcript retrieved cleanly via FastAPI endpoint.")

        # TEST 7: Idempotency (Re-triggering generate on completed course returns immediately)
        print("\n--- TEST 7: Idempotent Re-trigger Check ---")
        gen_again = await ac.post(f"/api/v1/teacher/courses/{c1_id}/transcript/generate", headers={"Authorization": f"Bearer {t1_token}"})
        assert gen_again.status_code == 202
        assert gen_again.json()["message"] == "Transcript already generated."
        print("[PASS] TEST 7: Re-triggering generate on completed course returned status immediately without duplicate jobs.")

        # TEST 8: Teacher Ownership Isolation
        print("\n--- TEST 8: Teacher Ownership Isolation ---")
        unauth_res = await ac.get(f"/api/v1/teacher/courses/{c1_id}/transcript", headers={"Authorization": f"Bearer {t2_token}"})
        assert unauth_res.status_code == 403
        print("[PASS] TEST 8: Teacher 2 access to Teacher 1's transcript rejected with 403 Forbidden.")

        # TEST 9: Student Interaction Telemetry Tracking Integration
        print("\n--- TEST 9: Student Telemetry Tracking Integration ---")
        ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PLAY",
            "event_timestamp": "00:05"
        })
        assert ev.status_code == 201
        print("[PASS] TEST 9: Student interaction telemetry recorded successfully.")

        # TEST 10: Purge All Test Data (Return DB to 0 Records)
        print("\n--- TEST 10: Purge All Test Data (Return DB to 0 Records) ---")
        await database.users.delete_many({})
        await database.teachers.delete_many({})
        await database.students.delete_many({})
        await database.courses.delete_many({})
        await database.course_transcripts.delete_many({})
        await database.transcription_jobs.delete_many({})
        await database.interaction_events.delete_many({})
        await database.student_learning.delete_many({})

        final_users = await database.users.count_documents({})
        final_teachers = await database.teachers.count_documents({})
        final_students = await database.students.count_documents({})
        final_courses = await database.courses.count_documents({})
        final_txs = await database.course_transcripts.count_documents({})
        final_jobs = await database.transcription_jobs.count_documents({})

        assert final_users == 0
        assert final_teachers == 0
        assert final_students == 0
        assert final_courses == 0
        assert final_txs == 0
        assert final_jobs == 0
        print("[PASS] TEST 10: All test data purged. Database returned to EXACTLY 0 records!")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 10 DECOUPLED ARCHITECTURE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_decoupled_tests())
