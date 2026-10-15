import sys
from pymongo import MongoClient
from app.core.config import settings

client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB_NAME]

print("=== QUIZ SESSIONS ===")
sessions = list(db.quiz_sessions.find({}))
print(f"Total quiz sessions in DB: {len(sessions)}")

answered_sessions = [s for s in sessions if s.get("answered_questions", 0) > 0 or s.get("status") == "COMPLETED"]
print(f"Sessions with answered questions: {len(answered_sessions)}")

total_attempted_q = 0
total_correct_q = 0
concept_stats = {}

for s in sessions:
    for q in s.get("questions", []):
        if q.get("answered") is True or q.get("is_correct") is not None:
            total_attempted_q += 1
            is_c = q.get("is_correct", False)
            if is_c:
                total_correct_q += 1
            
            c_name = q.get("concept_name") or q.get("concept_id") or "General"
            if c_name not in concept_stats:
                concept_stats[c_name] = {"total": 0, "correct": 0}
            concept_stats[c_name]["total"] += 1
            if is_c:
                concept_stats[c_name]["correct"] += 1

print(f"Total Questions Attempted: {total_attempted_q}")
print(f"Total Correct Answers: {total_correct_q}")
if total_attempted_q > 0:
    print(f"Actual Quiz Accuracy: {(total_correct_q / total_attempted_q)*100:.2f}%")
else:
    print("Actual Quiz Accuracy: No answered questions recorded yet.")

print("\n=== CONCEPT-WISE PERFORMANCE ===")
if concept_stats:
    for c, stats in concept_stats.items():
        pct = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"Concept '{c}': Attempted={stats['total']}, Correct={stats['correct']}, Mastery={pct:.1f}%")
else:
    print("No concept-wise attempts recorded in quiz sessions yet.")

print("\n=== QUESTION GENERATION QUALITY EVALUATION ===")
questions = list(db.questions.find({}))
transcripts = list(db.course_transcripts.find({"status": "COMPLETED"}))

print(f"Total Questions in Question Bank: {len(questions)}")
print(f"Total Transcripts in Database: {len(transcripts)}")

transcript_corpus = {}
for t in transcripts:
    cid = str(t.get("course_id"))
    all_text = " ".join([seg.get("text", "") for seg in t.get("segments", [])]).lower()
    transcript_corpus[cid] = all_text

valid_format_count = 0
unique_hashes = set()
grounded_count = 0
relevant_count = 0

for q in questions:
    cid = str(q.get("course_id", ""))
    q_text = q.get("question") or q.get("question_text", "")
    options = q.get("options", [])
    correct_ans = q.get("correct_answer", "")
    q_hash = q.get("question_hash") or q_text.strip().lower()
    concept = q.get("concept_name") or q.get("concept_ref") or ""

    # Correctness
    if len(options) == 4 and correct_ans and (correct_ans in options or correct_ans in ["A", "B", "C", "D"]):
        valid_format_count += 1

    # Uniqueness
    unique_hashes.add(q_hash)

    # Relevance
    if concept and len(q_text) > 10:
        relevant_count += 1

    # Transcript Grounding
    course_text = transcript_corpus.get(cid, "")
    if course_text:
        words = [w for w in q_text.lower().split() if len(w) > 4]
        matches = sum(1 for w in words if w in course_text)
        if matches >= min(2, len(words)) or len(words) == 0:
            grounded_count += 1

total_q = len(questions)
if total_q > 0:
    print(f"Correctness (4 options + valid answer key): {valid_format_count}/{total_q} ({(valid_format_count/total_q)*100:.2f}%)")
    print(f"Uniqueness (distinct question hashes): {len(unique_hashes)}/{total_q} ({(len(unique_hashes)/total_q)*100:.2f}%)")
    print(f"Relevance (mapped concept & text validity): {relevant_count}/{total_q} ({(relevant_count/total_q)*100:.2f}%)")
    print(f"Transcript Grounding (keywords matched in ASR transcript): {grounded_count}/{total_q} ({(grounded_count/total_q)*100:.2f}%)")
