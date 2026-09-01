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


async def run_correction_tests():
    print("=" * 60)
    print("STARTING PHASE 5 CORRECTION: ALL INTERACTION EVENT TYPES TEST SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24AC01", "S24AC01"]
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

        # Setup 1: Register Teacher Sannidha (T24AC01 - 2nd Year - DAA)
        t_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24AC01",
            "name": "Prof. Sannidha",
            "year": "2nd Year",
            "subject": "DAA",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t_res.status_code == 201
        teacher_token = t_res.json()["access_token"]

        # Setup 2: Register Student Sannidha (S24AC01 - 2nd Year)
        s_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24AC01",
            "name": "Sannidha",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s_res.status_code == 201
        student_token = s_res.json()["access_token"]

        # Setup 3: Create Course "Definition"
        c_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {teacher_token}"}, json={
            "course_name": "definition",
            "youtube_url": "https://www.youtube.com/watch?v=ONFkb-PxKts"
        })
        assert c_res.status_code == 201
        course_id = c_res.json()["id"]

        # TEST A: Send PLAY Event
        print("\n--- TEST A: Record PLAY Event ---")
        play_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "PLAY",
            "event_timestamp": "00:00",
            "playback_speed": 1.0
        })
        assert play_res.status_code == 201
        assert play_res.json()["EventType"] == "PLAY"
        assert play_res.json()["EventDuration"] is None
        assert play_res.json()["PauseReason"] is None
        print("[PASS] TEST A: PLAY event recorded with duration=None, pause_reason=None.")

        # TEST B, C, D, E: Send PAUSE Event with Measured Duration & Reason
        print("\n--- TEST B-E: Record PAUSE Event with Duration & Reason ---")
        pause_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "PAUSE",
            "event_timestamp": "01:10",
            "event_duration": 10.0,
            "playback_speed": 1.0,
            "pause_reason": "Trying to understand the topic"
        })
        assert pause_res.status_code == 201
        assert pause_res.json()["EventType"] == "PAUSE"
        assert pause_res.json()["EventDuration"] == 10.0
        assert pause_res.json()["PauseReason"] == "Trying to understand the topic"
        print("[PASS] TEST B-E: PAUSE event recorded with duration=10.0s and reason='Trying to understand the topic'.")

        # TEST F: Record SEEK_BACKWARD & REPLAY Events
        print("\n--- TEST F: Record SEEK_BACKWARD & REPLAY Events ---")
        sb_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_BACKWARD",
            "event_timestamp": "00:55",
            "playback_speed": 1.0
        })
        assert sb_res.status_code == 201

        rp_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "REPLAY",
            "event_timestamp": "00:55",
            "playback_speed": 1.0
        })
        assert rp_res.status_code == 201
        print("[PASS] TEST F: SEEK_BACKWARD and REPLAY events recorded at timestamp 00:55.")

        # TEST G: Record SEEK_FORWARD Event
        print("\n--- TEST G: Record SEEK_FORWARD Event ---")
        sf_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SEEK_FORWARD",
            "event_timestamp": "01:30",
            "playback_speed": 1.0
        })
        assert sf_res.status_code == 201
        print("[PASS] TEST G: SEEK_FORWARD event recorded at timestamp 01:30.")

        # TEST H & I: Record SPEED_CHANGE Events (1.0x -> 1.5x, 1.5x -> 2.0x)
        print("\n--- TEST H & I: Record SPEED_CHANGE Events ---")
        sp1_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SPEED_CHANGE",
            "event_timestamp": "01:30",
            "playback_speed": 1.5
        })
        assert sp1_res.status_code == 201
        assert sp1_res.json()["PlaybackSpeed"] == 1.5

        sp2_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "SPEED_CHANGE",
            "event_timestamp": "01:30",
            "playback_speed": 2.0
        })
        assert sp2_res.status_code == 201
        assert sp2_res.json()["PlaybackSpeed"] == 2.0
        print("[PASS] TEST H & I: SPEED_CHANGE events recorded with speeds 1.5x and 2.0x.")

        # TEST J: Record VIDEO_COMPLETE Event
        print("\n--- TEST J: Record VIDEO_COMPLETE Event ---")
        vc_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {student_token}"}, json={
            "course_id": course_id,
            "event_type": "VIDEO_COMPLETE",
            "event_timestamp": "01:31",
            "playback_speed": 2.0
        })
        assert vc_res.status_code == 201
        assert vc_res.json()["EventType"] == "VIDEO_COMPLETE"
        print("[PASS] TEST J: VIDEO_COMPLETE event recorded.")

        # VERIFY DATASET IN MONGODB
        print("\n--- MONGODB VERIFICATION: Query All Events for Student ---")
        all_events_res = await ac.get("/api/v1/teacher/students/S24AC01/interactions", headers={"Authorization": f"Bearer {teacher_token}"})
        assert all_events_res.status_code == 200
        events = all_events_res.json()
        assert len(events) == 8
        event_types_found = {e["EventType"] for e in events}
        expected_types = {"PLAY", "PAUSE", "SEEK_BACKWARD", "REPLAY", "SEEK_FORWARD", "SPEED_CHANGE", "VIDEO_COMPLETE"}
        assert event_types_found == expected_types
        print(f"[PASS] MONGODB VERIFICATION: All 7 expected event types verified in MongoDB: {event_types_found}")

        # PURGE TEST DATA
        print("\n--- PURGE TEST DATA ---")
        await database.users.delete_many({"identifier": {"$in": test_ids}})
        await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
        await database.students.delete_many({"roll_number": {"$in": test_ids}})
        await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
        await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL CORRECTION VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_correction_tests())
