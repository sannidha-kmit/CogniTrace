import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import asyncio
import sys
import logging
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.core.config import settings
from app.core.security import verify_password
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_phase1")


async def run_phase1_tests():
    print("=" * 60)
    print("STARTING PHASE 1 AUTHENTICATION & SECURITY VERIFICATION SUITE")
    print("=" * 60)

    # 1. Connect to MongoDB
    await connect_to_mongo()
    if db.client is None:
        print("ERROR: Cannot connect to MongoDB server for testing.")
        sys.exit(1)

    database = db.client[settings.MONGODB_DB_NAME]

    # Pre-clean test identifiers if present
    await database.users.delete_many({"identifier": {"$in": ["S24A001", "T24A001"]}})
    await database.students.delete_many({"roll_number": "S24A001"})
    await database.teachers.delete_many({"teacher_id": "T24A001"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # TEST 1: Register real student (S24A001)
        print("\n--- TEST 1: Register Real Student (S24A001) ---")
        student_payload = {
            "roll_number": "S24A001",
            "name": "Alex Student",
            "year": "2nd Year",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123"
        }
        res1 = await ac.post("/api/v1/auth/register/student", json=student_payload)
        assert res1.status_code == 201, f"Test 1 Failed: {res1.text}"
        data1 = res1.json()
        assert "access_token" in data1
        assert data1["user"]["identifier"] == "S24A001"
        assert data1["user"]["role"] == "student"

        # Verify DB password hash & no plain password
        user_in_db = await database.users.find_one({"identifier": "S24A001"})
        assert user_in_db is not None
        assert "password" not in user_in_db
        assert "password_hash" in user_in_db
        assert verify_password("SecurePassword123", user_in_db["password_hash"])
        student_jwt = data1["access_token"]
        print("[PASS] TEST 1: Student registered, password hashed, JWT issued.")

        # TEST 2: Register duplicate student identifier (S24A001)
        print("\n--- TEST 2: Duplicate Student Identifier Prevention ---")
        res2 = await ac.post("/api/v1/auth/register/student", json=student_payload)
        assert res2.status_code == 400, f"Test 2 Failed: Status should be 400, got {res2.status_code}"
        assert "already exists" in res2.json()["detail"].lower()
        print("[PASS] TEST 2: Duplicate student registration rejected.")

        # TEST 3: Register real teacher (T24A001)
        print("\n--- TEST 3: Register Real Teacher (T24A001) ---")
        teacher_payload = {
            "teacher_id": "T24A001",
            "name": "Prof. Sarah Connor",
            "year": "3rd Year",
            "subject": "Computer Networks",
            "password": "TeacherPassword123",
            "confirm_password": "TeacherPassword123"
        }
        res3 = await ac.post("/api/v1/auth/register/teacher", json=teacher_payload)
        assert res3.status_code == 201, f"Test 3 Failed: {res3.text}"
        data3 = res3.json()
        assert data3["user"]["identifier"] == "T24A001"
        assert data3["user"]["role"] == "teacher"
        assert data3["user"]["subject"] == "Computer Networks"
        teacher_jwt = data3["access_token"]
        print("[PASS] TEST 3: Teacher registered successfully.")

        # TEST 4: Login with valid student credentials
        print("\n--- TEST 4: Login Valid Student ---")
        res4 = await ac.post("/api/v1/auth/login", json={"identifier": "S24A001", "password": "SecurePassword123"})
        assert res4.status_code == 200, f"Test 4 Failed: {res4.text}"
        assert res4.json()["user"]["role"] == "student"
        print("[PASS] TEST 4: Student logged in cleanly.")

        # TEST 5: Login with valid teacher credentials
        print("\n--- TEST 5: Login Valid Teacher ---")
        res5 = await ac.post("/api/v1/auth/login", json={"identifier": "T24A001", "password": "TeacherPassword123"})
        assert res5.status_code == 200, f"Test 5 Failed: {res5.text}"
        assert res5.json()["user"]["role"] == "teacher"
        print("[PASS] TEST 5: Teacher logged in cleanly.")

        # TEST 6: Login with nonexistent identifier
        print("\n--- TEST 6: Login Nonexistent Identifier ---")
        res6 = await ac.post("/api/v1/auth/login", json={"identifier": "S999999", "password": "AnyPassword"})
        assert res6.status_code == 401, f"Test 6 Failed: Status should be 401, got {res6.status_code}"
        print("[PASS] TEST 6: Nonexistent account login rejected.")

        # TEST 7: Login with wrong password
        print("\n--- TEST 7: Login Wrong Password ---")
        res7 = await ac.post("/api/v1/auth/login", json={"identifier": "S24A001", "password": "WrongPassword"})
        assert res7.status_code == 401, f"Test 7 Failed: Status should be 401, got {res7.status_code}"
        print("[PASS] TEST 7: Invalid password login rejected.")

        # TEST 8: Student profile access via /me
        print("\n--- TEST 8: Student Access /me Endpoint ---")
        res8 = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {student_jwt}"})
        assert res8.status_code == 200
        assert res8.json()["identifier"] == "S24A001"
        assert res8.json()["role"] == "student"
        print("[PASS] TEST 8: Student authenticated /me endpoint verified.")

        # TEST 9: Teacher profile access via /me
        print("\n--- TEST 9: Teacher Access /me Endpoint ---")
        res9 = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {teacher_jwt}"})
        assert res9.status_code == 200
        assert res9.json()["identifier"] == "T24A001"
        assert res9.json()["role"] == "teacher"
        print("[PASS] TEST 9: Teacher authenticated /me endpoint verified.")

        # TEST 10: Invalid / Expired Token Access
        print("\n--- TEST 10: Invalid JWT Authorization Rejection ---")
        res10 = await ac.get("/api/v1/auth/me", headers={"Authorization": "Bearer InvalidTokenHeaderString"})
        assert res10.status_code == 401
        print("[PASS] TEST 10: Invalid token access rejected with 401.")

        # TEST 11: Cross-role identifier registration prevention (S identifier for teacher or vice versa)
        print("\n--- TEST 11: Format Mismatch Prevention ---")
        res11 = await ac.post("/api/v1/auth/register/student", json={
            "roll_number": "T24A001",
            "name": "Fake Student",
            "year": "1st Year",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        assert res11.status_code == 422, f"Expected 422 for format mismatch, got {res11.status_code}"
        print("[PASS] TEST 11: Roll Number format mismatch rejected.")

        # TEST 12: Database Persistence & Record Count Check
        print("\n--- TEST 12: Verify Database Counts ---")
        users_count = await database.users.count_documents({})
        students_count = await database.students.count_documents({})
        teachers_count = await database.teachers.count_documents({})
        assert users_count == 2, f"Users count should be 2, got {users_count}"
        assert students_count == 1, f"Students count should be 1, got {students_count}"
        assert teachers_count == 1, f"Teachers count should be 1, got {teachers_count}"
        print("[PASS] TEST 12: Verified exactly 2 registered accounts in MongoDB.")

        # TEST 13: Clean up test accounts after verification
        print("\n--- TEST 13: Clean Up Test Accounts (Return DB to 0 Records) ---")
        await database.users.delete_many({"identifier": {"$in": ["S24A001", "T24A001"]}})
        await database.students.delete_many({"roll_number": "S24A001"})
        await database.teachers.delete_many({"teacher_id": "T24A001"})

        final_users = await database.users.count_documents({})
        final_students = await database.students.count_documents({})
        final_teachers = await database.teachers.count_documents({})

        assert final_users == 0, f"Final users should be 0, got {final_users}"
        assert final_students == 0, f"Final students should be 0, got {final_students}"
        assert final_teachers == 0, f"Final teachers should be 0, got {final_teachers}"
        print("[PASS] TEST 13: All test records purged. Database returned to EXACTLY 0 records!")

    await close_mongo_connection()
    print("\n" + "=" * 60)
    print("ALL 13 PHASE 1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase1_tests())
