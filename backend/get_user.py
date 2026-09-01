import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    user = await db.users.find_one({"role": "teacher"})
    if user:
        print(user)
        
asyncio.run(check())
