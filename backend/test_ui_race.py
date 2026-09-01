import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timezone, timedelta
import os, sys
sys.path.append(os.getcwd())
from app.core.config import settings

async def real_frontend_simulation():
    client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=120.0)
    db_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = db_client.cognitrace_db

    # Constants
    student_id = "S24A001"
    course_ds = "6a95aefcda7042bd6c0a29f9"
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    s_token = jwt.encode({"sub": student_id, "identifier": student_id, "role": "student", "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    headers = {"Authorization": f"Bearer {s_token}"}
    
    # Cleanup before tests
    await db.interaction_events.delete_many({"StudentID": student_id})
    await db.questions.delete_many({"course_id": course_ds})
    
    print("\n=======================================================")
    print("SIMULATING FRONTEND RACE CONDITION FIX")
    print("=======================================================")
    
    # User clicks pause at 01:24
    print("1. Video is paused by student at 01:24.")
    # In the new code, this fires PAUSE immediately!
    await client.post("/api/v1/student/events", headers=headers, json={"course_id": course_ds, "event_type": "PAUSE", "event_timestamp": "01:24", "event_duration": None})
    
    # User clicks Generate Questions IMMEDIATELY while video is still paused (no RESUME/PAUSE_END event sent yet)
    print("2. Student clicks 'Generate Questions (Pause-Based)' immediately while paused.")
    res = await client.post(f"/api/v1/student/courses/{course_ds}/auto-generate", headers=headers)
    data = res.json()
    
    if res.status_code == 200 and "questions" in data and len(data["questions"]) > 0:
        concepts = set(q["concept_name"] for q in data["questions"])
        print(f"PASS: Question Generation succeeded! The endpoint found the PAUSE event at 01:24.")
        print(f"Generated {data['total']} questions covering concepts: {concepts}")
        for q in data["questions"]:
            print(f" - [{q['concept_name']}] {q['question']}")
    else:
        print("FAIL: Expected questions but got:", res.status_code, res.text)

    print("\n3. Verifying the database stored the exact pause event...")
    db_events = await db.interaction_events.find({"StudentID": student_id, "CourseID": course_ds}).to_list(length=10)
    for ev in db_events:
        print(f"DB RECORD: Type={ev['EventType']}, Timestamp={ev.get('EventTimestamp')}, Course={ev['CourseID']}")

    await client.aclose()

asyncio.run(real_frontend_simulation())
