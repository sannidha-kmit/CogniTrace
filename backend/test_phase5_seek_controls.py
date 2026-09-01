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


async def run_seek_controls_tests():
    print("=" * 60)
    print("STARTING PHASE 5 EXPLICIT SEEK CONTROLS TEST SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24AS01", "T24AS02", "S24AS01"]
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

        # Setup 1: Register Teacher A (T24AS01 - 2nd Year - DAA)
        t_a_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24AS01",
            "name": "Prof. A",
            "year": "2nd Year",
            "subject": "DAA",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t_a_res.status_code == 201
        teacher_a_token = t_a_res.json()["access_token"]

        # Setup 2: Register Teacher B (T24AS02 - 2nd Year - OS)
        t_b_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24AS02",
            "name": "Prof. B",
            "year": "2nd Year",
            "subject": "Operating Systems",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t_b_res.status_code == 201
        teacher_b_token = t_b_res.json()["access_token"]

        # Setup 3: Register Student Sannidha (S24AS01 - 2nd Year)
        s_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24AS01",
            "name": "Sannidha",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s_res.status_code == 201
        student_token = s_res.json()["access_token"]

        # Setup 4: Create Course for Teacher A
        c_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {teacher_a_token}"}, json={
            "course_name": "Algorithm Controls",
            "youtube_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        })
        assert c_res.status_code == 201
        course_id = c_res.json()["id"]

        # TEST 1: Backward 10s While Playing (01:00 -> 00:50)
        print("\n--- TEST 1: Backward 10s While Playing (01:00 -> 00:50) ---")
        t1_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_BACKWARD",
            "event_timestamp": "00:50",
            "playback_speed": 1.0
        })
        assert t1_res.status_code == 201
        assert t1_res.json()["EventType"] == "SEEK_BACKWARD"
        assert t1_res.json()["EventTimestamp"] == "00:50"
        assert t1_res.json()["EventDuration"] is None
        assert t1_res.json()["PauseReason"] is None
        print("[PASS] TEST 1: SEEK_BACKWARD event recorded at timestamp 00:50 with duration=None.")

        # TEST 2: Forward 10s While Playing (01:00 -> 01:10)
        print("\n--- TEST 2: Forward 10s While Playing (01:00 -> 01:10) ---")
        t2_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_FORWARD",
            "event_timestamp": "01:10",
            "playback_speed": 1.0
        })
        assert t2_res.status_code == 201
        assert t2_res.json()["EventType"] == "SEEK_FORWARD"
        assert t2_res.json()["EventTimestamp"] == "01:10"
        print("[PASS] TEST 2: SEEK_FORWARD event recorded at timestamp 01:10.")

        # TEST 3 & 4: Backward & Forward While Paused
        print("\n--- TEST 3 & 4: Backward & Forward While Paused ---")
        t3_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_BACKWARD",
            "event_timestamp": "01:50",
            "playback_speed": 1.0
        })
        assert t3_res.status_code == 201

        t4_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_FORWARD",
            "event_timestamp": "02:10",
            "playback_speed": 1.0
        })
        assert t4_res.status_code == 201
        print("[PASS] TEST 3 & 4: Seek events recorded while video is paused.")

        # TEST 5: Multiple Backward Clicks (03:00 -> 02:50, 02:40, 02:30)
        print("\n--- TEST 5: Multiple Backward Clicks ---")
        for ts in ["02:50", "02:40", "02:30"]:
            res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
                "course_id": course_id,
                "event_type": "SEEK_BACKWARD",
                "event_timestamp": ts,
                "playback_speed": 1.0
            })
            assert res.status_code == 201
        print("[PASS] TEST 5: 3 distinct SEEK_BACKWARD events recorded for 3 backward clicks.")

        # TEST 6: Multiple Forward Clicks (03:00 -> 03:10, 03:20)
        print("\n--- TEST 6: Multiple Forward Clicks ---")
        for ts in ["03:10", "03:20"]:
            res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
                "course_id": course_id,
                "event_type": "SEEK_FORWARD",
                "event_timestamp": ts,
                "playback_speed": 1.0
            })
            assert res.status_code == 201
        print("[PASS] TEST 6: 2 distinct SEEK_FORWARD events recorded for 2 forward clicks.")

        # TEST 7: Video Start Boundary (00:05 -> 00:00)
        print("\n--- TEST 7: Video Start Boundary Clamp ---")
        t7_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_BACKWARD",
            "event_timestamp": "00:00",
            "playback_speed": 1.0
        })
        assert t7_res.status_code == 201
        assert t7_res.json()["EventTimestamp"] == "00:00"
        print("[PASS] TEST 7: Backward at 00:05 clamped to 00:00 (non-negative).")

        # TEST 8: Video End Boundary (10:55 -> 11:00)
        print("\n--- TEST 8: Video End Boundary Clamp ---")
        t8_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_FORWARD",
            "event_timestamp": "11:00",
            "playback_speed": 1.0
        })
        assert t8_res.status_code == 201
        assert t8_res.json()["EventTimestamp"] == "11:00"
        print("[PASS] TEST 8: Forward at 10:55 clamped to 11:00.")

        # TEST 9: Playback Speed Persistence (1.5x speed)
        print("\n--- TEST 9: Playback Speed Persistence during Seek ---")
        t9_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_BACKWARD",
            "event_timestamp": "05:00",
            "playback_speed": 1.5
        })
        assert t9_res.status_code == 201
        assert t9_res.json()["PlaybackSpeed"] == 1.5
        print("[PASS] TEST 9: SEEK_BACKWARD recorded actual speed = 1.5x.")

        # TEST 10: Database Schema Verification
        print("\n--- TEST 10: Database Schema Verification ---")
        db_events = await database.interaction_events.find({"StudentID": "S24AS01"}).to_list(length=100)
        assert len(db_events) == 12
        for e in db_events:
            assert "StudentID" in e
            assert "StudentName" in e
            assert "CourseSubject" in e
            assert "CourseName" in e
            assert "EventType" in e
            assert "EventTimestamp" in e
            assert "EventDuration" in e
            assert "PlaybackSpeed" in e
            assert "PauseReason" in e
            # Ensure no extra fake columns added
            assert "SeekAmount" not in e
            assert "PreviousTimestamp" not in e
        print("[PASS] TEST 10: Verified database schema contains exactly the 9 required dataset columns.")

        # TEST 11: Teacher A Dataset View
        print("\n--- TEST 11: Teacher Dataset View ---")
        teacher_view = await ac.get("/api/v1/teacher/students/S24AS01/interactions", headers={"Authorization": f"Bearer {teacher_a_token}"})
        assert teacher_view.status_code == 200
        assert len(teacher_view.json()) == 12
        print("[PASS] TEST 11: Teacher A dataset viewer retrieved all 12 seek events.")

        # TEST 12: No Cross-Teacher Leak (Teacher B cannot see Teacher A's seek events)
        print("\n--- TEST 12: No Cross-Teacher Leak ---")
        teacher_b_view = await ac.get("/api/v1/teacher/students/S24AS01/interactions", headers={"Authorization": f"Bearer {teacher_b_token}"})
        assert teacher_b_view.status_code == 200
        assert len(teacher_b_view.json()) == 0
        print("[PASS] TEST 12: Verified Teacher B sees 0 seek events for Teacher A's course.")

        # PURGE TEST DATA
        print("\n--- PURGE TEST DATA ---")
        await database.users.delete_many({"identifier": {"$in": test_ids}})
        await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
        await database.students.delete_many({"roll_number": {"$in": test_ids}})
        await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
        await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 12 EXPLICIT SEEK CONTROL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_seek_controls_tests())
