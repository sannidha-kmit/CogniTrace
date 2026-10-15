import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    db_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = db_client.cognitrace_db
    print(await db.students.find_one({}))

asyncio.run(run())
