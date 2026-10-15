"""
CogniTrace Adaptive Quiz Model - Model Evaluation

Evaluates the saved Logistic Regression model using a synthetic
held-out test dataset.

Metrics:
    - Accuracy
    - Precision
    - Recall
    - F1 Score
    - Multiclass ROC-AUC
    - Per-class ROC-AUC
    - Confusion Matrix
    - Classification Report

IMPORTANT:
    This reports synthetic-data evaluation metrics.
    It is NOT real-student accuracy or real-student AUC.
"""

import os
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "adaptive_quiz_model.pkl"
)

FEATURES = [
    "backward_count",
    "replay_count",
    "study_pause_count",
    "other_work_pause_count",
    "forward_count",
    "speed_increase_count"
]

RANDOM_SEED = 42
TEST_SAMPLES = 600

CLASS_LABELS = [
    "HIGH",
    "LOW",
    "MEDIUM"
]


# ============================================================
# LOAD SAVED MODEL
# ============================================================

def load_model():

    print("=" * 70)
    print("COGNITRACE ADAPTIVE QUIZ MODEL EVALUATION")
    print("=" * 70)

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"\nModel file not found:\n{MODEL_PATH}\n"
        )

    package = joblib.load(MODEL_PATH)

    if not isinstance(package, dict):
        raise ValueError(
            "adaptive_quiz_model.pkl is not a model package dictionary."
        )

    if "model" not in package:
        raise ValueError(
            "Model package does not contain 'model'."
        )

    model = package["model"]

    print("\nModel information")
    print("-" * 70)

    print("Model type :", type(model).__name__)
    print("Version    :", package.get("version", "Unknown"))
    print("Classes    :", package.get("classes", "Unknown"))

    print("\nFeatures")
    print("-" * 70)

    for i, feature in enumerate(
        package.get("feature_names", FEATURES),
        start=1
    ):
        print(f"{i}. {feature}")

    return model


# ============================================================
# GENERATE SYNTHETIC TEST DATA
# ============================================================

def generate_test_data():

    print("\nGenerating synthetic held-out test data...")
    print("-" * 70)

    np.random.seed(RANDOM_SEED)

    n = TEST_SAMPLES

    data = pd.DataFrame({
        "backward_count": np.random.poisson(3.2, n),
        "replay_count": np.random.poisson(3.3, n),
        "study_pause_count": np.random.poisson(2.7, n),
        "other_work_pause_count": np.random.poisson(2.0, n),
        "forward_count": np.random.poisson(2.5, n),
        "speed_increase_count": np.random.poisson(1.5, n)
    })

    data = data.clip(lower=0)

    # --------------------------------------------------------
    # Difficulty signal
    #
    # Positive signals:
    #   backward
    #   replay
    #   study pauses
    #
    # Negative / easier signals:
    #   other-work pauses
    #   forward seeks
    #   speed increases
    # --------------------------------------------------------

    difficulty_signal = (
        data["backward_count"] * 2.0
        + data["replay_count"] * 2.0
        + data["study_pause_count"] * 2.5
        - data["other_work_pause_count"] * 1.0
        - data["forward_count"] * 1.0
        - data["speed_increase_count"] * 0.8
    )

    # --------------------------------------------------------
    # Create LOW / MEDIUM / HIGH labels
    # --------------------------------------------------------

    low_threshold = np.percentile(
        difficulty_signal,
        33
    )

    high_threshold = np.percentile(
        difficulty_signal,
        66
    )

    labels = np.where(
        difficulty_signal <= low_threshold,
        "LOW",
        np.where(
            difficulty_signal <= high_threshold,
            "MEDIUM",
            "HIGH"
        )
    )

    data["quiz_priority"] = labels

    return data


# ============================================================
# CALCULATE ROC-AUC
# ============================================================

def calculate_auc(model, X_test, y_test):

    if not hasattr(model, "predict_proba"):
        raise ValueError(
            "The saved model does not support predict_proba(). "
            "ROC-AUC requires probability scores."
        )

    # --------------------------------------------------------
    # Get probability predictions
    # --------------------------------------------------------

    y_proba = model.predict_proba(X_test)

    # Classes used by the model
    model_classes = list(model.classes_)

    print("\nModel probability classes")
    print("-" * 70)
    print(model_classes)

    # --------------------------------------------------------
    # Multiclass ROC-AUC
    #
    # One-vs-Rest (OvR)
    # Weighted average across classes
    # --------------------------------------------------------

    auc_weighted = roc_auc_score(
        y_test,
        y_proba,
        labels=model_classes,
        multi_class="ovr",
        average="weighted"
    )

    auc_macro = roc_auc_score(
        y_test,
        y_proba,
        labels=model_classes,
        multi_class="ovr",
        average="macro"
    )

    # --------------------------------------------------------
    # Per-class ROC-AUC
    # --------------------------------------------------------

    y_test_binary = pd.get_dummies(
        y_test
    ).reindex(
        columns=model_classes,
        fill_value=0
    )

    per_class_auc = {}

    for i, class_name in enumerate(model_classes):

        try:

            class_auc = roc_auc_score(
                y_test_binary.iloc[:, i],
                y_proba[:, i]
            )

            per_class_auc[class_name] = class_auc

        except ValueError:

            per_class_auc[class_name] = float("nan")

    return (
        auc_weighted,
        auc_macro,
        per_class_auc
    )


# ============================================================
# EVALUATE MODEL
# ============================================================

def evaluate_model(model, test_data):

    X_test = test_data[FEATURES]
    y_test = test_data["quiz_priority"]

    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    y_pred = model.predict(X_test)

    # --------------------------------------------------------
    # Probability predictions
    # --------------------------------------------------------

    if not hasattr(model, "predict_proba"):
        raise ValueError(
            "Model does not support predict_proba(). "
            "ROC-AUC cannot be calculated."
        )

    y_proba = model.predict_proba(X_test)

    # ========================================================
    # CLASSIFICATION METRICS
    # ========================================================

    accuracy = accuracy_score(
        y_test,
        y_pred
    )

    precision = precision_score(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0
    )

    recall = recall_score(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0
    )

    # ========================================================
    # ROC-AUC
    # ========================================================

    (
        auc_weighted,
        auc_macro,
        per_class_auc
    ) = calculate_auc(
        model,
        X_test,
        y_test
    )

    # ========================================================
    # RESULTS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("MODEL PERFORMANCE")
    print("=" * 70)

    print(f"\nTest Samples : {len(test_data)}")
    print(f"Model        : {type(model).__name__}")

    print("\nClassification Metrics")
    print("-" * 70)

    print(f"Accuracy          : {accuracy:.6f}")
    print(f"Accuracy (%)      : {accuracy * 100:.2f}%")

    print(f"Precision         : {precision:.6f}")
    print(f"Recall            : {recall:.6f}")
    print(f"F1 Score          : {f1:.6f}")

    # ========================================================
    # ROC-AUC RESULTS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("ROC-AUC PERFORMANCE")
    print("=" * 70)

    print("\nMulticlass ROC-AUC")
    print("-" * 70)

    print(
        f"ROC-AUC (Weighted, OvR) : "
        f"{auc_weighted:.6f}"
    )

    print(
        f"ROC-AUC (Macro, OvR)    : "
        f"{auc_macro:.6f}"
    )

    print("\nROC-AUC by Class")
    print("-" * 70)

    for class_name in CLASS_LABELS:

        if class_name in per_class_auc:

            value = per_class_auc[class_name]

            if np.isnan(value):
                print(
                    f"{class_name:<10}: N/A"
                )
            else:
                print(
                    f"{class_name:<10}: "
                    f"{value:.6f}"
                )

    # ========================================================
    # CONFUSION MATRIX
    # ========================================================

    cm = confusion_matrix(
        y_test,
        y_pred,
        labels=CLASS_LABELS
    )

    print("\n")
    print("=" * 70)
    print("CONFUSION MATRIX")
    print("=" * 70)

    print("\n                 Predicted")
    print("              HIGH   LOW   MEDIUM")
    print("-" * 45)

    for i, actual in enumerate(CLASS_LABELS):

        print(
            f"Actual {actual:<7} "
            f"{cm[i][0]:>5} "
            f"{cm[i][1]:>6} "
            f"{cm[i][2]:>7}"
        )

    # ========================================================
    # CLASSIFICATION REPORT
    # ========================================================

    print("\n")
    print("=" * 70)
    print("CLASSIFICATION REPORT")
    print("=" * 70)

    print(
        classification_report(
            y_test,
            y_pred,
            labels=CLASS_LABELS,
            zero_division=0
        )
    )

    # ========================================================
    # PREDICTION DISTRIBUTION
    # ========================================================

    print("=" * 70)
    print("PREDICTION DISTRIBUTION")
    print("=" * 70)

    prediction_counts = pd.Series(
        y_pred
    ).value_counts()

    for priority in CLASS_LABELS:

        count = prediction_counts.get(
            priority,
            0
        )

        percentage = (
            count / len(y_pred)
        ) * 100

        print(
            f"{priority:<8}: "
            f"{count:>4} "
            f"({percentage:.2f}%)"
        )

    # ========================================================
    # ACTUAL CLASS DISTRIBUTION
    # ========================================================

    print("\n")
    print("=" * 70)
    print("ACTUAL TEST LABEL DISTRIBUTION")
    print("=" * 70)

    actual_counts = y_test.value_counts()

    for priority in CLASS_LABELS:

        count = actual_counts.get(
            priority,
            0
        )

        percentage = (
            count / len(y_test)
        ) * 100

        print(
            f"{priority:<8}: "
            f"{count:>4} "
            f"({percentage:.2f}%)"
        )

    # ========================================================
    # IMPORTANT NOTE
    # ========================================================

    print("\n")
    print("=" * 70)
    print("IMPORTANT")
    print("=" * 70)

    print(
        "These metrics are calculated on SYNTHETIC test data."
    )

    print(
        "ROC-AUC measures how well the model separates "
        "the LOW, MEDIUM and HIGH classes using predicted "
        "probabilities."
    )

    print(
        "They represent ML model validation, NOT real-student "
        "learning accuracy."
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    # Ignore sklearn version warnings during evaluation
    warnings.filterwarnings(
        "ignore",
        category=UserWarning
    )

    try:

        # Load trained model
        model = load_model()

        # Generate synthetic held-out test data
        test_data = generate_test_data()

        # Evaluate model
        evaluate_model(
            model,
            test_data
        )

    except Exception as e:

        print("\nERROR")
        print("-" * 70)
        print(str(e))

        raise


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()