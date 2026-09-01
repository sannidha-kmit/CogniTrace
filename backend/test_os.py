import asyncio
import os
import sys
sys.path.append(os.getcwd())
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.services.question_service import QuestionService

async def test_quiz():
    await connect_to_mongo()
    db = await get_database()
    
    os_course = await db.courses.find_one({"course_name": "Operating System Scheduling & Memory"})
    if os_course:
        print(f"Found OS course: {os_course['_id']}")
        try:
            res = await QuestionService.generate_and_store_questions(str(os_course['_id']), "FCFS Scheduling", count=1)
            print("Successfully generated OS question:")
            print(res[0].question)
        except Exception as e:
            print("OS generation failed:", str(e))
    else:
        print("OS course not found in db.")
        
    await close_mongo_connection()

asyncio.run(test_quiz())
