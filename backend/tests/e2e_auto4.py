import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timezone, timedelta
import os, sys
sys.path.append(os.getcwd())
from app.core.config import settings

async def e2e_student_part():
    client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=120.0)
    db_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = db_client.cognitrace_db

    course_id = "6a95b26395cea96d640e1f2a"
    
    print("--- Waiting for Automated Processing ---", flush=True)
    tx_ready = False
    concepts_ready = False
    
    for _ in range(90): 
        tx_doc = await db.course_transcripts.find_one({"course_id": course_id})
        cp_doc = await db.concept_segments.find_one({"course_id": course_id})
        
        tx_status = tx_doc.get("status") if tx_doc else "NOT_STARTED"
        cp_status = cp_doc.get("status") if cp_doc else "NOT_STARTED"
        
        print(f"Status - Transcript: {tx_status}, Concepts: {cp_status}", flush=True)
        
        if tx_status == "COMPLETED":
            tx_ready = True
        if cp_status == "COMPLETED":
            concepts_ready = True
            print(f"Extraction successful! Extracted {len(cp_doc.get('segments', []))} concepts.", flush=True)
            break
            
        await asyncio.sleep(2)
        
    if not concepts_ready:
        print("Test failed: automated pipeline did not finish in time.", flush=True)
        return
        
    print("\n--- Student Setup ---")
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    s_token = jwt.encode({"sub": "S24A001", "identifier": "S24A001", "role": "student", "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    s_headers = {"Authorization": f"Bearer {s_token}"}
    
    print("\n--- Student Interaction Telemetry ---")
    await db.interaction_events.delete_many({"StudentID": "S24A001", "CourseID": course_id})
    await db.questions.delete_many({"course_id": course_id})
    
    print("Student pauses at 00:30 (Topic A)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "00:30", "event_duration": 4.0})
    
    print("Student moves forward and pauses at 01:45 (Topic B)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "01:45", "event_duration": 2.0})
    
    print("Student moves backward and pauses at 00:35 (Topic A again)")
    await client.post("/api/v1/student/events", headers=s_headers, json={"course_id": course_id, "event_type": "PAUSE", "event_timestamp": "00:35", "event_duration": 5.0})
    
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

asyncio.run(e2e_student_part())
