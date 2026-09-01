import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import sys
import asyncio
import logging
from unittest.mock import patch
from bson import ObjectId
from httpx import AsyncClient, ASGITransport

# Ensure app imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db
from app.schemas.question import GeneratedMCQ
from app.services.question_service import map_pause_count_to_question_count

logging.basicConfig(level=logging.INFO)


async def run_phase13_end_to_end_tests():
    print("=" * 60)
    print("STARTING COGNITRACE PHASE 13 COMPLETE STUDENT FLOW VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24E2E1", "S24E2E1"]
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.course_transcripts.delete_many({"teacher_id": {"$in": test_ids}})
    await database.concept_segments.delete_many({"teacher_id": {"$in": test_ids}})
    await database.interaction_events.delete_many({"StudentID": {"$in": test_ids}})
    await database.questions.delete_many({"course_id": {"$regex": "^[0-9a-fA-F]{24}$"}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # TEST 1: Pause Count Mapping Function
        print("\n--- TEST 1: Configurable Pause Count to Question Count Mapping ---")
        assert map_pause_count_to_question_count(0) == 2
        assert map_pause_count_to_question_count(1) == 2
        assert map_pause_count_to_question_count(3) == 3
        assert map_pause_count_to_question_count(6) == 4
        assert map_pause_count_to_question_count(10) == 5
        print("[PASS] TEST 1: Pause count deterministic mapping (0-1->2, 2-4->3, 5-7->4, 8+->5) verified.")

        # Setup 1: Register Teacher
        t1_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24E2E1",
            "name": "Prof. Turing",
            "year": "2nd Year",
            "subject": "Operating Systems",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t1_res.status_code == 201
        t1_token = t1_res.json()["access_token"]

        # Setup 2: Register Student
        s1_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24E2E1",
            "name": "Ada",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s1_res.status_code == 201
        s1_token = s1_res.json()["access_token"]

        # Setup 3: Create Course
        c1_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Operating System Scheduling & Memory",
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })
        assert c1_res.status_code == 201
        c1_id = c1_res.json()["id"]

        # Setup 4: Populate Completed Transcript in course_transcripts
        real_segments = [
            {"start": 0.0, "end": 60.0, "text": "Welcome to OS Scheduling. Today we explore CPU Scheduling algorithms.", "TranscriptStart": "00:00", "TranscriptEnd": "01:00"},
            {"start": 60.0, "end": 180.0, "text": "First Come First Served (FCFS) schedules processes in arrival order.", "TranscriptStart": "01:00", "TranscriptEnd": "03:00"},
            {"start": 180.0, "end": 300.0, "text": "Shortest Job First (SJF) selects the process with minimum execution time.", "TranscriptStart": "03:00", "TranscriptEnd": "05:00"}
        ]
        await database.course_transcripts.update_one(
            {"course_id": c1_id},
            {"$set": {
                "course_name": "Operating System Scheduling & Memory",
                "subject": "Operating Systems",
                "teacher_id": "T24E2E1",
                "teacher_name": "Prof. Turing",
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "status": "COMPLETED",
                "language": "en",
                "segments": real_segments
            }},
            upsert=True
        )

        # Setup 5: Populate Completed Concepts in concept_segments
        await database.concept_segments.insert_one({
            "course_id": c1_id,
            "CourseSubject": "Operating Systems",
            "CourseName": "Operating System Scheduling & Memory",
            "teacher_id": "T24E2E1",
            "teacher_name": "Prof. Turing",
            "status": "COMPLETED",
            "segments": [
                {
                    "Concept": "FCFS Scheduling",
                    "ConceptStart": "01:00",
                    "ConceptEnd": "03:00",
                    "Prerequisite": "None",
                    "DifficultyLevel": "Easy"
                },
                {
                    "Concept": "SJF Scheduling",
                    "ConceptStart": "03:00",
                    "ConceptEnd": "05:00",
                    "Prerequisite": "FCFS Scheduling",
                    "DifficultyLevel": "Medium"
                }
            ]
        })

        # TEST 2: Student Video Interaction Telemetry Recording
        print("\n--- TEST 2: Record Student Video Interaction Telemetry ---")
        # Record PLAY event
        e1 = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
            "course_id": c1_id,
            "event_type": "PLAY",
            "event_timestamp": "00:05"
        })
        assert e1.status_code == 201

        # Record 3 PAUSE events on FCFS Scheduling (timestamp 01:30)
        for i in range(3):
            p_res = await ac.post("/api/v1/student/events", headers={"Authorization": f"Bearer {s1_token}"}, json={
                "course_id": c1_id,
                "event_type": "PAUSE",
                "event_timestamp": "01:30",
                "pause_reason": "STUDY"
            })
            assert p_res.status_code == 201
        print("[PASS] TEST 2: 3 PAUSE telemetry events logged for student S24E2E1 at timestamp 01:30.")

        # TEST 3: Telemetry-Driven Question Generation Flow
        print("\n--- TEST 3: Telemetry-Driven Question Auto-Generation Endpoint ---")
        mock_mcqs = [
            GeneratedMCQ(
                question="How does First Come First Served (FCFS) schedule processes?",
                options=["By length", "By arrival order", "Randomly", "By priority"],
                correct_answer="By arrival order",
                difficulty="MEDIUM",
                explanation="FCFS schedules processes strictly according to their order of arrival as explained in the lecture.",
                concept="FCFS Scheduling"
            ),
            GeneratedMCQ(
                question="What is the primary advantage of SJF?",
                options=["It minimizes average waiting time", "It is fair to all", "It avoids starvation", "It is simplest"],
                correct_answer="It minimizes average waiting time",
                difficulty="MEDIUM",
                explanation="SJF selects process with minimum execution time.",
                concept="SJF Scheduling"
            ),
            GeneratedMCQ(
                question="Which algorithm can lead to starvation?",
                options=["FCFS", "SJF", "Round Robin", "None"],
                correct_answer="SJF",
                difficulty="HARD",
                explanation="SJF can lead to starvation if short jobs keep arriving.",
                concept="SJF Scheduling"
            )
        ]

        with patch("app.services.claude_service.ClaudeService.generate_mcqs_from_transcript", return_value=mock_mcqs):
            auto_res = await ac.post(
                f"/api/v1/student/courses/{c1_id}/auto-generate",
                headers={"Authorization": f"Bearer {s1_token}"}
            )
            assert auto_res.status_code == 200
            data = auto_res.json()
            assert data["total"] == 3
            q1 = data["questions"][0]
            # SECURITY GUARANTEE: correct_answer & explanation MUST NOT BE RETURNED TO STUDENT!
            assert "correct_answer" not in q1
            assert "explanation" not in q1
            assert "question" in q1
            assert len(q1["options"]) == 4
            print(f"[PASS] TEST 3: Auto-generation triggered from telemetry. Generated {data['total']} student-safe questions.")

        # TEST 4: Duplicate Prevention Verification
        print("\n--- TEST 4: Duplicate Prevention on Repeated Telemetry Generation ---")
        with patch("app.services.claude_service.ClaudeService.generate_mcqs_from_transcript", return_value=mock_mcqs):
            re_gen = await ac.post(
                f"/api/v1/student/courses/{c1_id}/auto-generate",
                headers={"Authorization": f"Bearer {s1_token}"}
            )
            assert re_gen.status_code == 200
            db_q_count = await database.questions.count_documents({"course_id": c1_id})
            assert db_q_count == 3
            print(f"[PASS] TEST 4: Repeated generation call did not duplicate items (DB count remains {db_q_count}).")

        # TEST 5: Student Answer Submission & Grading Feedback
        print("\n--- TEST 5: Student Answer Submission & Post-Submission Feedback ---")
        target_q = data["questions"][0]
        q_id = target_q["id"]
        sub_res = await ac.post(
            f"/api/v1/student/questions/{q_id}/submit",
            headers={"Authorization": f"Bearer {s1_token}"},
            json={"selected_option": "By arrival order"}
        )
        assert sub_res.status_code == 200
        sub_data = sub_res.json()
        assert sub_data["is_correct"] is True
        assert sub_data["correct_answer"] == "By arrival order"
        assert "explanation" in sub_data and len(sub_data["explanation"]) > 10
        print("[PASS] TEST 5: Student submission graded correctly. Correct answer & explanation revealed ONLY post-submission.")

        # TEST 6: Clean Up All Test Data
        print("\n--- TEST 6: Purge All Test Data ---")
        await database.users.delete_many({"identifier": {"$in": test_ids}})
        await database.teachers.delete_many({"teacher_id": "T24E2E1"})
        await database.students.delete_many({"roll_number": "S24E2E1"})
        await database.courses.delete_one({"_id": ObjectId(c1_id)})
        await database.course_transcripts.delete_one({"course_id": c1_id})
        await database.concept_segments.delete_one({"course_id": c1_id})
        await database.interaction_events.delete_many({"StudentID": "S24E2E1"})
        await database.questions.delete_many({"course_id": c1_id})
        print("[PASS] TEST 6: Environment cleaned.")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 6 PHASE 13 END-TO-END STUDENT FLOW TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase13_end_to_end_tests())
