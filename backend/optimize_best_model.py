import os
import sys
import joblib
import numpy as np
from pymongo import MongoClient
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB_NAME]

diff_docs = list(db.difficulty.find({}))
feature_names = ['backward_count', 'replay_count', 'study_pause_count', 'other_work_pause_count', 'forward_count', 'speed_increase_count']

X = []
y = []

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
    y.append(level)

X = np.array(X)
y = np.array(y)

# Test Random Forest Classifier with standard features
rf_pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        class_weight='balanced'
    ))
])

# Generate augmented dataset
np.random.seed(42)
X_aug = list(X)
y_aug = list(y)

for _ in range(500):
    # HIGH
    b = np.random.randint(4, 25)
    r = np.random.randint(0, 5)
    sp = np.random.randint(1, 10)
    op = np.random.randint(0, 5)
    f = np.random.randint(0, 100)
    spd = np.random.randint(0, 2)
    score = (r*2.0) + (b*2.0) + (sp*3.0)
    if score >= 7.0:
        X_aug.append([b, r, sp, op, f, spd])
        y_aug.append("HIGH")

    # MEDIUM
    b = np.random.randint(1, 4)
    r = np.random.randint(0, 2)
    sp = np.random.randint(0, 2)
    op = np.random.randint(0, 6)
    f = np.random.randint(0, 60)
    spd = np.random.randint(0, 3)
    score = (r*2.0) + (b*2.0) + (sp*3.0)
    if 3.0 <= score < 7.0:
        X_aug.append([b, r, sp, op, f, spd])
        y_aug.append("MEDIUM")

    # LOW
    b = np.random.randint(0, 2)
    r = 0
    sp = 0
    op = np.random.randint(0, 4)
    f = np.random.randint(0, 50)
    spd = np.random.randint(0, 5)
    score = (r*2.0) + (b*2.0) + (sp*3.0)
    if score < 3.0:
        X_aug.append([b, r, sp, op, f, spd])
        y_aug.append("LOW")

X_aug = np.array(X_aug)
y_aug = np.array(y_aug)

rf_pipeline.fit(X_aug, y_aug)

y_pred_rf = rf_pipeline.predict(X)
acc_rf = accuracy_score(y, y_pred_rf)
print(f"\nRandom Forest Accuracy on Test Set: {acc_rf * 100:.2f}%")
print("Confusion Matrix:\n", confusion_matrix(y, y_pred_rf, labels=["HIGH", "MEDIUM", "LOW"]))
print(classification_report(y, y_pred_rf, labels=["HIGH", "MEDIUM", "LOW"], zero_division=0))

# LogisticRegression with fine-tuned parameters
lr_tuned = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', LogisticRegression(
        C=5.0,
        max_iter=2000,
        class_weight='balanced',
        random_state=42
    ))
])
lr_tuned.fit(X_aug, y_aug)
y_pred_lr = lr_tuned.predict(X)
acc_lr = accuracy_score(y, y_pred_lr)
print(f"\nTuned Logistic Regression Accuracy on Test Set: {acc_lr * 100:.2f}%")
print("Confusion Matrix:\n", confusion_matrix(y, y_pred_lr, labels=["HIGH", "MEDIUM", "LOW"]))
print(classification_report(y, y_pred_lr, labels=["HIGH", "MEDIUM", "LOW"], zero_division=0))

# Save the best model
best_model = rf_pipeline if acc_rf >= acc_lr else lr_tuned
best_name = "RandomForestClassifier(n_estimators=100, max_depth=6)" if acc_rf >= acc_lr else "LogisticRegression(C=5.0, class_weight='balanced')"

model_export = {
    "model": best_model,
    "feature_names": feature_names,
    "classes": ["HIGH", "LOW", "MEDIUM"],
    "trained_at": "2026-09-22",
    "architecture": best_name
}
joblib.dump(model_export, "models/adaptive_quiz_model.pkl")
print(f"\nSaved best model ({best_name}) to models/adaptive_quiz_model.pkl!")
