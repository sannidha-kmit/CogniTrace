import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import asyncio
import logging
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from app.main import app
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_attention")


async def run_attention_monitoring_tests():
    print("=" * 70)
    print("STARTING REAL-TIME PRIVACY-PRESERVING ATTENTION MONITORING TEST SUITE")
    print("=" * 70)

    # 1. Connect MongoDB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24AT01", "S24AT01", "S24AT02"]
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.student_attention_events.delete_many({"StudentID": {"$in": test_ids}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # -------------------------------------------------------------
        # 1. SETUP: Register Teacher and Student
        # -------------------------------------------------------------
        print("\n[STEP 1] Registering Test Teacher & Student...")
        t_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24AT01",
            "name": "Prof. Alan Turing",
            "year": "3rd Year",
            "subject": "Algorithm Analysis",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t_res.status_code == 201, f"Teacher reg failed: {t_res.text}"
        teacher_token = t_res.json()["access_token"]
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

        s_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24AT01",
            "name": "Alice Student",
            "year": "3rd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s_res.status_code == 201, f"Student reg failed: {s_res.text}"
        student_token = s_res.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}


        # -------------------------------------------------------------
        # 2. SETUP: Create Course
        # -------------------------------------------------------------
        print("\n[STEP 2] Creating Test Course for Year 3...")
        c_res = await ac.post("/api/v1/courses", json={
            "course_name": "Advanced Dynamic Programming",
            "youtube_url": "https://www.youtube.com/watch?v=kqtD5dpn9C8"
        }, headers=teacher_headers)
        assert c_res.status_code == 201, f"Course creation failed: {c_res.text}"
        course_id = c_res.json()["id"]
        print(f"Course created successfully: ID {course_id}")


        # -------------------------------------------------------------
        # 3. TEST: Config Endpoint
        # -------------------------------------------------------------
        print("\n[STEP 3] Testing GET /api/v1/attention/config...")
        cfg_res = await ac.get("/api/v1/attention/config")
        assert cfg_res.status_code == 200
        cfg = cfg_res.json()
        assert "yaw_threshold_degrees" in cfg
        assert "high_distraction_seconds" in cfg
        assert cfg["yaw_threshold_degrees"] == 25.0
        print("Config endpoint validated successfully.")

        # -------------------------------------------------------------
        # 4. TEST SCENARIOS: Privacy-Preserving Derived Attention Ingestion
        # -------------------------------------------------------------
        print("\n[STEP 4] Testing Scenario 1: Student Watches Normally (FOCUSED)...")
        ev1 = await ac.post("/api/v1/student/attention/telemetry", json={
            "course_id": course_id,
            "video_timestamp": "01:15",
            "attention_state": "FOCUSED",
            "distraction_score": 5.0,
            "distraction_duration": 0.0,
            "event_type": "FOCUSED_HEARTBEAT",
            "confidence": 0.95,
            "head_pose": {"yaw": 2.0, "pitch": -1.0, "roll": 0.0},
            "noise_level": "QUIET",
            "environmental_distraction": False,
            "behavioral_distraction": False,
            "notification_triggered": False
        }, headers=student_headers)
        assert ev1.status_code == 201, f"Telemetry post failed: {ev1.text}"
        ev1_data = ev1.json()
        assert ev1_data["StudentID"] == "S24AT01"
        assert ev1_data["attention_state"] == "FOCUSED"
        print("Scenario 1 verified.")

        print("\n[STEP 5] Testing Scenario 3: Looking Away Sustained (>10s)...")
        ev3 = await ac.post("/api/v1/student/attention/telemetry", json={
            "course_id": course_id,
            "video_timestamp": "02:30",
            "attention_state": "HIGH_DISTRACTION",
            "distraction_score": 85.0,
            "distraction_duration": 12.5,
            "event_type": "LOOKING_AWAY",
            "confidence": 0.90,
            "head_pose": {"yaw": 38.0, "pitch": 5.0, "roll": 2.0},
            "noise_level": "QUIET",
            "environmental_distraction": False,
            "behavioral_distraction": True,
            "notification_triggered": True
        }, headers=student_headers)
        assert ev3.status_code == 201
        assert ev3.json()["attention_state"] == "HIGH_DISTRACTION"
        assert ev3.json()["notification_triggered"] is True
        print("Scenario 3 verified.")

        print("\n[STEP 6] Testing Scenario 4: Electronic Accessory Interaction (PHONE_INTERACTION)...")
        ev4 = await ac.post("/api/v1/student/attention/telemetry", json={
            "course_id": course_id,
            "video_timestamp": "03:45",
            "attention_state": "SUSTAINED_DISTRACTION",
            "distraction_score": 75.0,
            "distraction_duration": 8.0,
            "event_type": "PHONE_INTERACTION",
            "confidence": 0.85,
            "head_pose": {"yaw": 5.0, "pitch": -28.0, "roll": 0.0},
            "noise_level": "QUIET",
            "environmental_distraction": False,
            "behavioral_distraction": True,
            "notification_triggered": False
        }, headers=student_headers)
        assert ev4.status_code == 201
        assert ev4.json()["event_type"] == "PHONE_INTERACTION"
        print("Scenario 4 verified.")

        print("\n[STEP 7] Testing Scenario 6: Face Not Detected (Temporary Leave)...")
        ev6 = await ac.post("/api/v1/student/attention/telemetry", json={
            "course_id": course_id,
            "video_timestamp": "04:10",
            "attention_state": "FACE_NOT_DETECTED",
            "distraction_score": 40.0,
            "distraction_duration": 5.0,
            "event_type": "FACE_NOT_DETECTED",
            "confidence": 0.50,
            "head_pose": None,
            "noise_level": "QUIET",
            "environmental_distraction": False,
            "behavioral_distraction": False,
            "notification_triggered": False
        }, headers=student_headers)
        assert ev6.status_code == 201
        assert ev6.json()["attention_state"] == "FACE_NOT_DETECTED"
        print("Scenario 6 verified.")

        print("\n[STEP 8] Testing Scenario 7: Environmental Noise Alert (HIGH_NOISE)...")
        ev7 = await ac.post("/api/v1/student/attention/telemetry", json={
            "course_id": course_id,
            "video_timestamp": "05:00",
            "attention_state": "POSSIBLE_DISTRACTION",
            "distraction_score": 35.0,
            "distraction_duration": 4.0,
            "event_type": "HIGH_NOISE",
            "confidence": 0.80,
            "head_pose": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            "noise_level": "NOISY",
            "environmental_distraction": True,
            "behavioral_distraction": False,
            "notification_triggered": True
        }, headers=student_headers)
        assert ev7.status_code == 201
        assert ev7.json()["environmental_distraction"] is True
        print("Scenario 7 verified.")

        # -------------------------------------------------------------
        # 5. TEST: Batch Telemetry Ingestion
        # -------------------------------------------------------------
        print("\n[STEP 9] Testing Batch Attention Ingestion...")
        batch_res = await ac.post("/api/v1/student/attention/batch", json={
            "events": [
                {
                    "course_id": course_id,
                    "video_timestamp": "05:30",
                    "attention_state": "RECOVERED",
                    "distraction_score": 0.0,
                    "distraction_duration": 0.0,
                    "event_type": "RECOVERED_ATTENTION",
                    "confidence": 0.95,
                    "noise_level": "QUIET",
                    "environmental_distraction": False,
                    "behavioral_distraction": False,
                    "notification_triggered": False
                },
                {
                    "course_id": course_id,
                    "video_timestamp": "06:00",
                    "attention_state": "FOCUSED",
                    "distraction_score": 0.0,
                    "distraction_duration": 0.0,
                    "event_type": "FOCUSED_HEARTBEAT",
                    "confidence": 0.98,
                    "noise_level": "QUIET",
                    "environmental_distraction": False,
                    "behavioral_distraction": False,
                    "notification_triggered": False
                }
            ]
        }, headers=student_headers)
        assert batch_res.status_code == 201
        assert batch_res.json()["inserted_count"] == 2
        print("Batch ingestion verified.")

        # -------------------------------------------------------------
        # 6. TEST: Student Summary Endpoint
        # -------------------------------------------------------------
        print("\n[STEP 10] Testing Student Attention Summary...")
        sum_res = await ac.get(f"/api/v1/student/attention/summary?course_id={course_id}", headers=student_headers)
        assert sum_res.status_code == 200
        summary = sum_res.json()
        assert summary["student_id"] == "S24AT01"
        assert summary["total_events"] >= 7
        assert "focused_ratio" in summary
        assert "distraction_event_count" in summary
        print(f"Student Summary: Total Events: {summary['total_events']}, Focused Ratio: {summary['focused_ratio']}")

        # -------------------------------------------------------------
        # 7. TEST: Teacher Course Attention Analytics
        # -------------------------------------------------------------
        print("\n[STEP 11] Testing Teacher Course Attention Analytics...")
        t_analytics_res = await ac.get(f"/api/v1/teacher/attention/course/{course_id}", headers=teacher_headers)
        assert t_analytics_res.status_code == 200
        t_data = t_analytics_res.json()
        assert t_data["course_id"] == course_id
        assert "distraction_breakdown" in t_data
        assert "average_focus_ratio" in t_data
        print("Teacher Course Analytics verified.")

        # -------------------------------------------------------------
        # 8. TEST: Strict Privacy Verification (MongoDB Audit)
        # -------------------------------------------------------------
        print("\n[STEP 12] Auditing Database Records for Absolute Privacy Preservation...")
        stored_events = await database.student_attention_events.find({"StudentID": "S24AT01"}).to_list(length=100)
        assert len(stored_events) > 0

        forbidden_keys = ["image", "frame", "camera_raw", "audio_sample", "audio_raw", "video_stream", "photo", "face_crop", "biometrics"]
        for ev in stored_events:
            for k in ev.keys():
                assert k.lower() not in forbidden_keys, f"CRITICAL PRIVACY VIOLATION: Found raw key {k} in database!"
            # Ensure numbers are standard floats
            assert isinstance(ev["distraction_score"], (int, float))
            assert isinstance(ev["distraction_duration"], (int, float))

        print("Database Audit PASSED: Zero camera frames or audio samples exist in MongoDB.")


        # -------------------------------------------------------------
        # 9. TEST: Web UI Endpoint Route
        # -------------------------------------------------------------
        print("\n[STEP 13] Testing /lecture Web UI Route...")
        lecture_res = await ac.get("/lecture")
        assert lecture_res.status_code == 200
        assert "CogniTrace" in lecture_res.text
        assert "Attention Monitor" in lecture_res.text
        print("Web UI /lecture route verified.")

    # Cleanup
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.student_attention_events.delete_many({"StudentID": {"$in": test_ids}})

    await close_mongo_connection()

    print("\n" + "=" * 70)
    print("ALL 13 TEST SCENARIOS PASSED WITH ZERO ERRORS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_attention_monitoring_tests())
