import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def inspect():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.cognitrace_db
    
    courses = await db.courses.find().to_list(10)
    print(f"Total courses: {len(courses)}")
    
    for c in courses:
        cid = str(c["_id"])
        name = c["course_name"]
        
        tx = await db.course_transcripts.find_one({"course_id": cid})
        tx_status = tx.get("status", "MISSING") if tx else "MISSING"
        
        ce_job = await db.concept_extraction_jobs.find_one({"course_id": cid})
        ce_job_status = ce_job.get("status", "MISSING") if ce_job else "MISSING"
        
        conc = await db.concept_segments.find_one({"course_id": cid})
        conc_status = conc.get("status", "MISSING") if conc else "MISSING"
        conc_count = len(conc.get("segments", [])) if conc else 0
        
        mapping = await db.concept_event_mappings.find_one({"CourseID": cid})
        map_status = "EXISTS" if mapping else "MISSING"
        
        print(f"\nCourse: {name} ({cid})")
        print(f"  Transcript Status: {tx_status}")
        print(f"  Concept Job Status: {ce_job_status}")
        print(f"  Concept Segments Status: {conc_status} (Count: {conc_count})")
        print(f"  Concept Event Mapping: {map_status}")

asyncio.run(inspect())
