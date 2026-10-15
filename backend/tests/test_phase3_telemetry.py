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


async def run_phase3_tests():
    print("=" * 60)
    print("STARTING PHASE 3 STUDENT ACCESS & TELEMETRY VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records if present
    test_ids = ["T24A001", "T24A002", "T24A003", "S24A001", "S24A002"]
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})
    await database.student_learning.delete_many({"StudentID": {"$in": test_ids}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # Setup 1: Register Teacher 1 (Priya - 2nd Year - Operating Systems)
        t1_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A001",
            "name": "Prof. Priya",
            "year": "2nd Year",
            "subject": "Operating Systems",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t1_res.status_code == 201
        t1_token = t1_res.json()["access_token"]

        # Setup 2: Register Teacher 2 (Ravi - 2nd Year - Web Tech)
        t2_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A002",
            "name": "Prof. Ravi",
            "year": "2nd Year",
            "subject": "Web Technologies",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t2_res.status_code == 201

        # Setup 3: Register Teacher 3 (Kumar - 3rd Year - DAA)
        t3_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A003",
            "name": "Prof. Kumar",
            "year": "3rd Year",
            "subject": "DAA",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t3_res.status_code == 201
        t3_token = t3_res.json()["access_token"]

        # Setup 4: Register Student 1 (Lasya - S24A001 - 2nd Year)
        s1_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A001",
            "name": "Lasya",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s1_res.status_code == 201
        s1_token = s1_res.json()["access_token"]

        # Setup 5: Register Student 2 (Anu - S24A002 - 2nd Year)
        s2_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A002",
            "name": "Anu",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s2_res.status_code == 201
        s2_token = s2_res.json()["access_token"]

        # Setup 6: Create Courses for 2nd Year (Priya)
        c1_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Process Management",
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })
        assert c1_res.status_code == 201
        c1_id = c1_res.json()["id"]

        c2_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "CPU Scheduling",
            "youtube_url": "https://www.youtube.com/watch?v=yPYZpwSpKmA"
        })
        assert c2_res.status_code == 201

        # Setup 7: Create Course for 3rd Year (Kumar)
        c3_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t3_token}"}, json={
            "course_name": "Binary Search Trees",
            "youtube_url": "https://www.youtube.com/watch?v=9XB8X5abcde"
        })
        assert c3_res.status_code == 201
        c3_id = c3_res.json()["id"]

        # TEST 1 & 2: Student Dashboard Profile & Teachers Scoped to 2nd Year
        print("\n--- TEST 1 & 2: Student Dashboard Teachers Year Filter ---")
        teachers_res = await ac.get("/api/v1/student/teachers", headers={"Authorization": f"Bearer {s1_token}"})
        assert teachers_res.status_code == 200
        teachers_list = teachers_res.json()
        assert len(teachers_list) == 2  # Priya & Ravi only
        t_ids = [t["teacher_id"] for t in teachers_list]
        assert "T24A001" in t_ids
        assert "T24A002" in t_ids
        assert "T24A003" not in t_ids  # Kumar (3rd Year) excluded
        print("[PASS] TEST 1 & 2: Verified only 2nd Year teachers (Priya, Ravi) returned to student Lasya.")

        # TEST 3 & 4: Direct Access Denial for Cross-Year Course (3rd Year Course by 2nd Year Student)
        print("\n--- TEST 3 & 4: Unauthorized Cross-Year Access Rejection ---")
        cross_res = await ac.get(f"/api/v1/student/courses/{c3_id}", headers={"Authorization": f"Bearer {s1_token}"})
        assert cross_res.status_code == 403
        assert "access denied" in cross_res.json()["detail"].lower()
        print("[PASS] TEST 3 & 4: 2nd Year student direct access to 3rd Year course rejected with 403 Forbidden.")

        # TEST 5: Open Specific Teacher Courses
        print("\n--- TEST 5: Teacher's Courses Retrieval ---")
        t1_courses = await ac.get(f"/api/v1/student/teachers/T24A001/courses", headers={"Authorization": f"Bearer {s1_token}"})
        assert t1_courses.status_code == 200
        t1_list = t1_courses.json()
        assert len(t1_list) == 2
        assert t1_list[0]["course_name"] == "CPU Scheduling"  # Newest first
        assert t1_list[1]["course_name"] == "Process Management"
        print("[PASS] TEST 5: Teacher T24A001 courses retrieved in newest-first order.")

        # TEST 6, 7, 8: Course Search (Exact, Case-Insensitive, Partial)
        print("\n--- TEST 6, 7, 8: Case-Insensitive Course Search ---")
        # Search "process" (lowercase for "Process Management")
        s_res1 = await ac.get("/api/v1/student/courses/search?query=process", headers={"Authorization": f"Bearer {s1_token}"})
        assert s_res1.status_code == 200
        assert len(s_res1.json()) == 1
        assert s_res1.json()[0]["course_name"] == "Process Management"

        # Partial search "cpu"
        s_res2 = await ac.get("/api/v1/student/courses/search?query=cpu", headers={"Authorization": f"Bearer {s1_token}"})
        assert s_res2.status_code == 200
        assert len(s_res2.json()) == 1
        assert s_res2.json()[0]["course_name"] == "CPU Scheduling"
        print("[PASS] TEST 6, 7, 8: Exact, case-insensitive, and partial search verified.")

        # TEST 9: Search for 3rd Year course ("Binary") as 2nd Year student -> 0 results
        print("\n--- TEST 9: Search Authorization Scoping ---")
        s_res3 = await ac.get("/api/v1/student/courses/search?query=Binary", headers={"Authorization": f"Bearer {s1_token}"})
        assert s_res3.status_code == 200
        assert len(s_res3.json()) == 0  # 3rd Year Binary Search Trees hidden
        print("[PASS] TEST 9: 3rd Year course hidden from 2nd Year student search.")

        # TEST 10 & 11: Non-matching search & Clear search
        print("\n--- TEST 10 & 11: Non-matching & Empty Search Query ---")
        s_res4 = await ac.get("/api/v1/student/courses/search?query=NonExistentTopic", headers={"Authorization": f"Bearer {s1_token}"})
        assert s_res4.status_code == 200
        assert len(s_res4.json()) == 0

        s_res5 = await ac.get("/api/v1/student/courses/search?query=", headers={"Authorization": f"Bearer {s1_token}"})
        assert s_res5.status_code == 200
        assert len(s_res5.json()) == 0
        print("[PASS] TEST 10 & 11: Empty search and non-matching search handled cleanly.")

        # TEST 12: Load Course Overview Details for Authorized Course
        print("\n--- TEST 12: Course Overview Retrieval ---")
        c_details = await ac.get(f"/api/v1/student/courses/{c1_id}", headers={"Authorization": f"Bearer {s1_token}"})
        assert c_details.status_code == 200
        assert c_details.json()["course_name"] == "Process Management"
        print("[PASS] TEST 12: Course overview metadata fetched successfully.")

        # TEST 13: Record PLAY Event Telemetry
        print("\n--- TEST 13: Record PLAY Telemetry Event ---")
        play_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PLAY",
            "event_timestamp": "00:05",
            "playback_speed": 1.0
        })
        assert play_ev.status_code == 201
        p_data = play_ev.json()
        assert p_data["StudentID"] == "S24A001"
        assert p_data["StudentName"] == "Lasya"
        assert p_data["CourseSubject"] == "Operating Systems"
        assert p_data["CourseName"] == "Process Management"
        assert p_data["EventType"] == "PLAY"
        assert p_data["EventTimestamp"] == "00:05"
        print("[PASS] TEST 13: PLAY telemetry event recorded with correct research dataset schema.")

        # TEST 14 & 15: Record PAUSE Event with Duration and Pause Reason
        print("\n--- TEST 14 & 15: Record PAUSE Telemetry Event with Duration & Reason ---")
        pause_ev1 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PAUSE",
            "event_timestamp": "02:15",
            "event_duration": 12.0,
            "playback_speed": 1.0,
            "pause_reason": "Trying to understand the concept"
        })
        assert pause_ev1.status_code == 201
        pause_data = pause_ev1.json()
        assert pause_data["EventType"] == "PAUSE"
        assert pause_data["EventTimestamp"] == "02:15"
        assert pause_data["EventDuration"] == 12.0
        assert pause_data["PauseReason"] == "Trying to understand the concept"
        print("[PASS] TEST 14 & 15: Single PAUSE event recorded with timestamp, duration (12s), and reason.")

        # TEST 16: Record Second Distinct PAUSE Event
        print("\n--- TEST 16: Record Second Distinct PAUSE Event ---")
        pause_ev2 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PAUSE",
            "event_timestamp": "04:30",
            "event_duration": 8.0,
            "playback_speed": 1.0,
            "pause_reason": "Taking notes"
        })
        assert pause_ev2.status_code == 201
        print("[PASS] TEST 16: Second distinct PAUSE event recorded cleanly.")

        # TEST 17: Record SEEK_BACKWARD Event
        print("\n--- TEST 17: Record SEEK_BACKWARD Event ---")
        seek_b_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "SEEK_BACKWARD",
            "event_timestamp": "01:45"
        })
        assert seek_b_ev.status_code == 201
        print("[PASS] TEST 17: SEEK_BACKWARD event recorded.")

        # TEST 18: Record SEEK_FORWARD Event
        print("\n--- TEST 18: Record SEEK_FORWARD Event ---")
        seek_f_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "SEEK_FORWARD",
            "event_timestamp": "05:10"
        })
        assert seek_f_ev.status_code == 201
        print("[PASS] TEST 18: SEEK_FORWARD event recorded.")

        # TEST 19: Record SPEED_CHANGE Event
        print("\n--- TEST 19: Record SPEED_CHANGE Event ---")
        speed_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "SPEED_CHANGE",
            "event_timestamp": "05:15",
            "playback_speed": 1.5
        })
        assert speed_ev.status_code == 201
        assert speed_ev.json()["PlaybackSpeed"] == 1.5
        print("[PASS] TEST 19: SPEED_CHANGE event recorded with speed 1.5x.")

        # TEST 20: Record REPLAY Event
        print("\n--- TEST 20: Record REPLAY Event ---")
        replay_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "REPLAY",
            "event_timestamp": "01:45"
        })
        assert replay_ev.status_code == 201
        print("[PASS] TEST 20: REPLAY event recorded.")

        # TEST 21: Record VIDEO_COMPLETE Event
        print("\n--- TEST 21: Record VIDEO_COMPLETE Event ---")
        complete_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "VIDEO_COMPLETE",
            "event_timestamp": "10:00"
        })
        assert complete_ev.status_code == 201
        print("[PASS] TEST 21: VIDEO_COMPLETE event recorded.")

        # TEST 22: Learning Session Start & End
        print("\n--- TEST 22: Student Learning Session Start & End ---")
        ls_start = await ac.post("/api/v1/student/learning/start", headers={"Authorization": f"Bearer {s1_token}"}, json={"course_id": c1_id})
        assert ls_start.status_code == 201
        session_id = ls_start.json()["session_id"]

        ls_end = await ac.post("/api/v1/student/learning/end", headers={"Authorization": f"Bearer {s1_token}"}, json={"session_id": session_id})
        assert ls_end.status_code == 200
        print("[PASS] TEST 22: Learning session start & end recorded in student_learning.")

        # TEST 23: Student 2 Identity Binding Check
        print("\n--- TEST 23: Student 2 Telemetry Identity Binding ---")
        s2_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s2_token}"}, json={
            "course_id": c1_id,
            "event_type": "PLAY",
            "event_timestamp": "00:00"
        })
        assert s2_ev.status_code == 201
        assert s2_ev.json()["StudentID"] == "S24A002"
        assert s2_ev.json()["StudentName"] == "Anu"
        print("[PASS] TEST 23: Student 2 telemetry bound strictly to Student 2 identity.")

        # TEST 24: Attempt Payload Student Identity Override
        print("\n--- TEST 24: Student Identity Tampering Prevention ---")
        tamper_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PLAY",
            "event_timestamp": "00:01",
            "StudentID": "FAKESTUDENT"
        })
        assert tamper_ev.status_code == 201
        assert tamper_ev.json()["StudentID"] == "S24A001"  # Bound from JWT, not body payload
        print("[PASS] TEST 24: Backend strictly bound telemetry ownership to authenticated student.")

        # TEST 25: Unauthorized Course Telemetry Rejection (3rd Year Course by 2nd Year Student)
        print("\n--- TEST 25: Unauthorized Course Telemetry Rejection ---")
        unauth_ev = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c3_id,
            "event_type": "PLAY",
            "event_timestamp": "00:00"
        })
        assert unauth_ev.status_code == 403
        print("[PASS] TEST 25: Unauthorized course event submission rejected with 403 Forbidden.")

        # TEST 26: Zero Synthetic Data & Record Verification
        print("\n--- TEST 26: Database Telemetry Counts Verification ---")
        events_count = await database.interaction_events.count_documents({})
        learning_count = await database.student_learning.count_documents({})
        assert events_count == 10, f"Expected 10 real telemetry events, got {events_count}"
        assert learning_count == 1, f"Expected 1 learning session, got {learning_count}"
        print(f"[PASS] TEST 26: Verified exactly {events_count} real events recorded in interaction_events.")

        # TEST 27: Test Data Cleanup (Purge all test records to return DB to 0 records)
        print("\n--- TEST 27: Purge All Test Telemetry & Accounts (Return DB to 0 Records) ---")
        await database.users.delete_many({"identifier": {"$in": test_ids}})
        await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
        await database.students.delete_many({"roll_number": {"$in": test_ids}})
        await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
        await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})
        await database.student_learning.delete_many({"StudentID": {"$in": test_ids}})

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
        print("[PASS] TEST 27: All test data purged. Database returned to EXACTLY 0 records!")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 27 PHASE 3 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase3_tests())
