import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    db = AsyncIOMotorClient('mongodb://localhost:27017').cognitrace_db
    doc = await db.course_transcripts.find_one()
    if doc:
        print(f"Transcript course_id: {doc.get('course_id')} type: {type(doc.get('course_id'))}")
    else:
        print("No transcript docs")
        
    cdoc = await db.concept_segments.find_one()
    if cdoc:
        print(f"Concept course_id: {cdoc.get('course_id')} type: {type(cdoc.get('course_id'))}")
    else:
        print("No concept docs")

asyncio.run(main())
