import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import json
import asyncio
from app.core.security import create_access_token
from app.db.mongodb import get_database

async def main():
    db = await get_database()
    student = await db.users.find_one({"identifier": "S24A003"})
    if not student:
        print("Student not found")
        return
        
    course_id = "6a7f29a87959ed0a44852fc7"
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        from bson import ObjectId
        course = await db.courses.find_one({"_id": ObjectId(course_id)})
        
    # Create token for S24A003 with year matching course ("3rd Year")
    payload = {
        "sub": "S24A003",
        "identifier": "S24A003",
        "role": "student",
        "year": course.get("year", "3rd Year")
    }
    token = create_access_token(payload)
    print("Generated token for S24A003 with year:", payload["year"])
    
    # Call Adaptive Quiz endpoint
    quiz_req = urllib.request.Request(
        f"http://127.0.0.1:8000/api/v1/student/courses/{course_id}/adaptive-quiz",
        headers={"Authorization": f"Bearer {token}"}
    )
    quiz_resp = urllib.request.urlopen(quiz_req)
    quiz_data = json.loads(quiz_resp.read())
    print("\nAdaptive Quiz loaded successfully!")
    print("Session ID:", quiz_data.get("quiz_session_id"))
    print("Total Questions:", len(quiz_data.get("questions", [])))
    print("Concept Map:")
    for n in quiz_data.get("concept_map", {}).get("nodes", []):
        print(f"  - Concept: '{n['concept_name']}' | Priority: {n['priority']} | Question Count: {n['question_count']}")
        
    print("\nFirst 3 Questions:")
    for i, q in enumerate(quiz_data.get("questions", [])[:3], 1):
        print(f"  Q{i}: {q['question']} [{q.get('concept', 'General')}]")
        for opt in q["options"]:
            print(f"      * {opt}")
            
    # Submit the quiz
    quiz_id = quiz_data.get("quiz_session_id")
    submit_data = {
        "quiz_session_id": quiz_id,
        "answers": [
            {"question_id": q["question_id"], "selected_answer": q["options"][0]}
            for q in quiz_data.get("questions", [])
        ]
    }
    submit_req = urllib.request.Request(
        f"http://127.0.0.1:8000/api/v1/student/courses/{course_id}/adaptive-quiz/submit",
        data=json.dumps(submit_data).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    submit_resp = urllib.request.urlopen(submit_req)
    submit_res_data = json.loads(submit_resp.read())
    print("\nQuiz submission completed!")
    print(f"  Score: {submit_res_data.get('correct_count')}/{submit_res_data.get('total_questions')}")
    print(f"  Percentage: {submit_res_data.get('score_percentage')}%")
    print(f"  Concept Performance Breakdown:")
    for cp in submit_res_data.get("concept_performance", []):
        print(f"    - {cp['concept']}: {cp['correct']}/{cp['total_questions']} ({cp['accuracy_percentage']}%)")

if __name__ == "__main__":
    asyncio.run(main())
