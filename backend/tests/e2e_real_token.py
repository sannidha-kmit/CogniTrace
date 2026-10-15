import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
import os, sys
from datetime import datetime, timezone, timedelta
sys.path.append(os.getcwd())
from app.core.config import settings

async def run():
    # Setup DB for clean test
    db_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = db_client.cognitrace_db
    daa = await db.courses.find_one({"course_name": "DAA"})
    os_c = await db.courses.find_one({"course_name": "goal of os"})
    daa_id = str(daa["_id"])
    os_id = str(os_c["_id"])
    
    # Clean telemetry and questions for S24A001
    await db.interaction_events.delete_many({"StudentID": "S24A001"})
    
    # We also delete the generated questions from DAA so we can see exact generation
    await db.questions.delete_many({"course_id": daa_id})

    # Direct token generation
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    student = await db.students.find_one({"roll_number": "S24A001"})
    to_encode = {"sub": student["roll_number"], "identifier": student["roll_number"], "role": "student", "exp": expire}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=120.0) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"--- DAA VIDEO E2E TEST ---")
        # Action 1: Start video, pause at Topic 1
        print("Student pauses at 00:05 (Concept 1: Algorithm Definition & Properties)")
        await client.post("/api/v1/student/events", headers=headers, json={"course_id": daa_id, "event_type": "PAUSE", "event_timestamp": "00:05", "event_duration": 5.0})
        
        # Action 2: Resume, move forward, pause at Topic 2
        print("Student moves forward and pauses at 04:00 (Concept 2: Time Complexity)")
        await client.post("/api/v1/student/events", headers=headers, json={"course_id": daa_id, "event_type": "PAUSE", "event_timestamp": "04:00", "event_duration": 3.0})
        
        # Action 3: Move backward, pause at Topic 3
        print("Student moves backward and pauses at 01:30 (Concept 3: Search Fundamentals)")
        await client.post("/api/v1/student/events", headers=headers, json={"course_id": daa_id, "event_type": "PAUSE", "event_timestamp": "01:30", "event_duration": 4.0})
        
        # Action 4: Pause again at Concept 2
        print("Student jumps back to Time Complexity and pauses at 04:10 (Duplicate concept)")
        await client.post("/api/v1/student/events", headers=headers, json={"course_id": daa_id, "event_type": "PAUSE", "event_timestamp": "04:10", "event_duration": 2.0})

        print("\nClicking 'Generate Questions (Pause-Based)'...")
        res = await client.post(f"/api/v1/student/courses/{daa_id}/auto-generate", headers=headers)
        data = res.json()
        print(f"Total Questions Generated: {data.get('total', 0)}")
        
        if "questions" in data:
            # Group by concept
            concepts_found = set()
            for q in data["questions"]:
                concepts_found.add(q["concept_name"])
                print(f" - [{q['concept_name']}] {q['question']}")
                
            print(f"\nUnique Concepts Identified: {len(concepts_found)}")
            print(f"Concepts Mapped: {concepts_found}")
        else:
            print(data)
        
        print("\n--- OS VIDEO E2E TEST (Regression check) ---")
        # Ensure OS works
        await db.interaction_events.delete_many({"CourseID": os_id, "StudentID": "S24A001"})
        await db.questions.delete_many({"course_id": os_id})
        await client.post("/api/v1/student/events", headers=headers, json={"course_id": os_id, "event_type": "PAUSE", "event_timestamp": "00:10", "event_duration": 5.0})
        os_res = await client.post(f"/api/v1/student/courses/{os_id}/auto-generate", headers=headers)
        print(f"OS Generated: {os_res.json().get('total', 0)} questions.")
        if "questions" in os_res.json():
            for q in os_res.json()["questions"]:
                print(f" - [{q['concept_name']}] {q['question']}")

asyncio.run(run())
