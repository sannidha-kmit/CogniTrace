import sys
import os
import joblib
import numpy as np
from pymongo import MongoClient
from app.core.config import settings

client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB_NAME]

print("=== DB DATASET SUMMARY ===")
print("Interaction events count:", db.interaction_events.count_documents({}))
print("Concept mappings count:", db.concept_event_mappings.count_documents({}))
print("Difficulty records count:", db.difficulty.count_documents({}))
print("Quiz sessions count:", db.quiz_sessions.count_documents({}))
print("Questions count:", db.questions.count_documents({}))
print("Course transcripts count:", db.course_transcripts.count_documents({}))
print("Courses count:", db.courses.count_documents({}))

# Check difficulty records
diff_docs = list(db.difficulty.find({}))
print(f"\nDifficulty records ({len(diff_docs)}):")
for d in diff_docs[:5]:
    print(d)

# Load model
model_dict = joblib.load("models/adaptive_quiz_model.pkl")
model = model_dict["model"]
features = model_dict["feature_names"]
classes = model_dict["classes"]
print("\nLoaded Model:", type(model))
print("Classes:", classes)
print("Features:", features)

# Test model predictions on actual difficulty records
if diff_docs:
    X_actual = []
    y_ground_truth = []
    for d in diff_docs:
        # map features: ['backward_count', 'replay_count', 'study_pause_count', 'other_work_pause_count', 'forward_count', 'speed_increase_count']
        b_count = float(d.get("SeekBackwardCount", 0))
        r_count = float(d.get("ReplayCount", 0))
        study_pause = float(d.get("UnderstandPauseCount", 0))
        total_pause = float(d.get("PauseCount", 0))
        other_pause = max(0.0, total_pause - study_pause)
        f_count = float(d.get("SeekForwardCount", 0))
        speed_count = 0.0 # From raw telemetry if speed changed
        
        feat_vector = [b_count, r_count, study_pause, other_pause, f_count, speed_count]
        X_actual.append(feat_vector)
        
        # Ground truth difficulty level from actual Phase 8 dataset
        level = d.get("DifficultyLevel", "Easy").upper()
        if level == "EASY":
            level = "LOW"
        y_ground_truth.append(level)

    X_actual = np.array(X_actual)
    preds = model.predict(X_actual)
    probas = model.predict_proba(X_actual)
    print("\nActual Predictions:")
    for i, (gt, pred, proba) in enumerate(zip(y_ground_truth, preds, probas)):
        print(f"Sample {i+1}: Features={X_actual[i]} -> GroundTruth={gt}, Predicted={pred}, Proba={proba}")
