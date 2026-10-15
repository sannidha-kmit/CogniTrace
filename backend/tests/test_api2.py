import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timedelta, timezone
import requests

async def get_token():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    user = await db.users.find_one({"identifier": "T24A001"})
    
    import os, sys
    sys.path.append(os.getcwd())
    from app.core.config import settings
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"sub": user["identifier"], "identifier": user["identifier"], "role": user["role"], "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

token = asyncio.run(get_token())
headers = {"Authorization": f"Bearer {token}"}

res = requests.post("http://localhost:8000/api/v1/courses", 
    headers=headers,
    json={"course_name": "API Test Course 2", "youtube_url": "https://www.youtube.com/watch?v=M7FIvfx5J10"}
)
print("Create response:", res.status_code, res.text)
