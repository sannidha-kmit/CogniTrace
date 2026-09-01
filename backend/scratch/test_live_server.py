import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import requests

BASE_URL = "http://localhost:8000/api/v1"

def test_live_server():
    print("=" * 60)
    print("VERIFYING LIVE RUNNING FASTAPI SERVER ENDPOINTS AT http://localhost:8000")
    print("=" * 60)

    # 1. Fetch OpenAPI spec
    r_docs = requests.get(f"{BASE_URL}/openapi.json")
    assert r_docs.status_code == 200
    spec = r_docs.json()
    paths = spec.get("paths", {})
    
    question_paths = [p for p in paths if "question" in p]
    print(f"\n1. REGISTERED QUESTION ENDPOINTS IN SWAGGER / OPENAPI ({len(question_paths)}):")
    for path in question_paths:
        methods = list(paths[path].keys())
        print(f"  [REGISTERED] {methods[0].upper()} {BASE_URL}{path}")
    
    assert len(question_paths) == 4, f"Expected 4 question paths, found {len(question_paths)}"

    # 2. Register Teacher
    t_id = "T24LIVE1"
    reg_t = requests.post(f"{BASE_URL}/auth/register/teacher", json={
        "teacher_id": t_id,
        "name": "Prof. Live",
        "year": "2nd Year",
        "subject": "OS",
        "password": "Password123",
        "confirm_password": "Password123"
    })
    if reg_t.status_code != 201:
        # Login if already exists
        login_t = requests.post(f"{BASE_URL}/auth/login", json={"identifier": t_id, "password": "Password123"})
        t_token = login_t.json()["access_token"]
    else:
        t_token = reg_t.json()["access_token"]
    print("\n2. Teacher Authentication Token acquired.")

    # 3. Register Student
    s_id = "S24LIVE1"
    reg_s = requests.post(f"{BASE_URL}/auth/register/student", json={
        "roll_number": s_id,
        "name": "Student Live",
        "year": "2nd Year",
        "password": "Password123",
        "confirm_password": "Password123"
    })
    if reg_s.status_code != 201:
        login_s = requests.post(f"{BASE_URL}/auth/login", json={"identifier": s_id, "password": "Password123"})
        s_token = login_s.json()["access_token"]
    else:
        s_token = reg_s.json()["access_token"]
    print("3. Student Authentication Token acquired.")

    # 4. Use existing real course ID from database (or create a test course for live request)
    course_id = "6a8d5f5e0dcc32a196810357"  # Real Course ID in cognitrace_db

    # 5. Live GET Student Questions on running server
    get_sq = requests.get(
        f"{BASE_URL}/student/courses/{course_id}/questions",
        headers={"Authorization": f"Bearer {s_token}"}
    )
    print(f"\n4. LIVE GET Student Questions Endpoint Response Status: {get_sq.status_code}")
    assert get_sq.status_code == 200
    sq_data = get_sq.json()
    print(f"   Total questions returned: {sq_data['total']}")
    if sq_data["questions"]:
        sample_q = sq_data["questions"][0]
        assert "correct_answer" not in sample_q
        assert "explanation" not in sample_q
        print("   [SECURITY VERIFIED] correct_answer and explanation hidden from student API response.")

    print("\n" + "=" * 60)
    print("ALL LIVE SERVER FASTAPI ROUTE VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_live_server()
