import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        res = await client.post("/api/v1/auth/login", json={"identifier": "S24A001", "password": "password"})
        print(res.text)

asyncio.run(run())
