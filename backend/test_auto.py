import requests

def test():
    # Login Teacher
    res = requests.post("http://localhost:8000/api/v1/auth/login", json={"identifier": "T24A001", "password": "password"})
    t_token = res.json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}
    
    # Create course
    course_data = {
        "course_name": "Test Course Auto",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    }
    res = requests.post("http://localhost:8000/api/v1/courses", json=course_data, headers=t_headers)
    print("Create:", res.status_code, res.text)
    
test()
