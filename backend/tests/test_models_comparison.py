import math
import joblib
import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
from app.core.config import settings

client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB_NAME]

# 1. Load trained LogisticRegression model
model_dict = joblib.load("models/adaptive_quiz_model.pkl")
lr_model = model_dict["model"]

# 2. Extract Phase 8 difficulty dataset
diff_docs = list(db.difficulty.find({}))
X_lr = []
y_true = []
preds_heuristic = []

for d in diff_docs:
    b_count = float(d.get("SeekBackwardCount", 0))
    r_count = float(d.get("ReplayCount", 0))
    study_pause = float(d.get("UnderstandPauseCount", 0))
    total_pause = float(d.get("PauseCount", 0))
    other_pause = max(0.0, total_pause - study_pause)
    f_count = float(d.get("SeekForwardCount", 0))
    diff_score = float(d.get("DifficultyScore", 0.0))
    
    X_lr.append([b_count, r_count, study_pause, other_pause, f_count, 0.0])
    
    level = str(d.get("DifficultyLevel", "Easy")).upper()
    if level == "EASY":
        level = "LOW"
    y_true.append(level)

    # Member 1 Heuristic engine prediction:
    weighted_struggle = (
        (r_count * 2.0) +
        (b_count * 2.0) +
        (study_pause * 3.0) +
        (diff_score * 1.5) +
        (total_pause * 0.5)
    )
    score = 1.0 / (1.0 + math.exp(-0.4 * (weighted_struggle - 5.0)))
    if score >= 0.7:
        p_h = "HIGH"
    elif score >= 0.4:
        p_h = "MEDIUM"
    else:
        p_h = "LOW"
    preds_heuristic.append(p_h)

X_lr = np.array(X_lr)
y_true = np.array(y_true)
y_pred_lr = lr_model.predict(X_lr)
y_pred_heur = np.array(preds_heuristic)

print("=== 1. LOGISTIC REGRESSION (models/adaptive_quiz_model.pkl) ===")
acc_lr = accuracy_score(y_true, y_pred_lr)
print(f"Accuracy: {acc_lr*100:.2f}%")
print("Confusion Matrix [HIGH, MEDIUM, LOW]:\n", confusion_matrix(y_true, y_pred_lr, labels=["HIGH", "MEDIUM", "LOW"]))
print(classification_report(y_true, y_pred_lr, labels=["HIGH", "MEDIUM", "LOW"], zero_division=0))

print("\n=== 2. ADAPTIVE INFERENCE ENGINE (AdaptiveModelService) ===")
acc_heur = accuracy_score(y_true, y_pred_heur)
print(f"Accuracy: {acc_heur*100:.2f}%")
print("Confusion Matrix [HIGH, MEDIUM, LOW]:\n", confusion_matrix(y_true, y_pred_heur, labels=["HIGH", "MEDIUM", "LOW"]))
print(classification_report(y_true, y_pred_heur, labels=["HIGH", "MEDIUM", "LOW"], zero_division=0))
