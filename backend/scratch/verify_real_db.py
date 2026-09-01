import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import asyncio
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db
from app.services.question_service import QuestionService

async def test_real():
    await connect_to_mongo()
    course_id = "6a8d5f5e0dcc32a196810357"
    concept_ref, concept_name, tx_text = await QuestionService.extract_transcript_for_concept(course_id, "Goal Of Os Fundamentals")
    print("=" * 60)
    print("REAL DATA TRANSCRIPT EXTRACTION SUCCESSFUL:")
    print(f"  - Concept Ref Derived: {concept_ref}")
    print(f"  - Concept Name Matched: {concept_name}")
    print(f"  - Extracted Text Length: {len(tx_text)} chars")
    print(f"  - Sample Extracted Text: '{tx_text[:200]}...'")
    print("=" * 60)
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_real())
