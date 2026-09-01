import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
from datetime import datetime, timedelta, timezone

async def get_token():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    user = await db.users.find_one({"identifier": "T24A001"})
    
    import os, sys
    sys.path.append(os.getcwd())
    from app.core.config import settings
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"sub": user["identifier"], "role": user["role"], "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    print(encoded_jwt)

asyncio.run(get_token())
