import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_e2e():
    print("Starting End-to-End API Test for Phase 11...")
    
    # 1. Login Teacher
    print("1. Login Teacher T24A001")
    res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": "T24A001", "password": "password"})
    assert res.status_code == 200, res.text
    t_token = res.json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}
    
    # 2. Login Student
    print("2. Login Student S24A001")
    res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": "S24A001", "password": "password"})
    assert res.status_code == 200, res.text
    s_token = res.json()["access_token"]
    s_headers = {"Authorization": f"Bearer {s_token}"}
    
    # 3. Teacher creates a course
    print("3. Teacher creates course")
    course_data = {
        "course_name": "Test Course 101",
        "youtube_url": "https://www.youtube.com/watch?v=M7FIvfx5J10",
        "year": "2nd Year"
    }
    res = requests.post(f"{BASE_URL}/courses", json=course_data, headers=t_headers)
    print("Create Course Response:", res.status_code, res.text)
    if res.status_code == 400 and "already exists" in res.text:
        res = requests.get(f"{BASE_URL}/courses/my", headers=t_headers)
        course_id = res.json()[0]["id"]
    else:
        assert res.status_code == 201, res.text
        course_id = res.json().get("id")
    print(f"   Course ID: {course_id}")
    
    # 4. Generate Transcript
    print("4. Teacher requests transcript")
    res = requests.post(f"{BASE_URL}/teacher/courses/{course_id}/transcript/generate", headers=t_headers)
    print("Generate Transcript Response:", res.status_code, res.text)
    assert res.status_code in (202, 200, 400), res.text
    
    # Wait for transcript to finish
    print("5. Waiting for transcript completion...")
    for _ in range(30):
        res = requests.get(f"{BASE_URL}/teacher/courses/{course_id}/transcript/status", headers=t_headers)
        status = res.json()["status"]
        print(f"   Status: {status}")
        if status == "COMPLETED":
            break
        time.sleep(2)
        
    # 6. Student interacts
    print("6. Student sends interaction")
    event_data = {
        "course_id": course_id,
        "event_type": "PLAY",
        "event_timestamp": "12.5",
        "event_duration": "0",
        "playback_speed": "1.0",
        "pause_reason": "None"
    }
    res = requests.post(f"{BASE_URL}/student/events", json=event_data, headers=s_headers)
    print("Student Interaction Response:", res.status_code, res.text)
    assert res.status_code == 201, res.text
    
    # 7. Teacher views Dataset
    print("7. Teacher views Dataset Summary")
    res = requests.get(f"{BASE_URL}/teacher/datasets/summary", headers=t_headers)
    print("Dataset Summary Response:", res.status_code, res.text)
    assert res.status_code == 200, res.text
    
    print("\nAll End-to-End API Tests Passed!")

if __name__ == "__main__":
    test_e2e()
