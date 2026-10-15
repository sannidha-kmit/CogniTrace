import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
"""
Phase 11 — Comprehensive Backend API Test Suite
Tests all phases: Auth, Courses, Transcripts, Interactions, Concepts, Mappings, Difficulty, Dataset, Export
"""
import requests
import time

BASE = "http://localhost:8000/api/v1"

PASS = []
FAIL = []

def ok(label):
    PASS.append(label)
    print(f"  [PASS] {label}")

def fail(label, detail=""):
    FAIL.append(label)
    print(f"  [FAIL] {label} — {detail}")

def run():
    print("=" * 60)
    print("COGNITRACE PHASE 11 — COMPREHENSIVE API TEST SUITE")
    print("=" * 60)

    # ── HEALTH ─────────────────────────────────────────────────
    print("\n[1] Health Check")
    r = requests.get(f"{BASE}/health")
    if r.status_code == 200 and r.json()["database"]["status"] == "connected":
        ok("Health — MongoDB connected")
    else:
        fail("Health", r.text)

    # ── AUTH ───────────────────────────────────────────────────
    print("\n[2] Authentication")
    # Teacher Login
    r = requests.post(f"{BASE}/auth/login", json={"identifier": "T24A001", "password": "password"})
    if r.status_code == 200:
        ok("Teacher Login")
        t_token = r.json()["access_token"]
        t_h = {"Authorization": f"Bearer {t_token}"}
    else:
        fail("Teacher Login", r.text); return

    # Student Login
    r = requests.post(f"{BASE}/auth/login", json={"identifier": "S24A001", "password": "password"})
    if r.status_code == 200:
        ok("Student Login")
        s_token = r.json()["access_token"]
        s_h = {"Authorization": f"Bearer {s_token}"}
    else:
        fail("Student Login", r.text); return

    # /me endpoints
    r = requests.get(f"{BASE}/auth/me", headers=t_h)
    if r.status_code == 200 and r.json()["role"] == "teacher":
        ok("Teacher /me")
    else:
        fail("Teacher /me", r.text)

    r = requests.get(f"{BASE}/auth/me", headers=s_h)
    if r.status_code == 200 and r.json()["role"] == "student":
        ok("Student /me")
    else:
        fail("Student /me", r.text)

    # Duplicate registration blocked
    r = requests.post(f"{BASE}/auth/register/teacher", json={
        "teacher_id": "T24A001", "name": "Nidhi", "year": "2nd Year",
        "subject": "DAA", "password": "password", "confirm_password": "password"
    })
    if r.status_code == 400:
        ok("Duplicate teacher registration blocked")
    else:
        fail("Duplicate teacher registration blocked", r.text)

    # Wrong password rejected
    r = requests.post(f"{BASE}/auth/login", json={"identifier": "T24A001", "password": "wrongpass"})
    if r.status_code in (401, 400):
        ok("Wrong password rejected")
    else:
        fail("Wrong password rejected", r.text)

    # ── COURSES ────────────────────────────────────────────────
    print("\n[3] Course Management")
    r = requests.get(f"{BASE}/courses/my", headers=t_h)
    if r.status_code == 200:
        courses = r.json()
        ok(f"Get teacher courses ({len(courses)} courses)")
        if courses:
            course_id = courses[0]["id"]
            course_name = courses[0]["course_name"]
        else:
            fail("No courses found — create one first"); return
    else:
        fail("Get teacher courses", r.text); return

    # Get single course
    r = requests.get(f"{BASE}/courses/{course_id}", headers=t_h)
    if r.status_code == 200:
        ok("Get course by ID")
    else:
        fail("Get course by ID", r.text)

    # Student cannot create courses
    r = requests.post(f"{BASE}/courses", json={
        "course_name": "Hack", "youtube_url": "https://www.youtube.com/watch?v=test", "year": "2nd Year"
    }, headers=s_h)
    if r.status_code == 403:
        ok("Student blocked from creating courses")
    else:
        fail("Student blocked from creating courses", f"Got {r.status_code}")

    # ── TRANSCRIPTS ────────────────────────────────────────────
    print("\n[4] Transcript System")
    r = requests.get(f"{BASE}/teacher/courses/{course_id}/transcript/status", headers=t_h)
    if r.status_code == 200:
        status = r.json()["status"]
        ok(f"Transcript status endpoint ({status})")
    else:
        fail("Transcript status endpoint", r.text)

    r = requests.get(f"{BASE}/teacher/courses/{course_id}/transcript", headers=t_h)
    if r.status_code == 200:
        tx = r.json()
        seg_count = len(tx.get("segments", []))
        ok(f"Get transcript ({seg_count} segments, status={tx['status']})")
    else:
        fail("Get transcript", r.text)

    # ── INTERACTIONS ───────────────────────────────────────────
    print("\n[5] Interaction Telemetry")
    for event_type in ["PLAY", "PAUSE", "SEEK_FORWARD", "SEEK_BACKWARD", "SPEED_CHANGE"]:
        r = requests.post(f"{BASE}/student/events", json={
            "course_id": course_id,
            "event_type": event_type,
            "event_timestamp": "30.0",
            "event_duration": "5",
            "playback_speed": "1.5" if event_type == "SPEED_CHANGE" else "1.0",
            "pause_reason": "UNDERSTANDING" if event_type == "PAUSE" else "None"
        }, headers=s_h)
        if r.status_code == 201:
            ok(f"Record {event_type} event")
        else:
            fail(f"Record {event_type} event", r.text)

    # ── STUDENT COURSE BROWSING ────────────────────────────────
    print("\n[6] Student Course Access")
    r = requests.get(f"{BASE}/student/courses", headers=s_h)
    if r.status_code == 200:
        ok(f"Student course list ({len(r.json())} courses)")
    else:
        fail("Student course list", r.text)

    r = requests.get(f"{BASE}/student/courses/{course_id}", headers=s_h)
    if r.status_code == 200:
        ok("Student get course by ID")
    else:
        fail("Student get course by ID", r.text)

    # ── DATASET SUMMARY ────────────────────────────────────────
    print("\n[7] Dataset Viewer")
    r = requests.get(f"{BASE}/teacher/datasets/summary", headers=t_h)
    if r.status_code == 200:
        summary = r.json()
        ok(f"Dataset summary — interactions:{summary['interactions']} transcripts:{summary['transcripts']} concepts:{summary['concepts']}")
    else:
        fail("Dataset summary", r.text)

    for ds_type in ["interactions", "transcripts", "concepts", "mappings", "difficulty"]:
        r = requests.get(f"{BASE}/teacher/datasets/{ds_type}", headers=t_h)
        if r.status_code == 200:
            total = r.json().get("total", 0)
            ok(f"Dataset viewer — {ds_type} ({total} records)")
        else:
            fail(f"Dataset viewer — {ds_type}", r.text)

    # ── EXPORTS ────────────────────────────────────────────────
    print("\n[8] Dataset Exports")
    for fmt in ["csv", "json", "xlsx"]:
        r = requests.get(f"{BASE}/teacher/datasets/interactions/export?format={fmt}", headers=t_h)
        if r.status_code == 200:
            ok(f"Export interactions as {fmt.upper()}")
        else:
            fail(f"Export interactions as {fmt.upper()}", r.text)

    # ── CONCEPT EXTRACTION ─────────────────────────────────────
    print("\n[9] Concept Extraction (Phase 6)")
    r = requests.post(f"{BASE}/teacher/courses/{course_id}/concepts/extract", headers=t_h)
    if r.status_code in (202, 200, 400):
        ok(f"Concept extraction queued ({r.status_code})")
    else:
        fail("Concept extraction queued", r.text)

    r = requests.get(f"{BASE}/teacher/courses/{course_id}/concepts/status", headers=t_h)
    if r.status_code == 200:
        ok(f"Concept extraction status ({r.json().get('status')})")
    else:
        fail("Concept extraction status", r.text)

    # ── SUMMARY ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"RESULTS: {len(PASS)} PASSED  |  {len(FAIL)} FAILED")
    print("=" * 60)
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print(f"  - {f}")
    else:
        print("ALL TESTS PASSED!")

if __name__ == "__main__":
    run()
