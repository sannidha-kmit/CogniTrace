import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    
    courses = await db.courses.find({"course_name": {"": ["New Video Alpha", "New Video Beta"]}}).to_list(10)
    for c in courses:
        print(f"\nCourse: {c['course_name']} ({c['_id']})")
        print(f"Video URL: {c['youtube_url']}")
        tx = await db.course_transcripts.find_one({"course_id": str(c["_id"])})
        print(f"Transcript exists: {tx is not None}")
        print(f"Final Transcript status: {tx['status'] if tx else 'MISSING'}")
        if tx:
            print(f"Transcript length: {len(tx.get('segments', []))} segments")
            
        con = await db.concept_segments.find_one({"course_id": str(c["_id"])})
        print(f"Concepts available: {con is not None and con.get('status') == 'COMPLETED'}")
        
asyncio.run(check())
