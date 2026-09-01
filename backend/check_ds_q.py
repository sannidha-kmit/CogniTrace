import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_ds_questions():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.cognitrace_db
    
    course_id = "6a95aefcda7042bd6c0a29f9"
    q = await db.questions.count_documents({"course_id": course_id})
    print("DS Generated Questions:", q)
    
asyncio.run(check_ds_questions())
