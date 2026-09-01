import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    print("Collections:", await db.list_collection_names())

asyncio.run(check())
