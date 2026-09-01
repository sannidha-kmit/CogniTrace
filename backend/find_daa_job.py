import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    job1 = await db.transcription_jobs.find_one({"course_name": "DAA"})
    job2 = await db.transcription_jobs.find_one({"youtube_url": "https://youtu.be/u8JZ9gU5o4g?si=Zz1bNGuWfUB0GLN1"})
    print("job by name:", job1)
    print("job by url:", job2)
    
asyncio.run(check())
