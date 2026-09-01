import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    
    courses = await db.courses.find().sort('created_at', -1).limit(2).to_list(length=10)
    for c in courses:
        cid = str(c['_id'])
        print(f"Course: {c['course_name']} ({cid})")
        tx = await db.course_transcripts.find_one({'course_id': cid})
        job = await db.transcription_jobs.find_one({'course_id': cid})
        print(f"  Transcript status: {tx.get('status') if tx else 'MISSING'}")
        print(f"  Job status: {job.get('status') if job else 'MISSING'}")
        
asyncio.run(check())
