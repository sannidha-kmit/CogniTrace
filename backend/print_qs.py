import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timedelta, timezone
import requests

async def get_token(identifier, role):
    import os, sys
    sys.path.append(os.getcwd())
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"sub": identifier, "identifier": identifier, "role": role, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def run():
    token = await get_token("S24A001", "student")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Alpha
    print("Video Alpha Questions:")
    res = requests.post("http://localhost:8000/api/v1/student/courses/6a95a31eda7042bd6c0a29ac/auto-generate", headers=headers)
    for q in res.json().get("questions", []):
        print("-", q["question"])
        
    # Beta
    print("\nVideo Beta Questions:")
    res = requests.post("http://localhost:8000/api/v1/student/courses/6a95a32fda7042bd6c0a29b0/auto-generate", headers=headers)
    for q in res.json().get("questions", []):
        print("-", q["question"])

asyncio.run(run())
