import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def fix_stuck_courses():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.cognitrace_db
    
    now = datetime.now(timezone.utc)
    courses = await db.courses.find().to_list(100)
    for c in courses:
        cid = str(c["_id"])
        tx = await db.course_transcripts.find_one({"course_id": cid})
        if tx and tx.get("status") == "COMPLETED":
            cp = await db.concept_segments.find_one({"course_id": cid})
            if not cp or cp.get("status") != "COMPLETED":
                print(f"Queueing concepts for {cid} ({c['course_name']})")
                
                # Delete existing if any to avoid update issues
                await db.concept_extraction_jobs.delete_many({"course_id": cid})
                await db.concept_segments.delete_many({"course_id": cid})
                
                await db.concept_extraction_jobs.insert_one(
                    {
                        "course_id": cid,
                        "teacher_id": c["teacher_id"],
                        "status": "PENDING",
                        "attempts": 0,
                        "error_message": None,
                        "created_at": now,
                        "updated_at": now
                    }
                )
                
                await db.concept_segments.insert_one(
                    {
                        "course_id": cid,
                        "CourseSubject": c["subject"],
                        "CourseName": c["course_name"],
                        "teacher_id": c["teacher_id"],
                        "teacher_name": c["teacher_name"],
                        "status": "PENDING",
                        "segments": [],
                        "error_message": None,
                        "created_at": now,
                        "updated_at": now
                    }
                )
                
asyncio.run(fix_stuck_courses())
