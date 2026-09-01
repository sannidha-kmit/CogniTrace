import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import asyncio
import sys
import logging
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db

logging.basicConfig(level=logging.INFO)


async def run_phase4_tests():
    print("=" * 60)
    print("STARTING PHASE 4 FASTER-WHISPER TRANSCRIPT VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records if present
    test_ids = ["T24A101", "T24A102", "S24A101", "S24A102"]
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.course_transcripts.delete_many({"teacher_id": {"$in": test_ids}})
    await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})
    await database.student_learning.delete_many({"StudentID": {"$in": test_ids}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # Setup 1: Register Teacher 1 (Nidhi - 2nd Year - DAA)
        t1_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A101",
            "name": "Prof. Nidhi",
            "year": "2nd Year",
            "subject": "DAA",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t1_res.status_code == 201
        t1_token = t1_res.json()["access_token"]

        # Setup 2: Register Teacher 2 (Rahul - 2nd Year - OS)
        t2_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A102",
            "name": "Prof. Rahul",
            "year": "2nd Year",
            "subject": "Operating Systems",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t2_res.status_code == 201
        t2_token = t2_res.json()["access_token"]

        # Setup 3: Register Student 1 & Student 2
        s1_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A101",
            "name": "Student A",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s1_res.status_code == 201
        s1_token = s1_res.json()["access_token"]

        s2_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A102",
            "name": "Student B",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s2_res.status_code == 201
        s2_token = s2_res.json()["access_token"]

        # TEST 1: Create Real Course with YouTube Video
        print("\n--- TEST 1: Create Real Course ---")
        c1_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Recursion Fundamentals",
            "youtube_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        })
        assert c1_res.status_code == 201
        c1_id = c1_res.json()["id"]
        print(f"[PASS] TEST 1: Course 'Recursion Fundamentals' created with ID {c1_id}.")

        # TEST 2: Initiate Transcript Generation & Poll Status
        print("\n--- TEST 2: Initiate Transcript Generation & Poll Status ---")
        gen_res = await ac.post(f"/api/v1/teacher/courses/{c1_id}/transcript/generate", headers={"Authorization": f"Bearer {t1_token}"})
        assert gen_res.status_code == 202
        assert gen_res.json()["status"] in ["PROCESSING", "PENDING", "COMPLETED"]

        # Poll status until COMPLETED or FAILED
        max_retries = 30
        completed = False
        for i in range(max_retries):
            await asyncio.sleep(1.0)
            st_res = await ac.get(f"/api/v1/teacher/courses/{c1_id}/transcript/status", headers={"Authorization": f"Bearer {t1_token}"})
            assert st_res.status_code == 200
            st_data = st_res.json()
            print(f"Polling status (attempt {i+1}): {st_data['status']}")
            if st_data["status"] == "COMPLETED":
                completed = True
                break
            elif st_data["status"] == "FAILED":
                print(f"Job failed with error: {st_data.get('error_message')}")
                break

        assert completed, "Transcript generation did not complete in time."
        print("[PASS] TEST 2: Transcript generation status transitioned to COMPLETED.")

        # TEST 3 & 4: Retrieve Timestamped Transcript & Validate Segments
        print("\n--- TEST 3 & 4: Retrieve & Validate Timestamped Transcript Segments ---")
        tx_res = await ac.get(f"/api/v1/teacher/courses/{c1_id}/transcript", headers={"Authorization": f"Bearer {t1_token}"})
        assert tx_res.status_code == 200
        tx_data = tx_res.json()
        assert tx_data["course_name"] == "Recursion Fundamentals"
        assert tx_data["subject"] == "DAA"
        assert len(tx_data["segments"]) > 0
        first_seg = tx_data["segments"][0]
        assert "start" in first_seg
        assert "end" in first_seg
        assert "text" in first_seg
        assert "TranscriptStart" in first_seg
        assert "TranscriptEnd" in first_seg
        print(f"[PASS] TEST 3 & 4: Retrieved {len(tx_data['segments'])} timestamped segments (First: {first_seg['TranscriptStart']} - {first_seg['TranscriptEnd']}: '{first_seg['text'][:30]}...').")

        # TEST 5: Check MongoDB Document Uniqueness
        print("\n--- TEST 5: MongoDB 1-to-1 Document Uniqueness ---")
        doc_count = await database.course_transcripts.count_documents({"course_id": c1_id})
        assert doc_count == 1
        print("[PASS] TEST 5: Verified exactly ONE transcript document exists for Course 1 in MongoDB.")

        # TEST 6 & 7 & 8: Re-trigger Generation on Completed Course (Idempotency)
        print("\n--- TEST 6, 7, 8: Re-trigger Generation Idempotency ---")
        gen_res2 = await ac.post(f"/api/v1/teacher/courses/{c1_id}/transcript/generate", headers={"Authorization": f"Bearer {t1_token}"})
        assert gen_res2.status_code == 202
        assert gen_res2.json()["message"] == "Transcript already generated."
        
        # Verify count still 1
        doc_count2 = await database.course_transcripts.count_documents({"course_id": c1_id})
        assert doc_count2 == 1
        print("[PASS] TEST 6, 7, 8: Repeated generation request reused existing transcript document without duplicate job execution.")

        # TEST 9 & 10: Teacher Access Isolation (Teacher 2 Cannot Access Teacher 1's Transcript)
        print("\n--- TEST 9 & 10: Teacher Ownership Access Isolation ---")
        unauth_tx = await ac.get(f"/api/v1/teacher/courses/{c1_id}/transcript", headers={"Authorization": f"Bearer {t2_token}"})
        assert unauth_tx.status_code == 403
        assert "access denied" in unauth_tx.json()["detail"].lower()

        unauth_gen = await ac.post(f"/api/v1/teacher/courses/{c1_id}/transcript/generate", headers={"Authorization": f"Bearer {t2_token}"})
        assert unauth_gen.status_code == 403
        print("[PASS] TEST 9 & 10: Teacher 2 access to Teacher 1's transcript rejected with 403 Forbidden.")

        # TEST 11 & 12: Create Course 2 and Verify Separate Transcript Document
        print("\n--- TEST 11 & 12: Course 2 Separate Transcript Document ---")
        c2_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Binary Search Operations",
            "youtube_url": "https://www.youtube.com/watch?v=2lAe1cqCOXo"
        })
        assert c2_res.status_code == 201
        c2_id = c2_res.json()["id"]

        gen_c2 = await ac.post(f"/api/v1/teacher/courses/{c2_id}/transcript/generate", headers={"Authorization": f"Bearer {t1_token}"})
        assert gen_c2.status_code == 202

        # Poll Course 2 completion
        for _ in range(30):
            await asyncio.sleep(1.0)
            st = await ac.get(f"/api/v1/teacher/courses/{c2_id}/transcript/status", headers={"Authorization": f"Bearer {t1_token}"})
            if st.json()["status"] in ["COMPLETED", "FAILED"]:
                break

        total_tx_docs = await database.course_transcripts.count_documents({"teacher_id": "T24A101"})
        assert total_tx_docs == 2
        print(f"[PASS] TEST 11 & 12: Verified Course 1 and Course 2 have 2 distinct transcript documents (1 per course).")

        # TEST 13 & 14: Failed Transcription Handling & Retry
        print("\n--- TEST 13 & 14: Failed Job Handling & Controlled Retry ---")
        # Create course with bad YouTube URL structure
        c_bad = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Bad URL Course",
            "youtube_url": "https://www.youtube.com/watch?v=invalid_id_99999"
        })
        assert c_bad.status_code == 201
        c_bad_id = c_bad.json()["id"]

        await ac.post(f"/api/v1/teacher/courses/{c_bad_id}/transcript/generate", headers={"Authorization": f"Bearer {t1_token}"})
        
        # Wait for fail
        for _ in range(15):
            await asyncio.sleep(1.0)
            st_b = await ac.get(f"/api/v1/teacher/courses/{c_bad_id}/transcript/status", headers={"Authorization": f"Bearer {t1_token}"})
            if st_b.json()["status"] == "FAILED":
                break

        st_b_data = (await ac.get(f"/api/v1/teacher/courses/{c_bad_id}/transcript/status", headers={"Authorization": f"Bearer {t1_token}"})).json()
        assert st_b_data["status"] == "FAILED"
        assert st_b_data["error_message"] is not None

        # Controlled retry
        regen_res = await ac.post(f"/api/v1/teacher/courses/{c_bad_id}/transcript/regenerate", headers={"Authorization": f"Bearer {t1_token}"})
        assert regen_res.status_code == 202
        assert regen_res.json()["status"] == "PROCESSING"
        print("[PASS] TEST 13 & 14: Failed transcription handled gracefully with safe error status; retry initiated successfully.")

        # TEST 15 & 16 & 17: Multiple Students Watching Same Course (Zero Transcript Duplication)
        print("\n--- TEST 15, 16, 17: Multi-Student Course Watching & Telemetry Integration ---")
        ev1 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PLAY",
            "event_timestamp": "00:10"
        })
        assert ev1.status_code == 201

        ev2 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s2_token}"}, json={
            "course_id": c1_id,
            "event_type": "PAUSE",
            "event_timestamp": "02:15",
            "event_duration": 10.0,
            "pause_reason": "Taking notes"
        })
        assert ev2.status_code == 201

        # Verify student interaction events recorded separately
        s1_events = await database.interaction_events.count_documents({"StudentID": "S24A101"})
        s2_events = await database.interaction_events.count_documents({"StudentID": "S24A102"})
        assert s1_events == 1
        assert s2_events == 1

        # Verify course transcripts count is STILL 1 for Course 1 (Students didn't create duplicate transcripts!)
        c1_tx_count = await database.course_transcripts.count_documents({"course_id": c1_id})
        assert c1_tx_count == 1
        print("[PASS] TEST 15, 16, 17: Multi-student views recorded separate interaction events while reusing the single course transcript document.")

        # TEST 18: Research Dataset Fields Verification
        print("\n--- TEST 18: Research Dataset Fields Schema Check ---")
        sample_tx = await database.course_transcripts.find_one({"course_id": c1_id})
        assert "course_name" in sample_tx
        assert "subject" in sample_tx
        assert "segments" in sample_tx
        seg_0 = sample_tx["segments"][0]
        assert "TranscriptStart" in seg_0
        assert "TranscriptEnd" in seg_0
        assert "text" in seg_0
        # Verify research dataset does NOT contain student-specific columns
        assert "StudentID" not in sample_tx
        assert "StudentName" not in sample_tx
        print("[PASS] TEST 18: Research dataset fields schema verified (No student-specific columns in transcripts).")

        # TEST 19: Test Data Cleanup (Purge all test records to return DB to 0 records)
        print("\n--- TEST 19: Purge All Test Records (Return DB to 0 Records) ---")
        await database.users.delete_many({})
        await database.teachers.delete_many({})
        await database.students.delete_many({})
        await database.courses.delete_many({})
        await database.course_transcripts.delete_many({})
        await database.interaction_events.delete_many({})
        await database.student_learning.delete_many({})

        final_users = await database.users.count_documents({})
        final_teachers = await database.teachers.count_documents({})
        final_students = await database.students.count_documents({})
        final_courses = await database.courses.count_documents({})
        final_txs = await database.course_transcripts.count_documents({})
        final_events = await database.interaction_events.count_documents({})

        assert final_users == 0
        assert final_teachers == 0
        assert final_students == 0
        assert final_courses == 0
        assert final_txs == 0
        assert final_events == 0
        print("[PASS] TEST 19: All test data purged. Database returned to EXACTLY 0 records!")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 19 PHASE 4 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase4_tests())
