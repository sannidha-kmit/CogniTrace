import httpx
import asyncio
from datetime import datetime

async def run_e2e():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Login or Register a new student
        res = await client.post("/api/v1/auth/register/student", json={
            "identifier": "S99_E2E",
            "password": "password",
            "name": "E2E Student",
            "year": 2
        })
        if res.status_code == 400 and "already registered" in res.text:
            res = await client.post("/api/v1/auth/login", json={"identifier": "S99_E2E", "password": "password"})
        
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Courses
        res = await client.get("/api/v1/student/courses", headers=headers)
        courses = res.json()
        daa_course = next((c for c in courses if c["course_name"] == "DAA"), None)
        os_course = next((c for c in courses if c["course_name"] == "Operating System Scheduling & Memory" or "os" in c["course_name"].lower()), None)
        
        print(f"DAA Course ID: {daa_course['id']}")
        
        # 3. Clear existing questions & telemetry (to make it a fresh test)
        # We can't clear from API easily, so we will use motor directly in the script for cleanup before test
        
