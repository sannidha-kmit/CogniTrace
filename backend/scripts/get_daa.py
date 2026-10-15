import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    daa = await db.courses.find_one({"course_name": "DAA"})
    if daa:
        print(daa)
        
asyncio.run(check())
