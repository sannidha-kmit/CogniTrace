import requests
import json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJUMjRBMDAxIiwicm9sZSI6InRlYWNoZXIiLCJleHAiOjE3ODgxOTE0NjJ9.Y4hAIwHEqAjwQi7k9Ogg9WK04bWzc7CEIi6f-BSwRtk"
headers = {"Authorization": f"Bearer {token}"}

res = requests.post("http://localhost:8000/api/v1/courses", 
    headers=headers,
    json={"course_name": "API Test Course", "youtube_url": "https://www.youtube.com/watch?v=M7FIvfx5J10"}
)
print(res.status_code)
print(res.text)

