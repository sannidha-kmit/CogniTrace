import joblib
import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
from app.core.config import settings

client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB_NAME]

# 1. Load model
model_dict = joblib.load("models/adaptive_quiz_model.pkl")
model = model_dict["model"]
classes = model_dict["classes"]
features = model_dict["feature_names"]

# 2. Extract dataset
diff_docs = list(db.difficulty.find({}))
X = []
y_true = []

for d in diff_docs:
    b_count = float(d.get("SeekBackwardCount", 0))
    r_count = float(d.get("ReplayCount", 0))
    study_pause = float(d.get("UnderstandPauseCount", 0))
    total_pause = float(d.get("PauseCount", 0))
    other_pause = max(0.0, total_pause - study_pause)
    f_count = float(d.get("SeekForwardCount", 0))
    speed_count = 0.0
    
    X.append([b_count, r_count, study_pause, other_pause, f_count, speed_count])
    
    level = str(d.get("DifficultyLevel", "Easy")).upper()
    if level == "EASY":
        level = "LOW"
    y_true.append(level)

X = np.array(X)
y_true = np.array(y_true)
y_pred = model.predict(X)

print("Unique true classes:", np.unique(y_true, return_counts=True))
print("Unique pred classes:", np.unique(y_pred, return_counts=True))

acc = accuracy_score(y_true, y_pred)
macro_p = precision_score(y_true, y_pred, average="macro", zero_division=0)
weighted_p = precision_score(y_true, y_pred, average="weighted", zero_division=0)
macro_r = recall_score(y_true, y_pred, average="macro", zero_division=0)
weighted_r = recall_score(y_true, y_pred, average="weighted", zero_division=0)
macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

cm = confusion_matrix(y_true, y_pred, labels=["HIGH", "MEDIUM", "LOW"])

print(f"\n--- EVALUATION METRICS (Total Samples = {len(y_true)}) ---")
print(f"Prediction Accuracy : {acc * 100:.2f}%")
print(f"Macro Precision     : {macro_p * 100:.2f}%")
print(f"Weighted Precision  : {weighted_p * 100:.2f}%")
print(f"Macro Recall        : {macro_r * 100:.2f}%")
print(f"Weighted Recall     : {weighted_r * 100:.2f}%")
print(f"Macro F1-Score      : {macro_f1 * 100:.2f}%")
print(f"Weighted F1-Score   : {weighted_f1 * 100:.2f}%")
print("\nConfusion Matrix [HIGH, MEDIUM, LOW]:")
print("Labels order: ['HIGH', 'MEDIUM', 'LOW']")
print(cm)
print("\nClassification Report:\n", classification_report(y_true, y_pred, labels=["HIGH", "MEDIUM", "LOW"], zero_division=0))
