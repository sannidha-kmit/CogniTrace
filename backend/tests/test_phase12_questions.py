import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import asyncio
import sys
import time
import logging
from unittest.mock import patch
from bson import ObjectId
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db
from app.schemas.question import GeneratedMCQ
from app.services.question_service import derive_concept_ref, compute_question_hash, QuestionService

logging.basicConfig(level=logging.INFO)


async def run_phase12_tests():
    print("=" * 60)
    print("STARTING PHASE 12 CLAUDE QUESTION GENERATION & QUESTION BANK VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records
    test_ids = ["T24QG1", "S24QG1"]
    await database.users.delete_many({"identifier": {"$in": test_ids}})
    await database.teachers.delete_many({"teacher_id": {"$in": test_ids}})
    await database.students.delete_many({"roll_number": {"$in": test_ids}})
    await database.courses.delete_many({"teacher_id": {"$in": test_ids}})
    await database.course_transcripts.delete_many({"teacher_id": {"$in": test_ids}})
    await database.concept_segments.delete_many({"teacher_id": {"$in": test_ids}})
    await database.questions.delete_many({"course_id": {"$regex": "^[0-9a-fA-F]{24}$"}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # Setup 1: Register Teacher
        t1_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24QG1",
            "name": "Prof. Alan",
            "year": "2nd Year",
            "subject": "Algorithms",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t1_res.status_code == 201
        t1_token = t1_res.json()["access_token"]

        # Setup 2: Register Student
        s1_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24QG1",
            "name": "Grace",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s1_res.status_code == 201
        s1_token = s1_res.json()["access_token"]

        # Setup 3: Create Course
        c1_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Data Structures & Algorithms",
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })
        assert c1_res.status_code == 201
        c1_id = c1_res.json()["id"]

        # Setup 4: Populate Completed Transcript in course_transcripts
        real_segments = [
            {"start": 0.0, "end": 60.0, "text": "Welcome to Algorithms. Today we discuss Binary Search on sorted arrays.", "TranscriptStart": "00:00", "TranscriptEnd": "01:00"},
            {"start": 60.0, "end": 180.0, "text": "Binary search halves the search space each step giving logarithmic O(log n) time complexity.", "TranscriptStart": "01:00", "TranscriptEnd": "03:00"},
            {"start": 180.0, "end": 300.0, "text": "Linear search scans elements sequentially resulting in O(n) worst case time complexity.", "TranscriptStart": "03:00", "TranscriptEnd": "05:00"}
        ]
        await database.course_transcripts.update_one(
            {"course_id": c1_id},
            {"$set": {
                "course_name": "Data Structures & Algorithms",
                "subject": "Algorithms",
                "teacher_id": "T24QG1",
                "teacher_name": "Prof. Alan",
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "status": "COMPLETED",
                "language": "en",
                "segments": real_segments
            }},
            upsert=True
        )

        # Setup 5: Populate Completed Concepts in concept_segments (WITHOUT concept_id!)
        concept_list = [
            {
                "Concept": "Binary Search",
                "ConceptStart": "01:00",
                "ConceptEnd": "03:00",
                "Prerequisite": "Arrays",
                "DifficultyLevel": "Medium"
            },
            {
                "Concept": "Linear Search",
                "ConceptStart": "03:00",
                "ConceptEnd": "05:00",
                "Prerequisite": "None",
                "DifficultyLevel": "Easy"
            }
        ]
        await database.concept_segments.insert_one({
            "course_id": c1_id,
            "CourseSubject": "Algorithms",
            "CourseName": "Data Structures & Algorithms",
            "teacher_id": "T24QG1",
            "teacher_name": "Prof. Alan",
            "status": "COMPLETED",
            "segments": concept_list
        })

        # TEST 1: Concept Reference Derivation Check
        print("\n--- TEST 1: Deterministic Concept Reference Derivation ---")
        ref = derive_concept_ref(c1_id, "Binary Search")
        assert ref == f"{c1_id}:Binary_Search"
        print(f"[PASS] TEST 1: Concept ref derived deterministically as '{ref}'.")

        # TEST 2: Concept Transcript Text Extraction
        print("\n--- TEST 2: Transcript Text Extraction between ConceptStart & ConceptEnd ---")
        ref_out, name_out, tx_text = await QuestionService.extract_transcript_for_concept(c1_id, "Binary Search")
        assert "Binary search halves the search space" in tx_text
        assert "Linear search scans elements" not in tx_text
        print(f"[PASS] TEST 2: Extracted concept transcript text cleanly: '{tx_text[:60]}...'")

        # TEST 3: MCQ Generation Flow (with Mock Claude response to ensure predictable test suite execution)
        print("\n--- TEST 3: MCQ Generation & Validation Flow ---")
        mock_mcqs = [
            GeneratedMCQ(
                question="What is the time complexity of Binary Search on a sorted array?",
                options=["O(1)", "O(n)", "O(log n)", "O(n log n)"],
                correct_answer="O(log n)",
                difficulty="MEDIUM",
                explanation="Binary search repeatedly divides the search space in half, resulting in O(log n) complexity as stated in the transcript.",
                concept="Binary Search"
            ),
            GeneratedMCQ(
                question="What is a core prerequisite before applying binary search?",
                options=["Data must be integers", "Data must be positive", "Data must be sorted", "Data must be unique"],
                correct_answer="Data must be sorted",
                difficulty="EASY",
                explanation="Binary search logic fundamentally requires a sorted search space to know which half to eliminate.",
                concept="Binary Search"
            ),
        ]

        with patch("app.services.claude_service.ClaudeService.generate_mcqs_from_transcript", return_value=mock_mcqs):
            gen_res = await ac.post(
                f"/api/v1/teacher/courses/{c1_id}/questions/generate",
                headers={"Authorization": f"Bearer {t1_token}"},
                json={
                    "concept_identifier": "Binary Search",
                    "count": 2,
                    "difficulty": "MEDIUM"
                }
            )
            assert gen_res.status_code == 201
            data = gen_res.json()
            assert data["total"] == 2
            assert len(data["questions"]) == 2
            q1 = data["questions"][0]
            assert q1["question"] == "What is the time complexity of Binary Search on a sorted array?"
            assert q1["correct_answer"] == "O(log n)"
            assert len(q1["options"]) == 4
            assert q1["difficulty"] == "MEDIUM"
            print(f"[PASS] TEST 3: Generated and validated {data['total']} MCQs successfully via Teacher API.")

        # TEST 4: Question Quality Schema Enforcement
        print("\n--- TEST 4: MCQ Quality Schema Validation ---")
        q_item = data["questions"][0]
        assert "question" in q_item and len(q_item["question"]) > 5
        assert len(q_item["options"]) == 4
        assert q_item["correct_answer"] in q_item["options"]
        assert q_item["difficulty"] in ["EASY", "MEDIUM", "HARD"]
        assert "explanation" in q_item and len(q_item["explanation"]) > 10
        print("[PASS] TEST 4: All question quality schema criteria (4 options, valid correct_answer, difficulty, explanation) passed.")

        # TEST 5: Duplicate Question Prevention Method
        print("\n--- TEST 5: Duplicate Question Prevention ---")
        with patch("app.services.claude_service.ClaudeService.generate_mcqs_from_transcript", return_value=mock_mcqs):
            gen_res_dup = await ac.post(
                f"/api/v1/teacher/courses/{c1_id}/questions/generate",
                headers={"Authorization": f"Bearer {t1_token}"},
                json={
                    "concept_identifier": "Binary Search",
                    "count": 2
                }
            )
            assert gen_res_dup.status_code == 201
            # Questions in DB should still be 2, not 4
            q_count = await database.questions.count_documents({"course_id": c1_id})
            assert q_count == 2
            print(f"[PASS] TEST 5: Re-running generation returned existing questions without creating duplicates (DB count remains {q_count}).")

        # TEST 6: Teacher Question Bank Retrieval API (Full Data & Filtering)
        print("\n--- TEST 6: Teacher Question Bank Retrieval API ---")
        t_get_res = await ac.get(
            f"/api/v1/teacher/courses/{c1_id}/questions?difficulty=MEDIUM&count=1",
            headers={"Authorization": f"Bearer {t1_token}"}
        )
        assert t_get_res.status_code == 200
        t_data = t_get_res.json()
        assert t_data["total"] == 1
        assert t_data["questions"][0]["difficulty"] == "MEDIUM"
        assert "correct_answer" in t_data["questions"][0]
        assert "explanation" in t_data["questions"][0]
        print("[PASS] TEST 6: Teacher API retrieved full question payload with difficulty & count filters.")

        # TEST 7: Student Question Retrieval API Security Enforcement & Filtering
        print("\n--- TEST 7: Student Security Verification (Zero Data Leakage) ---")
        s_get_res = await ac.get(
            f"/api/v1/student/courses/{c1_id}/questions?concept_name=Binary%20Search",
            headers={"Authorization": f"Bearer {s1_token}"}
        )
        assert s_get_res.status_code == 200
        s_data = s_get_res.json()
        assert s_data["total"] == 2
        sq1 = s_data["questions"][0]
        # SECURITY CHECKS: correct_answer & explanation MUST NOT be present in dict
        assert "correct_answer" not in sq1
        assert "explanation" not in sq1
        assert "question" in sq1
        assert "options" in sq1 and len(sq1["options"]) == 4
        print("[PASS] TEST 7: Student API payload verified 100% secure: correct_answer and explanation strictly hidden.")

        # TEST 8: Student Answer Submission & Post-Submission Feedback
        print("\n--- TEST 8: Student Quiz Answer Submission ---")
        question_id = sq1["id"]
        # Submit correct option
        sub_res = await ac.post(
            f"/api/v1/student/questions/{question_id}/submit",
            headers={"Authorization": f"Bearer {s1_token}"},
            json={"selected_option": "O(log n)"}
        )
        assert sub_res.status_code == 200
        sub_data = sub_res.json()
        assert sub_data["is_correct"] is True
        assert sub_data["correct_answer"] == "O(log n)"
        assert len(sub_data["explanation"]) > 0
        print("[PASS] TEST 8: Answer submission correctly evaluated choice and returned feedback post-submission.")

        # TEST 9: Verification of Zero Changes to concept_segments Collection
        print("\n--- TEST 9: Zero Modification to Existing concept_segments Collection ---")
        concept_db_doc = await database.concept_segments.find_one({"course_id": c1_id})
        for seg in concept_db_doc.get("segments", []):
            assert "concept_id" not in seg
        print("[PASS] TEST 9: Verified existing concept_segments records were NOT modified and contain NO concept_id field.")

        # TEST 10: Teacher Ownership Authorization Guard
        print("\n--- TEST 10: Teacher Ownership Security Guard ---")
        # Register second teacher
        t2_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24QG2",
            "name": "Prof. Bob",
            "year": "2nd Year",
            "subject": "Algorithms",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t2_res.status_code == 201
        t2_token = t2_res.json()["access_token"]

        unauth_gen = await ac.post(
            f"/api/v1/teacher/courses/{c1_id}/questions/generate",
            headers={"Authorization": f"Bearer {t2_token}"},
            json={"concept_identifier": "Binary Search", "count": 2}
        )
        assert unauth_gen.status_code == 403
        print("[PASS] TEST 10: Teacher 2 access to Teacher 1 course questions rejected with 403 Forbidden.")

        # TEST 11: Clean Up All Test Data
        print("\n--- TEST 11: Purge All Test Data ---")
        await database.users.delete_many({"identifier": {"$in": ["T24QG1", "T24QG2", "S24QG1"]}})
        await database.teachers.delete_many({"teacher_id": {"$in": ["T24QG1", "T24QG2"]}})
        await database.students.delete_many({"roll_number": "S24QG1"})
        await database.courses.delete_one({"_id": ObjectId(c1_id)})
        await database.course_transcripts.delete_one({"course_id": c1_id})
        await database.concept_segments.delete_one({"course_id": c1_id})
        await database.questions.delete_many({"course_id": c1_id})
        print("[PASS] TEST 11: All test data purged cleanly.")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 11 PHASE 12 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase12_tests())
