import requests
import time

base_url = 'http://localhost:8000/api/v1'

reg_data = {'username': 'teacher_daa2', 'password': 'password123', 'role': 'teacher', 'name': 'Prof. DAA', 'year': '3', 'subject': 'DAA'}
requests.post(f'{base_url}/auth/register', json=reg_data)

login_data = {'username': 'teacher_daa2', 'password': 'password123'}
res = requests.post(f'{base_url}/auth/token', data=login_data)
if res.status_code != 200:
    print('Login failed:', res.text)
    exit(1)

token = res.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

course_data = {'course_name': 'DAA Introduction 4', 'youtube_url': 'https://www.youtube.com/watch?v=kqtD5dpn9C8'}
res = requests.post(f'{base_url}/teacher/courses', json=course_data, headers=headers)

if res.status_code == 400:
    print('Course exists, finding it...')
    res = requests.get(f'{base_url}/teacher/courses/my', headers=headers)
    course_id = next(c['id'] for c in res.json() if c['course_name'] == 'DAA Introduction 4')
else:
    course_id = res.json()['id']

print(f'1. Course created/found. Course ID: {course_id}')
print(f'2. Automatic transcript job should be created. Polling status...')

for _ in range(60):
    time.sleep(2)
    res = requests.get(f'{base_url}/teacher/courses/{course_id}/transcript/status', headers=headers)
    status = res.json()
    print('Status:', status['status'], status['stage'], f"{status['progress']}%", status.get('message', ''))
    if status['status'] == 'COMPLETED':
        print('Transcript finished!')
        break
    elif status['status'] == 'FAILED':
        print('Transcript failed.')
        break

# check transcript generation
res = requests.get(f'{base_url}/teacher/courses/{course_id}/transcript', headers=headers)
if res.status_code == 200 and len(res.json().get('segments', [])) > 0:
    print(f"5. Transcript content is stored successfully, got {len(res.json()['segments'])} segments.")

# generate questions
print('6. Generating Questions...')
res = requests.post(f'{base_url}/teacher/courses/{course_id}/questions/generate', headers=headers, json={"num_questions": 3, "difficulty_distribution": {"easy": 1, "medium": 1, "hard": 1}})
if res.status_code == 200:
    print('Questions generate API succeeded!')
    # you can print the questions if you want
    print('Success:', res.json().get('message', ''))
else:
    print('Questions generate failed:', res.text)

