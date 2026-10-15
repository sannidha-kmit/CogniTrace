import asyncio
import jwt
from datetime import datetime, timedelta, timezone
import requests

async def get_token():
    import os, sys
    sys.path.append(os.getcwd())
    from app.core.config import settings
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"sub": "T24A001", "identifier": "T24A001", "role": "teacher", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

token = asyncio.run(get_token())
headers = {"Authorization": f"Bearer {token}"}

res = requests.post("http://localhost:8000/api/v1/teacher/courses/6a955a3cd0c51643561d77f2/transcript/generate", headers=headers)
print("Generate response:", res.status_code, res.text)
