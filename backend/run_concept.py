import asyncio
import os
import sys
import time
sys.path.append(os.getcwd())
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.workers.concept_worker import process_concept_job

async def fix_daa():
    await connect_to_mongo()
    db = await get_database()
    
    daa_c = await db.courses.find_one({"_id": "6a955a3cd0c51643561d77f2"})
    # wait, ObjectId
    
asyncio.run(fix_daa())
