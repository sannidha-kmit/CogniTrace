import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_concepts():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.cognitrace_db
    doc = await db.concept_segments.find_one({"course_id": "6a95b26395cea96d640e1f2a"})
    for c in doc["segments"]:
        print(f"- {c['Concept']} ({c['ConceptStart']} - {c['ConceptEnd']})")
        
asyncio.run(check_concepts())
