import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    
    courses = await db.courses.find({"_id": {"": ["6a95a31eda7042bd6c0a29ac", "6a95a32fda7042bd6c0a29b0"]}}).to_list(10)
    print("Found courses:", len(courses))
    
asyncio.run(check())
