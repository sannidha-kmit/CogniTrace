import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clear():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.cognitrace_db
    # Find the 4-hour video
    bad_course = await db.courses.find_one({"youtube_url": "https://www.youtube.com/watch?v=IPvYjXCsTg8"})
    if bad_course:
        cid = str(bad_course["_id"])
        await db.course_transcripts.delete_many({"course_id": cid})
        await db.courses.delete_many({"_id": bad_course["_id"]})
        print(f"Deleted bad course {cid}")
        
asyncio.run(clear())
