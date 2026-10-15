import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    daa = await db.course_transcripts.find_one({"course_name": "DAA"})
    print("DAA Transcript status:", daa.get("status") if daa else "MISSING")
    
asyncio.run(check())
