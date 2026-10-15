import asyncio
import os
import sys
sys.path.append(os.getcwd())
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.services.question_service import QuestionService
from bson import ObjectId

async def test_quiz():
    await connect_to_mongo()
    db = await get_database()
    
    # OS
    os_c = await db.courses.find_one({"_id": ObjectId("6a8d5f5e0dcc32a196810357")})
    print(f"\nTesting OS Course: {os_c['course_name']}")
    try:
        # What concepts does it have?
        conc = await db.concept_segments.find_one({"course_id": str(os_c['_id'])})
        first_concept = conc['segments'][0]['Concept']
        print(f"Using concept: {first_concept}")
        res = await QuestionService.generate_and_store_questions(str(os_c['_id']), first_concept, count=1)
        print("Success! Question:", res[0].question)
    except Exception as e:
        print("Failed:", str(e))

    # DAA
    daa_c = await db.courses.find_one({"_id": ObjectId("6a955a3cd0c51643561d77f2")})
    print(f"\nTesting DAA Course: {daa_c['course_name']}")
    try:
        conc = await db.concept_segments.find_one({"course_id": str(daa_c['_id'])})
        first_concept = conc['segments'][0]['Concept']
        print(f"Using concept: {first_concept}")
        res = await QuestionService.generate_and_store_questions(str(daa_c['_id']), first_concept, count=1)
        print("Success! Question:", res[0].question)
    except Exception as e:
        print("Failed:", str(e))

    await close_mongo_connection()

asyncio.run(test_quiz())
