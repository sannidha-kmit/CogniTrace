import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    
    courses = await db.courses.find().to_list(100)
    for c in courses:
        name = c.get('course_name', '')
        if name in ["New Video Alpha", "New Video Beta", "Test Video 4", "Test Video 3", "API Test Course 2"]:
            print(f"Deleting test record: {name} ({c['_id']})")
            course_id = str(c['_id'])
            await db.courses.delete_one({"_id": c['_id']})
            await db.course_transcripts.delete_one({"course_id": course_id})
            await db.transcription_jobs.delete_one({"course_id": course_id})
            await db.concept_segments.delete_one({"course_id": course_id})
            await db.concept_extraction_jobs.delete_one({"course_id": course_id})
            await db.question_bank.delete_one({"course_id": course_id})
            await db.questions.delete_many({"course_id": course_id})
            await db.telemetry.delete_many({"course_id": course_id})

asyncio.run(cleanup())
