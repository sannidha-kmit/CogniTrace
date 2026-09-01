import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    db = AsyncIOMotorClient('mongodb://localhost:27017').cognitrace_db
    doc = await db.concept_segments.find_one()
    if doc:
        segs = doc.get('segments')
        if segs:
            print(f"Concept Segments: {len(segs)} segments found")
        else:
            print("Concept segments field missing or empty")
        print(f"Course ID: {doc.get('course_id')}")
    else:
        print("No concept_segments found")
    
    tdoc = await db.course_transcripts.find_one()
    if tdoc:
        segs = tdoc.get('segments')
        if segs:
            print(f"Transcript Segments: {len(segs)} segments found")
        else:
            print("Transcript segments field missing or empty")
        print(f"Transcript Status: {tdoc.get('status')}")
    else:
        print("No course_transcripts found")

asyncio.run(main())
