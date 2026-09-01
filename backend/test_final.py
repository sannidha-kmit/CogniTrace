import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timezone, timedelta
import os, sys
sys.path.append(os.getcwd())
from app.core.config import settings

async def run_final_tests():
    client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=120.0)
    db_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = db_client.cognitrace_db

    # Constants
    student_id = "S24A001"
    course_ds = "6a95aefcda7042bd6c0a29f9"
    course_api = "6a95b26395cea96d640e1f2a"
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    s_token = jwt.encode({"sub": student_id, "identifier": student_id, "role": "student", "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    headers = {"Authorization": f"Bearer {s_token}"}
    
    # Cleanup before tests
    await db.interaction_events.delete_many({"StudentID": student_id})
    await db.questions.delete_many({"course_id": {"": [course_ds, course_api]}})
    
    print("\n=======================================================")
    print("TEST 1: Open course, NO pause, Generate Questions")
    print("=======================================================")
    res = await client.post(f"/api/v1/student/courses/{course_ds}/auto-generate", headers=headers)
    if res.status_code == 400:
        print("PASS (Expected 400):", res.json().get("detail"))
    else:
        print("FAIL: Expected 400 Bad Request but got:", res.status_code, res.json())
        
    print("\n=======================================================")
    print("TEST 2: Watch -> pause at X -> Generate Questions")
    print("=======================================================")
    await client.post("/api/v1/student/events", headers=headers, json={"course_id": course_ds, "event_type": "PAUSE", "event_timestamp": "00:30", "event_duration": 4.0})
    res = await client.post(f"/api/v1/student/courses/{course_ds}/auto-generate", headers=headers)
    data = res.json()
    if "questions" in data and len(data["questions"]) > 0:
        concepts = set(q["concept_name"] for q in data["questions"])
        print(f"PASS: Generated {data['total']} questions for concepts: {concepts}")
        for q in data["questions"]:
            print(f" - [{q['concept_name']}] {q['question']}")
    else:
        print("FAIL:", res.text)
        
    print("\n=======================================================")
    print("TEST 3: Pause at X -> backward 10s -> pause again")
    print("=======================================================")
    await db.interaction_events.delete_many({"StudentID": student_id, "CourseID": course_api})
    await db.questions.delete_many({"course_id": course_api})
    
    await client.post("/api/v1/student/events", headers=headers, json={"course_id": course_api, "event_type": "PAUSE", "event_timestamp": "01:20", "event_duration": 2.0})
    # backward 10s logic sends a SEEK_BACKWARD at the new timestamp!
    await client.post("/api/v1/student/events", headers=headers, json={"course_id": course_api, "event_type": "SEEK_BACKWARD", "event_timestamp": "01:10", "event_duration": None})
    await client.post("/api/v1/student/events", headers=headers, json={"course_id": course_api, "event_type": "PAUSE", "event_timestamp": "01:10", "event_duration": 4.0})
    
    res = await client.post(f"/api/v1/student/courses/{course_api}/auto-generate", headers=headers)
    data = res.json()
    if "questions" in data and len(data["questions"]) > 0:
        concepts = set(q["concept_name"] for q in data["questions"])
        print(f"PASS: Generated {data['total']} questions (duplicates controlled) for concepts: {concepts}")
        for q in data["questions"]:
            print(f" - [{q['concept_name']}] {q['question']}")
    else:
        print("FAIL:", res.text)
        
    print("\n=======================================================")
    print("TEST 4: Pause at two different concepts")
    print("=======================================================")
    # Clean DS
    await db.interaction_events.delete_many({"StudentID": student_id, "CourseID": course_ds})
    await db.questions.delete_many({"course_id": course_ds})
    
    await client.post("/api/v1/student/events", headers=headers, json={"course_id": course_ds, "event_type": "PAUSE", "event_timestamp": "00:30", "event_duration": 2.0})
    await client.post("/api/v1/student/events", headers=headers, json={"course_id": course_ds, "event_type": "PAUSE", "event_timestamp": "03:15", "event_duration": 2.0})
    
    res = await client.post(f"/api/v1/student/courses/{course_ds}/auto-generate", headers=headers)
    data = res.json()
    if "questions" in data and len(data["questions"]) > 0:
        concepts = set(q["concept_name"] for q in data["questions"])
        print(f"PASS: Generated {data['total']} questions covering {len(concepts)} concepts: {concepts}")
        for q in data["questions"]:
            print(f" - [{q['concept_name']}] {q['question']}")
    else:
        print("FAIL:", res.text)
        
    print("\n=======================================================")
    print("TEST 5: Two different courses/videos (Course Isolation)")
    print("=======================================================")
    # The API course already has questions from Test 3. The DS course has questions from Test 4.
    res_ds = await client.post(f"/api/v1/student/courses/{course_ds}/auto-generate", headers=headers)
    res_api = await client.post(f"/api/v1/student/courses/{course_api}/auto-generate", headers=headers)
    
    ds_data = res_ds.json()
    api_data = res_api.json()
    
    ds_concepts = set(q["concept_name"] for q in ds_data["questions"])
    api_concepts = set(q["concept_name"] for q in api_data["questions"])
    
    if ds_concepts.isdisjoint(api_concepts):
        print(f"PASS: Course isolation successful! DS concepts ({ds_concepts}) did NOT mix with API concepts ({api_concepts}).")
    else:
        print("FAIL: Courses mixed up!")

    print("\n=======================================================")
    print("TEST 6: Repeat generation (no unnecessary duplicates)")
    print("=======================================================")
    # We already requested DS generation above in Test 5. Total should be the same as Test 4!
    if ds_data['total'] == data['total']:
        print(f"PASS: Total questions remained {ds_data['total']} after repeat generation.")
    else:
        print(f"FAIL: Duplicates created! Test 4 had {data['total']}, Test 6 has {ds_data['total']}.")

    await client.aclose()

asyncio.run(run_final_tests())
