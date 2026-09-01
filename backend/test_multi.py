import asyncio
import os
import sys
sys.path.append(os.getcwd())
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.services.question_service import QuestionService
from bson import ObjectId

async def test_telemetry():
    await connect_to_mongo()
    db = await get_database()
    
    daa_c = await db.courses.find_one({"course_name": "DAA"})
    course_id = str(daa_c['_id'])
    
    # create multiple pauses for student S99
    student_id = "S99"
    await db.interaction_events.delete_many({"StudentID": student_id})
    await db.questions.delete_many({"course_id": course_id, "difficulty": {"": True}})  # Clear previous
    
    # Look at concepts to pick correct timestamps
    conc = await db.concept_segments.find_one({"course_id": course_id})
    print("Available concepts:")
    for c in conc['segments']:
        print(f"- {c['Concept']} ({c['ConceptStart']} - {c['ConceptEnd']})")
    
    # insert 3 pause events in 3 different concepts
    await db.interaction_events.insert_many([
        {"CourseID": course_id, "StudentID": student_id, "EventType": "PAUSE", "EventTimestamp": "00:30"},
        {"CourseID": course_id, "StudentID": student_id, "EventType": "PAUSE", "EventTimestamp": "01:20"},
        {"CourseID": course_id, "StudentID": student_id, "EventType": "PAUSE", "EventTimestamp": "01:50"}
    ])
    
    print("\nCalling auto_generate...")
    try:
        res = await QuestionService.auto_generate_for_student_telemetry(course_id, student_id)
        print(f"Generated {len(res)} questions:")
        for q in res:
            print(f"- [{q.concept_name}] {q.question}")
    except Exception as e:
        print("Failed:", str(e))

    await close_mongo_connection()

asyncio.run(test_telemetry())
