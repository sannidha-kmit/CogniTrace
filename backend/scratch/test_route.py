import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/student/courses/12345/auto-generate")
        print("Status:", res.status_code)
        print("Body:", res.text)

asyncio.run(main())
