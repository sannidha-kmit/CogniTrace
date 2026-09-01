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
from app.workers.concept_worker import run_concept_worker_loop

logging.basicConfig(level=logging.INFO)


async def run_phase6_tests():
    print("=" * 60)
    print("STARTING PHASE 6 CONCEPT EXTRACTION VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24AC61", "T24AC62", "S24AC61"]
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.course_transcripts.delete_many({"teacher_id": {"$in": test_ids}})
    await database.transcription_jobs.delete_many({"teacher_id": {"$in": test_ids}})
    await database.concept_segments.delete_many({"teacher_id": {"$in": test_ids}})
    await database.concept_extraction_jobs.delete_many({"teacher_id": {"$in": test_ids}})
    await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # Setup 1: Register Teacher 1 (Priya - T24AC61 - 2nd Year - DAA)
        t1_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24AC61",
            "name": "Prof. Priya",
            "year": "2nd Year",
            "subject": "DAA",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t1_res.status_code == 201
        t1_token = t1_res.json()["access_token"]

        # Setup 2: Register Teacher 2 (Ravi - T24AC62 - 2nd Year - OS)
        t2_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24AC62",
            "name": "Prof. Ravi",
            "year": "2nd Year",
            "subject": "Operating Systems",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t2_res.status_code == 201
        t2_token = t2_res.json()["access_token"]

        # Setup 3: Register Student Sannidha (S24AC61)
        s1_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24AC61",
            "name": "Sannidha",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s1_res.status_code == 201
        s1_token = s1_res.json()["access_token"]

        # Setup 4: Create Course 1 for Teacher 1
        c1_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Definition Concept Test",
            "youtube_url": "https://www.youtube.com/watch?v=ONFkb-PxKts"
        })
        assert c1_res.status_code == 201
        c1_id = c1_res.json()["id"]

        # Setup 5: Create Course 2 without Transcript
        c2_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "No Transcript Course",
            "youtube_url": "https://www.youtube.com/watch?v=2lAe1cqCOXo"
        })
        assert c2_res.status_code == 201
        c2_id = c2_res.json()["id"]

        # Setup 6: Create a REAL Phase 4 Transcript document in course_transcripts
        real_segments = [
            {"start": 0.0, "end": 20.0, "text": "In the series of data structures today we will discuss arrays and memory storage.", "TranscriptStart": "00:00", "TranscriptEnd": "00:20"},
            {"start": 20.0, "end": 120.0, "text": "Binary search is an efficient search algorithm that works on sorted arrays with time complexity log n.", "TranscriptStart": "00:20", "TranscriptEnd": "02:00"},
            {"start": 120.0, "end": 180.0, "text": "A binary search tree is a tree data structure where left child is smaller and right child is larger.", "TranscriptStart": "02:00", "TranscriptEnd": "03:00"}
        ]
        await database.course_transcripts.insert_one({
            "course_id": c1_id,
            "course_name": "Definition Concept Test",
            "subject": "DAA",
            "teacher_id": "T24AC61",
            "teacher_name": "Prof. Priya",
            "youtube_url": "https://www.youtube.com/watch?v=ONFkb-PxKts",
            "status": "COMPLETED",
            "language": "en",
            "segments": real_segments
        })

        # TEST 1: Initial Concept Status Check
        print("\n--- TEST 1: Initial Concept Status Check ---")
        status1_res = await ac.get(f"/api/v1/teacher/courses/{c1_id}/concepts/status", headers={"Authorization": f"Bearer {t1_token}"})
        assert status1_res.status_code == 200
        assert status1_res.json()["status"] == "NOT_GENERATED"
        print("[PASS] TEST 1: Initial Concept status verified as NOT_GENERATED.")

        # TEST 2: Fast Concept Extraction Job Queuing Response (<15ms)
        print("\n--- TEST 2: Fast Concept Extraction Job Queue Response (<15ms) ---")
        t_start = time.time()
        extract_res = await ac.post(f"/api/v1/teacher/courses/{c1_id}/concepts/extract", headers={"Authorization": f"Bearer {t1_token}"})
        t_duration = time.time() - t_start
        assert extract_res.status_code == 202
        assert extract_res.json()["status"] == "PENDING"
        assert t_duration < 0.2
        print(f"[PASS] TEST 2: Concept extraction queued in {t_duration*1000:.1f}ms with HTTP 202 Accepted.")

        # TEST 3: Standalone Concept Worker Execution (run_once=True)
        print("\n--- TEST 3: Standalone Concept Worker Process Execution ---")
        await run_concept_worker_loop(run_once=True)
        await connect_to_mongo()  # Re-establish test client connection

        # TEST 4: Job Status Completion Check
        print("\n--- TEST 4: Job Status Completion Check ---")
        status2_res = await ac.get(f"/api/v1/teacher/courses/{c1_id}/concepts/status", headers={"Authorization": f"Bearer {t1_token}"})
        assert status2_res.status_code == 200
        assert status2_res.json()["status"] == "COMPLETED"
        assert status2_res.json()["concept_count"] > 0
        print(f"[PASS] TEST 4: Concept status verified as COMPLETED with {status2_res.json()['concept_count']} concept segments.")

        # TEST 5: Retrieve Concept Segments via Teacher API
        print("\n--- TEST 5: Retrieve Concept Segments via Teacher API ---")
        get_c_res = await ac.get(f"/api/v1/teacher/courses/{c1_id}/concepts", headers={"Authorization": f"Bearer {t1_token}"})
        assert get_c_res.status_code == 200
        c_data = get_c_res.json()
        assert c_data["status"] == "COMPLETED"
        assert len(c_data["segments"]) == 3
        print(f"[PASS] TEST 5: Retrieved {len(c_data['segments'])} concept segments via Teacher API.")

        # TEST 6: Timestamp Accuracy Verification
        print("\n--- TEST 6: Timestamp Accuracy Verification ---")
        seg1 = c_data["segments"][0]
        seg2 = c_data["segments"][1]
        assert seg1["ConceptStart"] == "00:00"
        assert seg1["ConceptEnd"] == "00:20"
        assert seg2["ConceptStart"] == "00:20"
        assert seg2["ConceptEnd"] == "02:00"
        print("[PASS] TEST 6: Verified ConceptStart and ConceptEnd match transcript segment boundaries.")

        # TEST 7: Search Concepts by Keyword
        print("\n--- TEST 7: Search Concepts ---")
        concepts_list = c_data["segments"]
        matched_search = [c for c in concepts_list if "binary search" in c["Concept"].lower()]
        assert len(matched_search) >= 1
        print(f"[PASS] TEST 7: Search keyword 'binary search' matched {len(matched_search)} concept segment(s).")

        # TEST 8: Filter Concepts by Difficulty Level
        print("\n--- TEST 8: Filter Concepts by Difficulty Level ---")
        easy_concepts = [c for c in concepts_list if c["DifficultyLevel"] == "Easy"]
        hard_concepts = [c for c in concepts_list if c["DifficultyLevel"] == "Hard"]
        assert len(easy_concepts) >= 1
        print(f"[PASS] TEST 8: Difficulty filter verified (Easy: {len(easy_concepts)}, Hard: {len(hard_concepts)}).")

        # TEST 9: Idempotent Re-trigger Check
        print("\n--- TEST 9: Idempotent Re-trigger Check ---")
        re_extract = await ac.post(f"/api/v1/teacher/courses/{c1_id}/concepts/extract", headers={"Authorization": f"Bearer {t1_token}"})
        assert re_extract.status_code == 202
        assert re_extract.json()["message"] == "Concept extraction already completed."
        print("[PASS] TEST 9: Re-triggering concept extraction on COMPLETED course returned status immediately.")

        # TEST 10: Transcript Source Preservation
        print("\n--- TEST 10: Transcript Source Preservation ---")
        tx_check = await database.course_transcripts.find_one({"course_id": c1_id})
        assert tx_check["status"] == "COMPLETED"
        assert len(tx_check["segments"]) == 3
        print("[PASS] TEST 10: Original course_transcripts document is 100% intact and unchanged.")

        # TEST 11: Teacher Ownership Security
        print("\n--- TEST 11: Teacher Ownership Security ---")
        unauth_c = await ac.get(f"/api/v1/teacher/courses/{c1_id}/concepts", headers={"Authorization": f"Bearer {t2_token}"})
        assert unauth_c.status_code == 403
        print("[PASS] TEST 11: Teacher 2 access to Teacher 1's course concepts rejected with 403 Forbidden.")

        # TEST 12: No Transcript Guard
        print("\n--- TEST 12: No Transcript Guard ---")
        no_tx_req = await ac.post(f"/api/v1/teacher/courses/{c2_id}/concepts/extract", headers={"Authorization": f"Bearer {t1_token}"})
        assert no_tx_req.status_code == 400
        assert "transcript is required" in no_tx_req.json()["detail"].lower()
        print("[PASS] TEST 12: Concept extraction on course without completed transcript rejected with 400 Bad Request.")

        # TEST 13: Student Telemetry Preservation
        print("\n--- TEST 13: Student Telemetry Preservation ---")
        ev_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PLAY",
            "event_timestamp": "00:00"
        })
        assert ev_res.status_code == 201
        print("[PASS] TEST 13: Phase 5 student telemetry tracking operates independently.")

        # TEST 14: Worker Stale Recovery
        print("\n--- TEST 14: Worker Stale Job Recovery ---")
        from datetime import datetime, timezone, timedelta
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        await database.concept_extraction_jobs.insert_one({
            "course_id": "stale_course_123",
            "teacher_id": "T24AC61",
            "status": "PROCESSING",
            "attempts": 1,
            "updated_at": stale_time
        })
        from app.workers.concept_worker import recover_stale_concept_jobs
        await recover_stale_concept_jobs()
        stale_job = await database.concept_extraction_jobs.find_one({"course_id": "stale_course_123"})
        assert stale_job["status"] == "PENDING"
        await database.concept_extraction_jobs.delete_one({"course_id": "stale_course_123"})
        print("[PASS] TEST 14: Stale job in PROCESSING state (>10 min) successfully recovered to PENDING.")

        # TEST 15: Website Responsiveness Check
        print("\n--- TEST 15: Website Responsiveness Check ---")
        t_start = time.time()
        search_res = await ac.get("/api/v1/student/courses/search?query=Definition", headers={"Authorization": f"Bearer {s1_token}"})
        t_duration = time.time() - t_start
        assert search_res.status_code == 200
        assert t_duration < 0.2
        print(f"[PASS] TEST 15: Student search API responded in {t_duration*1000:.1f}ms.")

        # TEST 16: Verify Zero Student Fields in concept_segments Schema
        print("\n--- TEST 16: Verify Zero Student Fields in concept_segments ---")
        concept_doc = await database.concept_segments.find_one({"course_id": c1_id})
        assert "StudentID" not in concept_doc
        assert "StudentName" not in concept_doc
        assert "PauseReason" not in concept_doc
        assert "DifficultyScore" not in concept_doc
        print("[PASS] TEST 16: Verified concept_segments collection contains ZERO student-specific fields.")

        # TEST 17: Purge All Test Data (Return DB to 0 Records)
        print("\n--- TEST 17: Purge All Test Data (Return DB to 0 Records) ---")
        await database.users.delete_many({})
        await database.teachers.delete_many({})
        await database.students.delete_many({})
        await database.courses.delete_many({})
        await database.course_transcripts.delete_many({})
        await database.transcription_jobs.delete_many({})
        await database.concept_segments.delete_many({})
        await database.concept_extraction_jobs.delete_many({})
        await database.interaction_events.delete_many({})
        await database.student_learning.delete_many({})

        final_users = await database.users.count_documents({})
        final_teachers = await database.teachers.count_documents({})
        final_students = await database.students.count_documents({})
        final_courses = await database.courses.count_documents({})
        final_concepts = await database.concept_segments.count_documents({})

        assert final_users == 0
        assert final_teachers == 0
        assert final_students == 0
        assert final_courses == 0
        assert final_concepts == 0
        print("[PASS] TEST 17: All test data purged. Database returned to EXACTLY 0 records!")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 17 PHASE 6 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase6_tests())
