import requests
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timedelta, timezone
import time

def get_token(identifier, role):
    import os, sys
    sys.path.append(os.getcwd())
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"sub": identifier, "identifier": identifier, "role": role, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def test_new_video(name, url):
    print(f"\n--- Testing Video: {name} ---")
    token = get_token("T24A001", "teacher")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create course
    res = requests.post("http://localhost:8000/api/v1/courses", 
        headers=headers,
        json={"course_name": name, "youtube_url": url}
    )
    if res.status_code != 201:
        print("Create failed:", res.status_code, res.text)
        return
    
    course_id = res.json()["id"]
    print("Course created:", course_id)
    
    # Check status
    for _ in range(10):
        res = requests.get(f"http://localhost:8000/api/v1/teacher/courses/{course_id}/transcript/status", headers=headers)
        print("Status:", res.json()["status"], res.json()["stage"])
        if res.json()["status"] == "COMPLETED":
            break
        time.sleep(2)

test_new_video("Test Video 3", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
test_new_video("Test Video 4", "https://www.youtube.com/watch?v=9bZkp7q19f0")
