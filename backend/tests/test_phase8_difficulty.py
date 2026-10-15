import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import os
import sys
import asyncio
from datetime import datetime, timezone
import httpx
from bson import ObjectId

# Ensure app imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db


async def run_phase8_verification_tests():
    print("=" * 60)
    print("STARTING COGNITRACE PHASE 8 DIFFICULTY SCORE VERIFICATION SUITE")
    print("=" * 60)

    await connect_to_mongo()
    database = db.client[settings.MONGODB_DB_NAME]

    # Clean existing collections before test
    await database.users.delete_many({})
    await database.teachers.delete_many({})
    await database.students.delete_many({})
    await database.courses.delete_many({})
    await database.course_transcripts.delete_many({})
    await database.concept_segments.delete_many({})
    await database.interaction_events.delete_many({})
    await database.concept_event_mappings.delete_many({})
    await database.difficulty.delete_many({})

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        
        # 1. Register Teacher A
        teacher_payload = {
            "name": "Nidhi",
            "email": "nidhi.teacher8@cognitrace.edu",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "teacher_id": "T24A001",
            "subject": "DAA",
            "year": "2nd Year"
        }
        res_t = await ac.post("/api/v1/auth/register/teacher", json=teacher_payload)
        t_token = res_t.json()["access_token"]

        # 2. Register Student
        student_payload = {
            "name": "Sannidha",
            "email": "sannidha.student8@cognitrace.edu",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "roll_number": "S24A001",
            "year": "2nd Year"
        }
        res_s = await ac.post("/api/v1/auth/register/student", json=student_payload)
        s_token = res_s.json()["access_token"]

        # 3. Create Course
        course_payload = {
            "course_name": "Definition",
            "subject": "DAA",
            "year": "2nd Year",
            "youtube_url": "https://www.youtube.com/watch?v=ONFkb-PxKts"
        }
        res_c = await ac.post("/api/v1/courses", json=course_payload, headers={"Authorization": f"Bearer {t_token}"})
        c_id = res_c.json()["id"]

        now = datetime.now(timezone.utc)
        
        # 4. Insert Transcript (Phase 4)
        transcript_doc = {
            "course_id": c_id,
            "status": "COMPLETED",
            "segments": [
                {"start": 0.0, "end": 60.0, "text": "Part 1"},
                {"start": 60.0, "end": 120.0, "text": "Part 2"}
            ]
        }
        await database.course_transcripts.insert_one(transcript_doc)

        # 5. Insert Concepts (Phase 6)
        concept_doc = {
            "course_id": c_id,
            "CourseSubject": "DAA",
            "CourseName": "Definition",
            "status": "COMPLETED",
            "segments": [
                {"Concept": "Array Intro", "ConceptStart": "00:00", "ConceptEnd": "01:00", "Prerequisite": "None"},
                {"Concept": "Def Fundamentals", "ConceptStart": "01:00", "ConceptEnd": "02:00", "Prerequisite": "Array Intro"}
            ]
        }
        await database.concept_segments.insert_one(concept_doc)

        print("\n--- TEST 1: Register Teacher, Student & Base Course Data ---")
        print("[PASS] Inserted initial student, teacher, and mock concept mappings.")

        # 6. Insert Phase 5 Interaction Telemetry
        events = [
            # High Difficulty Events on "Def Fundamentals" (Starts at 60s)
            {
                "StudentID": "S24A001", "StudentName": "Sannidha", "CourseSubject": "DAA", "CourseName": "Definition",
                "EventType": "PAUSE", "EventTimestamp": "01:10", "PauseReason": "Trying to understand the concept"
            },
            {
                "StudentID": "S24A001", "StudentName": "Sannidha", "CourseSubject": "DAA", "CourseName": "Definition",
                "EventType": "PAUSE", "EventTimestamp": "01:20", "PauseReason": "I didn't understand"
            },
            {
                "StudentID": "S24A001", "StudentName": "Sannidha", "CourseSubject": "DAA", "CourseName": "Definition",
                "EventType": "SEEK_BACKWARD", "EventTimestamp": "01:30"
            },
            # Progress bar jump produces SEEK_BACKWARD and REPLAY at the exact same timestamp
            {
                "StudentID": "S24A001", "StudentName": "Sannidha", "CourseSubject": "DAA", "CourseName": "Definition",
                "EventType": "SEEK_BACKWARD", "EventTimestamp": "01:40"
            },
            {
                "StudentID": "S24A001", "StudentName": "Sannidha", "CourseSubject": "DAA", "CourseName": "Definition",
                "EventType": "REPLAY", "EventTimestamp": "01:40"
            },
            {
                "StudentID": "S24A001", "StudentName": "Sannidha", "CourseSubject": "DAA", "CourseName": "Definition",
                "EventType": "SEEK_FORWARD", "EventTimestamp": "01:50"
            },

            # Zero interaction on "Array Intro" - just played through
            {
                "StudentID": "S24A001", "StudentName": "Sannidha", "CourseSubject": "DAA", "CourseName": "Definition",
                "EventType": "PLAY", "EventTimestamp": "00:10"
            }
        ]
        await database.interaction_events.insert_many(events)

        print("\n--- TEST 2: Trigger Phase 8 Difficulty Generation ---")
        res_diff = await ac.get(f"/api/v1/teacher/students/S24A001/difficulty", headers={"Authorization": f"Bearer {t_token}"})
        assert res_diff.status_code == 200
        difficulty_data = res_diff.json()

        print(f"[PASS] Retrieved {len(difficulty_data)} difficulty records.")
        assert len(difficulty_data) == 2, f"Expected 2 difficulty records, got {len(difficulty_data)}"

        # Find specific concept records
        def_fundamentals = next(d for d in difficulty_data if d["Concept"] == "Def Fundamentals")
        array_intro = next(d for d in difficulty_data if d["Concept"] == "Array Intro")

        # 7. Verify 13-Column Schema
        print("\n--- TEST 3: Verify Exact 13-Column Dataset Schema ---")
        expected_keys = {
            "id", "StudentID", "StudentName", "CourseSubject", "CourseName", "Concept",
            "ReplayCount", "PauseCount", "SeekBackwardCount", "SeekForwardCount", "UnderstandPauseCount",
            "DifficultyScore", "DifficultyLevel", "NeedsRevision"
        }
        assert set(def_fundamentals.keys()) == expected_keys, f"Schema mismatch! Keys: {set(def_fundamentals.keys())}"
        print("[PASS] Exact 13-column schema verified without quiz variables or AI data.")

        # 8. Verify Zero Interaction (Array Intro)
        print("\n--- TEST 4: Zero Interaction Test (Easy) ---")
        assert array_intro["PauseCount"] == 0
        assert array_intro["DifficultyScore"] == 0.0
        assert array_intro["DifficultyLevel"] == "Easy"
        assert array_intro["NeedsRevision"] is False
        print("[PASS] Zero interaction naturally results in Easy/0 score.")

        # 9. Verify Count Calculations & Double Count Prevention (Def Fundamentals)
        print("\n--- TEST 5: Verify Interaction Counts & Double Count Prevention ---")
        # 2 PAUSE events, both with "understand" in the reason
        assert def_fundamentals["PauseCount"] == 2
        assert def_fundamentals["UnderstandPauseCount"] == 2
        # 1 SEEK_FORWARD
        assert def_fundamentals["SeekForwardCount"] == 1
        # 1 REPLAY
        assert def_fundamentals["ReplayCount"] == 1
        # 2 SEEK_BACKWARD total, but 1 was at the same timestamp as REPLAY, so SeekBackwardCount = 1
        assert def_fundamentals["SeekBackwardCount"] == 1
        
        print("[PASS] Event counts correctly derived. Double counting of SEEK_BACKWARD/REPLAY prevented.")

        # 10. Verify Deterministic High Difficulty Score
        print("\n--- TEST 6: Deterministic Score Calculation (High) ---")
        # Score = (ReplayCount * 2) + (PauseCount * 1) + (SeekBackwardCount * 2) + (SeekForwardCount * 0.5) + (UnderstandPauseCount * 3)
        # = (1 * 2) + (2 * 1) + (1 * 2) + (1 * 0.5) + (2 * 3) = 2 + 2 + 2 + 0.5 + 6 = 12.5
        assert def_fundamentals["DifficultyScore"] == 12.5
        assert def_fundamentals["DifficultyLevel"] == "High"
        assert def_fundamentals["NeedsRevision"] is True
        print("[PASS] DifficultyScore = 12.5 -> High, NeedsRevision = true")

        # 11. Idempotency Check
        print("\n--- TEST 7: Idempotency & Duplicate Prevention ---")
        res_diff2 = await ac.get(f"/api/v1/teacher/students/S24A001/difficulty", headers={"Authorization": f"Bearer {t_token}"})
        assert len(res_diff2.json()) == 2
        db_count = await database.difficulty.count_documents({})
        assert db_count == 2
        print("[PASS] Database returned exactly 2 records on repeated calls. No duplicates.")

        # 12. Teacher Scoping Check
        print("\n--- TEST 8: Teacher Scoping & Authorization ---")
        teacher_b = {
            "name": "Ravi", "email": "ravi.teacher8@cognitrace.edu", "password": "Password123!", "confirm_password": "Password123!",
            "teacher_id": "T24A002", "subject": "Web Tech", "year": "2nd Year"
        }
        res_tb = await ac.post("/api/v1/auth/register/teacher", json=teacher_b)
        tb_token = res_tb.json()["access_token"]
        res_diff_b = await ac.get(f"/api/v1/teacher/students/S24A001/difficulty", headers={"Authorization": f"Bearer {tb_token}"})
        assert res_diff_b.status_code == 200
        assert len(res_diff_b.json()) == 0
        print("[PASS] Teacher B correctly blocked from Teacher A's student difficulty scores.")

        print("\n--- TEST 9: Purge All Test Data ---")
        await database.users.delete_many({})
        await database.teachers.delete_many({})
        await database.students.delete_many({})
        await database.courses.delete_many({})
        await database.course_transcripts.delete_many({})
        await database.concept_segments.delete_many({})
        await database.interaction_events.delete_many({})
        await database.concept_event_mappings.delete_many({})
        await database.difficulty.delete_many({})
        print("[PASS] Test environment cleaned.")

    print("\n" + "=" * 60)
    print("ALL PHASE 8 DIFFICULTY SCORE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_phase8_verification_tests())
