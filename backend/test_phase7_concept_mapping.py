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
from app.services.mapping_service import MappingService, parse_timestamp_to_seconds


async def run_phase7_verification_tests():
    print("=" * 60)
    print("STARTING COGNITRACE PHASE 7 CONCEPT MAPPING VERIFICATION SUITE")
    print("=" * 60)

    await connect_to_mongo()
    database = db.client[settings.MONGODB_DB_NAME]

    # Clean existing collections before test
    await database.users.delete_many({})
    await database.teachers.delete_many({})
    await database.students.delete_many({})
    await database.courses.delete_many({})
    await database.course_transcripts.delete_many({})
    await database.transcription_jobs.delete_many({})
    await database.concept_segments.delete_many({})
    await database.concept_extraction_jobs.delete_many({})
    await database.interaction_events.delete_many({})
    await database.concept_event_mappings.delete_many({})

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        
        # 1. Register Teacher A (Nidhi, T24A001, DAA, 2nd Year)
        teacher_payload = {
            "name": "Nidhi",
            "email": "nidhi.teacher7@cognitrace.edu",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "teacher_id": "T24A001",
            "subject": "DAA",
            "year": "2nd Year"
        }
        res_t = await ac.post("/api/v1/auth/register/teacher", json=teacher_payload)
        assert res_t.status_code == 201, f"Teacher registration failed: {res_t.text}"
        t_token = res_t.json()["access_token"]

        # 2. Register Student (Sannidha, S24A001, 2nd Year)
        student_payload = {
            "name": "Sannidha",
            "email": "sannidha.student7@cognitrace.edu",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "roll_number": "S24A001",
            "year": "2nd Year"
        }
        res_s = await ac.post("/api/v1/auth/register/student", json=student_payload)
        assert res_s.status_code == 201, f"Student registration failed: {res_s.text}"
        s_token = res_s.json()["access_token"]

        # 3. Create Course (Definition, DAA, 2nd Year)
        course_payload = {
            "course_name": "Definition",
            "subject": "DAA",
            "year": "2nd Year",
            "youtube_url": "https://www.youtube.com/watch?v=ONFkb-PxKts"
        }
        res_c = await ac.post("/api/v1/courses", json=course_payload, headers={"Authorization": f"Bearer {t_token}"})
        assert res_c.status_code == 201, f"Course creation failed: {res_c.text}"
        course_data = res_c.json()
        c_id = course_data["id"]

        print("\n--- TEST 1: Register Teacher, Student & Course ---")
        print(f"[PASS] TEST 1: Created course 'Definition' (ID: {c_id}) for teacher Nidhi & student Sannidha.")

        # 4. Insert Completed Phase 4 Course Transcript
        now = datetime.now(timezone.utc)
        transcript_doc = {
            "course_id": c_id,
            "course_name": "Definition",
            "subject": "DAA",
            "teacher_id": "T24A001",
            "teacher_name": "Nidhi",
            "youtube_url": "https://www.youtube.com/watch?v=ONFkb-PxKts",
            "status": "COMPLETED",
            "progress": 100,
            "stage": "COMPLETED",
            "language": "en",
            "processed_seconds": 91.0,
            "total_duration_seconds": 91.0,
            "segments": [
                {
                    "start": 0.0,
                    "end": 30.0,
                    "text": "Welcome to DAA. Let us introduce basic array definitions.",
                    "TranscriptStart": "00:00",
                    "TranscriptEnd": "00:30"
                },
                {
                    "start": 30.0,
                    "end": 60.0,
                    "text": "Now we discuss Def Fundamentals and core algorithm properties.",
                    "TranscriptStart": "00:30",
                    "TranscriptEnd": "01:00"
                },
                {
                    "start": 60.0,
                    "end": 91.0,
                    "text": "Finally, we cover Binary Search algorithm efficiency and time complexity.",
                    "TranscriptStart": "01:00",
                    "TranscriptEnd": "01:31"
                }
            ],
            "created_at": now,
            "updated_at": now
        }
        await database.course_transcripts.insert_one(transcript_doc)

        # 5. Insert Completed Phase 6 Concept Segments
        concept_doc = {
            "course_id": c_id,
            "CourseSubject": "DAA",
            "CourseName": "Definition",
            "teacher_id": "T24A001",
            "teacher_name": "Nidhi",
            "status": "COMPLETED",
            "segments": [
                {
                    "Concept": "Array Intro",
                    "ConceptStart": "00:00",
                    "ConceptEnd": "00:30",
                    "Prerequisite": "None",
                    "DifficultyLevel": "Easy"
                },
                {
                    "Concept": "Def Fundamentals",
                    "ConceptStart": "00:30",
                    "ConceptEnd": "01:00",
                    "Prerequisite": "Array Intro",
                    "DifficultyLevel": "Medium"
                },
                {
                    "Concept": "Binary Search",
                    "ConceptStart": "01:00",
                    "ConceptEnd": "01:31",
                    "Prerequisite": "Def Fundamentals",
                    "DifficultyLevel": "Hard"
                }
            ],
            "created_at": now,
            "updated_at": now
        }
        await database.concept_segments.insert_one(concept_doc)

        print("\n--- TEST 2: Insert Phase 4 Transcript & Phase 6 Concepts ---")
        print("[PASS] TEST 2: Inserted completed Phase 4 transcript & Phase 6 concepts.")

        # 6. Insert REAL Phase 5 Student Interaction Events
        events = [
            {
                "StudentID": "S24A001",
                "StudentName": "Sannidha",
                "CourseSubject": "DAA",
                "CourseName": "Definition",
                "EventType": "PAUSE",
                "EventTimestamp": "00:43",
                "EventDuration": 12.0,
                "PlaybackSpeed": 1.0,
                "PauseReason": "Re-read algorithm step",
                "created_at": now
            },
            {
                "StudentID": "S24A001",
                "StudentName": "Sannidha",
                "CourseSubject": "DAA",
                "CourseName": "Definition",
                "EventType": "SEEK_BACKWARD",
                "EventTimestamp": "00:35",
                "EventDuration": None,
                "PlaybackSpeed": 1.0,
                "PauseReason": None,
                "created_at": now
            },
            {
                "StudentID": "S24A001",
                "StudentName": "Sannidha",
                "CourseSubject": "DAA",
                "CourseName": "Definition",
                "EventType": "PLAY",
                "EventTimestamp": "01:00",
                "EventDuration": None,
                "PlaybackSpeed": 1.0,
                "PauseReason": None,
                "created_at": now
            },
            {
                "StudentID": "S24A001",
                "StudentName": "Sannidha",
                "CourseSubject": "DAA",
                "CourseName": "Definition",
                "EventType": "SPEED_CHANGE",
                "EventTimestamp": "01:15",
                "EventDuration": None,
                "PlaybackSpeed": 1.5,
                "PauseReason": None,
                "created_at": now
            }
        ]
        await database.interaction_events.insert_many(events)

        print("\n--- TEST 3: Insert Phase 5 Student Interaction Events ---")
        print(f"[PASS] TEST 3: Inserted {len(events)} Phase 5 student telemetry interaction events.")

        # 7. Execute Phase 7 GET /students/{roll}/concept-mappings Endpoint
        print("\n--- TEST 4: Phase 7 Concept-Event Mapping API Execution ---")
        res_m = await ac.get(f"/api/v1/teacher/students/S24A001/concept-mappings", headers={"Authorization": f"Bearer {t_token}"})
        assert res_m.status_code == 200, f"Mapping endpoint failed: {res_m.text}"
        mapped_list = res_m.json()

        assert len(mapped_list) == len(events), f"Expected {len(events)} mappings, got {len(mapped_list)}"
        print(f"[PASS] TEST 4: Generated {len(mapped_list)} concept-event mappings.")

        # 8. Verify Exact 9-Column Dataset Schema
        print("\n--- TEST 5: Verify Exact 9-Column Dataset Schema & Specific Values ---")
        sample_item = mapped_list[0]
        expected_keys = {
            "id", "StudentID", "StudentName", "CourseSubject", "CourseName",
            "EventType", "EventTimestamp", "Transcript", "Concept", "Prerequisite"
        }
        assert set(sample_item.keys()) == expected_keys, f"Schema mismatch! Keys: {set(sample_item.keys())}"

        # Verify PAUSE at 00:43 (43s) maps to 'Def Fundamentals' & 'Array Intro' prerequisite
        pause_event = next(m for m in mapped_list if m["EventType"] == "PAUSE" and m["EventTimestamp"] == "00:43")
        assert pause_event["StudentID"] == "S24A001"
        assert pause_event["StudentName"] == "Sannidha"
        assert pause_event["CourseSubject"] == "DAA"
        assert pause_event["CourseName"] == "Definition"
        assert pause_event["Concept"] == "Def Fundamentals"
        assert pause_event["Prerequisite"] == "Array Intro"
        assert "Def Fundamentals and core algorithm" in pause_event["Transcript"]
        print("[PASS] TEST 5: Verified PAUSE event at 00:43 mapped to 'Def Fundamentals' with exact 9-column schema.")

        # 9. Verify Timestamp Boundary Rule (01:00 / 60s matches 'Binary Search', not 'Def Fundamentals')
        print("\n--- TEST 6: Timestamp Boundary Rule Verification ---")
        boundary_event = next(m for m in mapped_list if m["EventTimestamp"] == "01:00")
        assert boundary_event["Concept"] == "Binary Search", f"Expected 'Binary Search', got '{boundary_event['Concept']}'"
        assert boundary_event["Prerequisite"] == "Def Fundamentals"
        print("[PASS] TEST 6: Boundary event at 01:00 (60s) correctly mapped to Concept starting at 01:00 ('Binary Search').")

        # 10. Idempotency Test: Call Endpoint Second Time
        print("\n--- TEST 7: Idempotency & Duplicate Prevention Check ---")
        res_m2 = await ac.get(f"/api/v1/teacher/students/S24A001/concept-mappings", headers={"Authorization": f"Bearer {t_token}"})
        assert res_m2.status_code == 200
        mapped_list2 = res_m2.json()
        assert len(mapped_list2) == len(events), "Duplicate rows were created on second endpoint call!"

        db_count = await database.concept_event_mappings.count_documents({})
        assert db_count == len(events), f"Expected {len(events)} docs in MongoDB, found {db_count}"
        print("[PASS] TEST 7: Idempotency verified. Re-running endpoint produced 0 duplicate documents.")

        # 11. Teacher Scoping & Authorization Test
        print("\n--- TEST 8: Teacher Scoping & Subject Authorization ---")
        teacher_b = {
            "name": "Ravi",
            "email": "ravi.teacher7@cognitrace.edu",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "teacher_id": "T24A002",
            "subject": "Web Tech",
            "year": "2nd Year"
        }
        res_tb = await ac.post("/api/v1/auth/register/teacher", json=teacher_b)
        tb_token = res_tb.json()["access_token"]

        res_mb = await ac.get(f"/api/v1/teacher/students/S24A001/concept-mappings", headers={"Authorization": f"Bearer {tb_token}"})
        assert res_mb.status_code == 200
        assert len(res_mb.json()) == 0, "Teacher B was able to view Teacher A's student mappings!"
        print("[PASS] TEST 8: Teacher B (Web Tech) correctly blocked from seeing Teacher A's (DAA) student mappings.")

        # 12. Purge All Test Data
        print("\n--- TEST 9: Purge All Test Data ---")
        await database.users.delete_many({})
        await database.teachers.delete_many({})
        await database.students.delete_many({})
        await database.courses.delete_many({})
        await database.course_transcripts.delete_many({})
        await database.transcription_jobs.delete_many({})
        await database.concept_segments.delete_many({})
        await database.concept_extraction_jobs.delete_many({})
        await database.interaction_events.delete_many({})
        await database.concept_event_mappings.delete_many({})

        final_count = await database.concept_event_mappings.count_documents({})
        assert final_count == 0
        print("[PASS] TEST 9: All test data purged. Database returned to EXACTLY 0 records!")

    print("\n" + "=" * 60)
    print("ALL PHASE 7 CONCEPT MAPPING VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_phase7_verification_tests())
