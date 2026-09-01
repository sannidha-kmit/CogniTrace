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


async def run_phase5_tests():
    print("=" * 60)
    print("STARTING PHASE 5 TEACHER DATASET VIEWER & ISOLATION VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24A301", "T24A302", "T24A303", "S24A301", "S24A302", "S24A303"]
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

        # Setup 1: Register Teacher Priya (T24A301 - 2nd Year - Operating Systems)
        t_priya_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A301",
            "name": "Prof. Priya",
            "year": "2nd Year",
            "subject": "Operating Systems",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t_priya_res.status_code == 201
        priya_token = t_priya_res.json()["access_token"]

        # Setup 2: Register Teacher Ravi (T24A302 - 2nd Year - Web Technologies)
        t_ravi_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A302",
            "name": "Prof. Ravi",
            "year": "2nd Year",
            "subject": "Web Technologies",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t_ravi_res.status_code == 201
        ravi_token = t_ravi_res.json()["access_token"]

        # Setup 3: Register Teacher Kumar (T24A303 - 3rd Year - DAA)
        t_kumar_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A303",
            "name": "Prof. Kumar",
            "year": "3rd Year",
            "subject": "DAA",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t_kumar_res.status_code == 201
        kumar_token = t_kumar_res.json()["access_token"]

        # Setup 4: Register Student Lasya (S24A301 - 2nd Year)
        s_lasya_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A301",
            "name": "Lasya",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s_lasya_res.status_code == 201
        lasya_token = s_lasya_res.json()["access_token"]

        # Setup 5: Register Student Rahul (S24A302 - 2nd Year)
        s_rahul_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A302",
            "name": "Rahul",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s_rahul_res.status_code == 201
        rahul_token = s_rahul_res.json()["access_token"]

        # Setup 6: Register Student 3rd Year (S24A303 - 3rd Year)
        s_3rd_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A303",
            "name": "3rd Year Student",
            "year": "3rd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s_3rd_res.status_code == 201

        # Setup 7: Create Course for Priya (Process Management)
        c_priya_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {priya_token}"}, json={
            "course_name": "Process Management",
            "youtube_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        })
        assert c_priya_res.status_code == 201
        c_priya_id = c_priya_res.json()["id"]

        # Setup 8: Create Course for Ravi (HTML Basics)
        c_ravi_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {ravi_token}"}, json={
            "course_name": "HTML Basics",
            "youtube_url": "https://www.youtube.com/watch?v=2lAe1cqCOXo"
        })
        assert c_ravi_res.status_code == 201
        c_ravi_id = c_ravi_res.json()["id"]

        # TEST 1: Record Real Interaction Telemetry for Lasya on Priya's Course
        print("\n--- TEST 1: Record Real Interaction Events for Priya's Course ---")
        ev1 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {lasya_token}"}, json={
            "course_id": c_priya_id,
            "event_type": "PLAY",
            "event_timestamp": "00:05"
        })
        assert ev1.status_code == 201

        ev2 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {lasya_token}"}, json={
            "course_id": c_priya_id,
            "event_type": "PAUSE",
            "event_timestamp": "02:15",
            "event_duration": 12.0,
            "pause_reason": "Trying to understand concept"
        })
        assert ev2.status_code == 201
        print("[PASS] TEST 1: Lasya's interaction telemetry recorded for Priya's course.")

        # TEST 2: Teacher Priya Views Student Lasya's Interaction Dataset
        print("\n--- TEST 2: Teacher Priya Dataset Viewer ---")
        priya_view = await ac.get("/api/v1/teacher/students/S24A301/interactions", headers={"Authorization": f"Bearer {priya_token}"})
        assert priya_view.status_code == 200
        priya_events = priya_view.json()
        assert len(priya_events) == 2
        assert priya_events[0]["CourseSubject"] == "Operating Systems"
        assert priya_events[0]["CourseName"] == "Process Management"
        print("[PASS] TEST 2: Teacher Priya sees Lasya's 2 interaction events for Operating Systems.")

        # TEST 3: Teacher Ravi Views Student Lasya (Strict Isolation Check)
        print("\n--- TEST 3: Teacher Ravi Subject Isolation (Cannot see Priya's Course Events) ---")
        ravi_view = await ac.get("/api/v1/teacher/students/S24A301/interactions", headers={"Authorization": f"Bearer {ravi_token}"})
        assert ravi_view.status_code == 200
        ravi_events = ravi_view.json()
        assert len(ravi_events) == 0  # Ravi sees ZERO events for Priya's Operating Systems course!
        print("[PASS] TEST 3: Verified Teacher Ravi sees 0 events for Priya's Operating Systems course.")

        # TEST 4: Student Lasya Watches Ravi's Course (HTML Basics) & Verification
        print("\n--- TEST 4: Student Lasya Watches Ravi's Course ---")
        ev3 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {lasya_token}"}, json={
            "course_id": c_ravi_id,
            "event_type": "PAUSE",
            "event_timestamp": "01:10",
            "event_duration": 5.0,
            "pause_reason": "Taking notes"
        })
        assert ev3.status_code == 201

        # Now Ravi views Lasya -> Should see 1 event for HTML Basics
        ravi_view2 = await ac.get("/api/v1/teacher/students/S24A301/interactions", headers={"Authorization": f"Bearer {ravi_token}"})
        assert ravi_view2.status_code == 200
        assert len(ravi_view2.json()) == 1
        assert ravi_view2.json()[0]["CourseSubject"] == "Web Technologies"

        # Priya views Lasya again -> Should STILL see ONLY 2 events for Operating Systems!
        priya_view2 = await ac.get("/api/v1/teacher/students/S24A301/interactions", headers={"Authorization": f"Bearer {priya_token}"})
        assert priya_view2.status_code == 200
        assert len(priya_view2.json()) == 2
        print("[PASS] TEST 4: Multi-teacher subject data isolation verified on backend.")

        # TEST 5 & 6: Cross-Year Student Access & Direct URL Rejection
        print("\n--- TEST 5 & 6: Unauthorized Student / Year Access Rejection ---")
        unauth_student = await ac.get("/api/v1/teacher/students/S24A303/interactions", headers={"Authorization": f"Bearer {priya_token}"})
        assert unauth_student.status_code == 403
        assert "access denied" in unauth_student.json()["detail"].lower()
        print("[PASS] TEST 5 & 6: Access to 3rd Year student by 2nd Year teacher rejected with 403 Forbidden.")

        # TEST 7: Filter Dataset by Specific Course ID
        print("\n--- TEST 7: Filter Dataset by Course ID ---")
        c_filter = await ac.get(f"/api/v1/teacher/students/S24A301/interactions?course_id={c_priya_id}", headers={"Authorization": f"Bearer {priya_token}"})
        assert c_filter.status_code == 200
        assert len(c_filter.json()) == 2
        print("[PASS] TEST 7: Filter dataset by course ID returned matching events.")

        # TEST 8: Filter Dataset by Event Type (PAUSE)
        print("\n--- TEST 8: Filter Dataset by Event Type ---")
        e_filter = await ac.get(f"/api/v1/teacher/students/S24A301/interactions?event_type=PAUSE", headers={"Authorization": f"Bearer {priya_token}"})
        assert e_filter.status_code == 200
        assert len(e_filter.json()) == 1
        assert e_filter.json()[0]["EventType"] == "PAUSE"
        print("[PASS] TEST 8: Filter dataset by event_type=PAUSE returned only PAUSE events.")

        # TEST 9: Transcript Connection Link Verification
        print("\n--- TEST 9: Transcript Connection Link Verification ---")
        # Ensure Phase 4 transcript API endpoint responds for authorized course
        tx_status = await ac.get(f"/api/v1/teacher/courses/{c_priya_id}/transcript/status", headers={"Authorization": f"Bearer {priya_token}"})
        assert tx_status.status_code == 200
        print("[PASS] TEST 9: Transcript connection link verified without triggering Faster-Whisper jobs.")

        # TEST 10: Multi-Student Interaction Tracking for Same Course
        print("\n--- TEST 10: Multi-Student Interaction Tracking for Same Course ---")
        ev_rahul = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {rahul_token}"}, json={
            "course_id": c_priya_id,
            "event_type": "PLAY",
            "event_timestamp": "00:00"
        })
        assert ev_rahul.status_code == 201

        priya_rahul = await ac.get("/api/v1/teacher/students/S24A302/interactions", headers={"Authorization": f"Bearer {priya_token}"})
        assert priya_rahul.status_code == 200
        assert len(priya_rahul.json()) == 1
        assert priya_rahul.json()[0]["StudentID"] == "S24A302"
        print("[PASS] TEST 10: Student B interaction telemetry tracked independently for same course.")

        # TEST 11: Empty State Handling for Student with 0 Interactions
        print("\n--- TEST 11: Empty State Handling ---")
        empty_res = await ac.get("/api/v1/teacher/students/S24A303/interactions", headers={"Authorization": f"Bearer {kumar_token}"})
        assert empty_res.status_code == 200
        assert len(empty_res.json()) == 0
        print("[PASS] TEST 11: Student with 0 interactions returned empty list [] cleanly.")

        # TEST 12: Test Data Cleanup (Purge All Test Records)
        print("\n--- TEST 12: Purge All Test Data (Return DB to 0 Records) ---")
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
        final_events = await database.interaction_events.count_documents({})

        assert final_users == 0
        assert final_teachers == 0
        assert final_students == 0
        assert final_courses == 0
        assert final_events == 0
        print("[PASS] TEST 12: All test data purged. Database returned to EXACTLY 0 records!")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 12 PHASE 5 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase5_tests())
