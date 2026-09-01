import asyncio
from httpx import AsyncClient

async def main():
    async with AsyncClient(base_url="http://localhost:8000") as ac:
        # We need a student token
        login_res = await ac.post("/api/v1/auth/login", data={"username": "S24QG1", "password": "Password123"})
        if login_res.status_code != 200:
            print("Login failed:", login_res.text)
            return
        token = login_res.json()["access_token"]
        
        # Call auto-generate
        print("Calling auto-generate...")
        res = await ac.post("/api/v1/student/courses/6a8d5f5e0dcc32a196810357/auto-generate", headers={"Authorization": f"Bearer {token}"})
        print("Status:", res.status_code)
        print("Response:", res.text)

asyncio.run(main())
