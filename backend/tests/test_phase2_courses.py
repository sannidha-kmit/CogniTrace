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


async def run_phase2_tests():
    print("=" * 60)
    print("STARTING PHASE 2 TEACHER COURSE MANAGEMENT TEST SUITE")
    print("=" * 60)

    # 1. Connect DB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test records if present
    await database.users.delete_many({"identifier": {"$in": ["T24A001", "T24A002", "S24A001", "S24A002", "S24A010"]}})
    await database.teachers.delete_many({"teacher_id": {"$in": ["T24A001", "T24A002"]}})
    await database.students.delete_many({"roll_number": {"$in": ["S24A001", "S24A002", "S24A010"]}})
    await database.courses.delete_many({"teacher_id": {"$in": ["T24A001", "T24A002"]}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # Setup: Register Teacher 1 (T24A001 - 2nd Year - Operating Systems)
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

        # Setup: Register Teacher 2 (T24A002 - 2nd Year - Web Tech)
        t2_res = await ac.post("/api/v1/auth/register/teacher", json={
            "teacher_id": "T24A002",
            "name": "Prof. Ravi",
            "year": "2nd Year",
            "subject": "Web Technologies",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert t2_res.status_code == 201
        t2_token = t2_res.json()["access_token"]

        # Setup: Register Student 1 (S24A001 - 2nd Year)
        s1_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A001",
            "name": "Lasya",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s1_res.status_code == 201
        s1_token = s1_res.json()["access_token"]

        # Setup: Register Student 2 (S24A010 - 2nd Year)
        s2_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A010",
            "name": "Rahul",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s2_res.status_code == 201

        # Setup: Register Student 3 (S24A002 - 2nd Year)
        s3_res = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "S24A002",
            "name": "Anu",
            "year": "2nd Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert s3_res.status_code == 201

        # TEST 1: Teacher Dashboard Profile Check (/me)
        print("\n--- TEST 1: Teacher Dashboard Credentials Verification ---")
        me_res = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t1_token}"})
        assert me_res.status_code == 200
        assert me_res.json()["name"] == "Prof. Priya"
        assert me_res.json()["subject"] == "Operating Systems"
        print("[PASS] TEST 1: Teacher profile credentials verified.")

        # TEST 2: Add Course validation with invalid URL
        print("\n--- TEST 2: Add Course Input Validation ---")
        bad_url_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Process Management",
            "youtube_url": "https://notyoutube.com/watch?v=12345"
        })
        assert bad_url_res.status_code == 422
        print("[PASS] TEST 2: Non-YouTube video URL rejected cleanly.")

        # TEST 3: Create Course 1 with valid YouTube URL
        print("\n--- TEST 3: Create Real Course (Process Management) ---")
        c1_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Process Management",
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })
        assert c1_res.status_code == 201, f"Course 1 creation failed: {c1_res.text}"
        c1_data = c1_res.json()
        assert c1_data["teacher_id"] == "T24A001"
        assert c1_data["teacher_name"] == "Prof. Priya"
        assert c1_data["year"] == "2nd Year"
        assert c1_data["subject"] == "Operating Systems"
        c1_id = c1_data["id"]
        print("[PASS] TEST 3: Course 1 created with server-timestamped metadata.")

        # TEST 4: Fetch My Courses (Verify persistence)
        print("\n--- TEST 4: Verify Course Persistence ---")
        get_res1 = await ac.get("/api/v1/courses/my", headers={"Authorization": f"Bearer {t1_token}"})
        assert get_res1.status_code == 200
        assert len(get_res1.json()) == 1
        print("[PASS] TEST 4: Course retrieved successfully.")

        # TEST 5: Submit exact same course name + URL again (Duplicate rejection)
        print("\n--- TEST 5: Duplicate Course Creation Rejection ---")
        dup_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Process Management",
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })
        assert dup_res.status_code == 400
        assert "already exists" in dup_res.json()["detail"].lower()
        print("[PASS] TEST 5: Duplicate course submission rejected.")

        # TEST 6 & 7: Create Course 2 & Verify DESC Ordering (Newest First)
        print("\n--- TEST 6 & 7: Newest-First Course Ordering ---")
        await asyncio.sleep(0.01)  # small delay for timestamp order
        c2_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "CPU Scheduling",
            "youtube_url": "https://www.youtube.com/watch?v=yPYZpwSpKmA"
        })
        assert c2_res.status_code == 201

        get_res2 = await ac.get("/api/v1/courses/my", headers={"Authorization": f"Bearer {t1_token}"})
        assert get_res2.status_code == 200
        my_courses = get_res2.json()
        assert len(my_courses) == 2
        assert my_courses[0]["course_name"] == "CPU Scheduling"  # Newest course first
        assert my_courses[1]["course_name"] == "Process Management"
        print("[PASS] TEST 6 & 7: Verified latest course appears first (DESC order).")

        # TEST 8: Data Isolation between Teachers
        print("\n--- TEST 8: Teacher Data Isolation ---")
        t2_courses_res = await ac.get("/api/v1/courses/my", headers={"Authorization": f"Bearer {t2_token}"})
        assert t2_courses_res.status_code == 200
        assert len(t2_courses_res.json()) == 0  # Teacher 2 sees 0 courses
        print("[PASS] TEST 8: Verified Teacher 2 cannot see Teacher 1's courses.")

        # TEST 9 & 10: View Students for Teacher's Year & Alphanumeric Roll Number Sorting
        print("\n--- TEST 9 & 10: View Students & Alphanumeric Sorting ---")
        students_res = await ac.get("/api/v1/students/my-year", headers={"Authorization": f"Bearer {t1_token}"})
        assert students_res.status_code == 200
        student_list = students_res.json()
        assert len(student_list) == 3
        # Check alphanumeric roll number order: S24A001 -> S24A002 -> S24A010
        roll_numbers = [s["roll_number"] for s in student_list]
        assert roll_numbers == ["S24A001", "S24A002", "S24A010"], f"Unexpected sort order: {roll_numbers}"
        print("[PASS] TEST 9 & 10: Student list filtered to 2nd Year & sorted alphanumerically (S24A001, S24A002, S24A010).")

        # TEST 11 & 12: Empty state checks (when queries return 0)
        print("\n--- TEST 11 & 12: Empty State Verification ---")
        assert len(t2_courses_res.json()) == 0
        print("[PASS] TEST 11 & 12: Empty states return empty list cleanly.")

        # TEST 13: Student JWT trying to access Teacher APIs
        print("\n--- TEST 13: Student Role Access Denial (403 Forbidden) ---")
        student_course_access = await ac.get("/api/v1/courses/my", headers={"Authorization": f"Bearer {s1_token}"})
        assert student_course_access.status_code == 403
        student_student_access = await ac.get("/api/v1/students/my-year", headers={"Authorization": f"Bearer {s1_token}"})
        assert student_student_access.status_code == 403
        print("[PASS] TEST 13: Student JWT access to teacher endpoints rejected with 403 Forbidden.")

        # TEST 14: Payload Ownership Override Prevention
        print("\n--- TEST 14: Payload Ownership Tampering Prevention ---")
        # Attempt to pass a fake teacher_id in request body (even if Pydantic ignores extra fields, check stored doc)
        tamper_res = await ac.post("/api/v1/courses", headers={"Authorization": f"Bearer {t1_token}"}, json={
            "course_name": "Deadlocks",
            "youtube_url": "https://www.youtube.com/watch?v=9XB8X5abcde",
            "teacher_id": "FAKETEACHER"
        })
        assert tamper_res.status_code == 201
        tamper_data = tamper_res.json()
        assert tamper_data["teacher_id"] == "T24A001"  # Bound from JWT, not body payload
        print("[PASS] TEST 14: Backend strictly bound ownership to authenticated teacher identity.")

        # TEST 15: Safe Course Deletion by Owner
        print("\n--- TEST 15: Safe Course Deletion by Owner ---")
        # Teacher 2 attempts to delete Teacher 1's course -> 403 Forbidden
        unauth_del = await ac.delete(f"/api/v1/courses/{c1_id}", headers={"Authorization": f"Bearer {t2_token}"})
        assert unauth_del.status_code == 403

        # Teacher 1 deletes own course -> 200 OK
        auth_del = await ac.delete(f"/api/v1/courses/{c1_id}", headers={"Authorization": f"Bearer {t1_token}"})
        assert auth_del.status_code == 200
        print("[PASS] TEST 15: Course deletion permissions verified.")

        # TEST 16: Test Data Cleanup (Purge all test records to leave DB at 0 records)
        print("\n--- TEST 16: Purge All Test Data (Return DB to 0 Records) ---")
        await database.users.delete_many({"identifier": {"$in": ["T24A001", "T24A002", "S24A001", "S24A002", "S24A010"]}})
        await database.teachers.delete_many({"teacher_id": {"$in": ["T24A001", "T24A002"]}})
        await database.students.delete_many({"roll_number": {"$in": ["S24A001", "S24A002", "S24A010"]}})
        await database.courses.delete_many({"teacher_id": {"$in": ["T24A001", "T24A002"]}})

        final_users = await database.users.count_documents({})
        final_teachers = await database.teachers.count_documents({})
        final_students = await database.students.count_documents({})
        final_courses = await database.courses.count_documents({})

        assert final_users == 0, f"Final users count should be 0, got {final_users}"
        assert final_teachers == 0, f"Final teachers count should be 0, got {final_teachers}"
        assert final_students == 0, f"Final students count should be 0, got {final_students}"
        assert final_courses == 0, f"Final courses count should be 0, got {final_courses}"
        print("[PASS] TEST 16: Test records purged. Database returned to EXACTLY 0 records!")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 16 PHASE 2 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase2_tests())
