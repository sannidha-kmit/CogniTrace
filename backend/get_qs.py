import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def get_q():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    
    courses = await db.courses.find({"_id": {"": [ObjectId("6a95a31eda7042bd6c0a29ac"), ObjectId("6a95a32fda7042bd6c0a29b0")]}}).to_list(10)
    for c in courses:
        print(f"\nCourse: {c['course_name']}")
        tx = await db.course_transcripts.find_one({"course_id": str(c["_id"])})
        print(f"Transcript segments: {len(tx.get('segments', []))}")
        
        q = await db.question_bank.find_one({"course_id": str(c["_id"])})
        if q:
            print("Questions generated:")
            for m in q.get('mcqs', [])[:2]:
                print(f"- {m['question']}")
                
asyncio.run(get_q())
