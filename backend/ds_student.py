import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timezone, timedelta
import os, sys
sys.path.append(os.getcwd())
from app.core.config import settings

async def ds_student_test():
    client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=120.0)
    db_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = db_client.cognitrace_db

    course_id = "6a95aefcda7042bd6c0a29f9"
    
    print("\n--- Student Setup ---")
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    s_token = jwt.encode({"sub": "S24A001", "identifier": "S24A001", "role": "student", "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    s_headers = {"Authorization": f"Bearer {s_token}"}
    
    print("\n--- Student Interaction Telemetry ---")
    await db.interaction_events.delete_many({"StudentID": "S24A001", "CourseID": course_id})
    await db.questions.delete_many({"course_id": course_id})
    
    # Let's pause at specific times in the Data Science video
    print("Student pauses at 00:30 (Topic A)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "00:30", "event_duration": 4.0})
    
    print("Student moves forward and pauses at 02:45 (Topic B)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "02:45", "event_duration": 2.0})
    
    print("\n--- Generate Questions ---")
    res = await client.post(f"/api/v1/student/courses/{course_id}/auto-generate", headers=s_headers)
    data = res.json()
    
    if "questions" in data:
        concepts = set(q["concept_name"] for q in data["questions"])
        print(f"\nFinal Result:")
        print(f"Total Questions Generated: {data['total']}")
        print(f"Concepts Used: {concepts}")
        for q in data["questions"]:
            print(f" - [{q['concept_name']}] {q['question']}")
    else:
        print("Generation failed:", data)

    await client.aclose()

asyncio.run(ds_student_test())
