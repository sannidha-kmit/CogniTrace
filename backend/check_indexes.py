import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    print("Jobs Indexes:", await db.transcription_jobs.index_information())
    print("Transcripts Indexes:", await db.course_transcripts.index_information())
    
asyncio.run(check())
