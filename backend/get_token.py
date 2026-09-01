import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import jwt
from datetime import datetime, timedelta, timezone

async def run():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.cognitrace_db
    daa = await db.courses.find_one({"_id": ObjectId("6a955a3cd0c51643561d77f2")})
    print(daa["teacher_id"])
    
    import sys, os
    sys.path.append(os.getcwd())
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"sub": daa["teacher_id"], "identifier": daa["teacher_id"], "role": "teacher", "exp": expire}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    print(token)

asyncio.run(run())
