import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import datetime

async def inspect_dates():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.cognitrace_db
    
    tx = await db.course_transcripts.find_one({"course_id": "6a95aefcda7042bd6c0a29f9"})
    if tx:
        print("DS Transcript Updated At:", tx.get("updated_at"))
        
asyncio.run(inspect_dates())
