import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timezone, timedelta
import os, sys
sys.path.append(os.getcwd())
from app.core.config import settings

async def e2e_new_video():
    client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=120.0)
    db_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = db_client.cognitrace_db

    print("--- 1. Login Teacher (T24A001) ---")
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    t_token = jwt.encode({"sub": "T24A001", "identifier": "T24A001", "role": "teacher", "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    t_headers = {"Authorization": f"Bearer {t_token}"}

    print("--- 2. Add New Video ---")
    res = await client.post("/api/v1/courses", headers=t_headers, json={
        "course_name": "Networking Basics Auto Test 3",
        "subject": "Computer Networks",
        "description": "A quick test on networking.",
        "year": 2,
        "youtube_url": "https://www.youtube.com/watch?v=IPvYjXCsTg8" 
    })
    
    if res.status_code != 201:
        print("Course creation failed:", res.text)
        return
        
    course = res.json()
    course_id = course["id"]
    print(f"Created Course ID: {course_id}")

    print("--- 3. Waiting for Automated Processing ---")
    tx_ready = False
    concepts_ready = False
    
    for _ in range(90): 
        tx_doc = await db.course_transcripts.find_one({"course_id": course_id})
        cp_doc = await db.concept_segments.find_one({"course_id": course_id})
        
        tx_status = tx_doc.get("status") if tx_doc else "NOT_STARTED"
        cp_status = cp_doc.get("status") if cp_doc else "NOT_STARTED"
        
        print(f"Status - Transcript: {tx_status}, Concepts: {cp_status}")
        
        if tx_status == "COMPLETED":
            tx_ready = True
        if cp_status == "COMPLETED":
            concepts_ready = True
            print(f"Extraction successful! Extracted {len(cp_doc.get('segments', []))} concepts.")
            break
            
        await asyncio.sleep(2)
        
    if not concepts_ready:
        print("Test failed: automated pipeline did not finish in time.")
        return
        
    print("\n--- 4. Student Setup ---")
    s_token = jwt.encode({"sub": "S24A001", "identifier": "S24A001", "role": "student", "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    s_headers = {"Authorization": f"Bearer {s_token}"}
    
    print("\n--- 5. Student Interaction Telemetry ---")
    await db.interaction_events.delete_many({"StudentID": "S24A001", "CourseID": course_id})
    await db.questions.delete_many({"course_id": course_id})
    
    print("Student pauses at 01:20 (Topic A)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "01:20", "event_duration": 4.0})
    
    print("Student moves forward and pauses at 03:45 (Topic B)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "03:45", "event_duration": 2.0})
    
    print("Student moves backward and pauses at 01:25 (Topic A again)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "01:25", "event_duration": 5.0})
    
    print("\n--- 6. Generate Questions ---")
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

asyncio.run(e2e_new_video())
