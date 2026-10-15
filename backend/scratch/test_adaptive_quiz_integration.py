import asyncio
import os
import sys
import numpy as np
import joblib

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("."))

from app.core.quiz_config import quiz_settings
from app.services.adapters.ml_inference_service import ml_service
from app.services.adapters.feature_service_adapter import FeatureServiceAdapter
from app.services.claude_service import ClaudeService, is_valid_conceptual_question
from app.schemas.question import GeneratedMCQ
from app.db.mongodb import get_database

async def run_tests():
    print("=" * 60)
    print("COGNITRACE ADAPTIVE QUIZ ML + GEMINI INTEGRATION TESTS")
    print("=" * 60)

    # TEST 1: Model Loading & Feature Order
    print("\n[TEST 1] Model Loading & Feature Order Verification...")
    assert ml_service.model is not None, "Model failed to load!"
    print(f"  Model loaded successfully from: {ml_service.model_path}")
    print(f"  Configured Feature Order: {quiz_settings.FEATURE_ORDER}")
    expected_order = [
        "backward_count",
        "replay_count",
        "study_pause_count",
        "other_work_pause_count",
        "forward_count",
        "speed_increase_count"
    ]
    assert quiz_settings.FEATURE_ORDER == expected_order, f"Feature order mismatch! {quiz_settings.FEATURE_ORDER}"
    print("  PASS: Exact 6 features and ordering verified.")

    # TEST 2: Question Allocation Mapping
    print("\n[TEST 2] Priority Question Count Mapping...")
    print(f"  PRIORITY_QUESTION_COUNTS: {quiz_settings.PRIORITY_QUESTION_COUNTS}")
    assert quiz_settings.PRIORITY_QUESTION_COUNTS["HIGH"] == 5, "HIGH must map to 5"
    assert quiz_settings.PRIORITY_QUESTION_COUNTS["MEDIUM"] == 3, "MEDIUM must map to 3"
    assert quiz_settings.PRIORITY_QUESTION_COUNTS["LOW"] == 1, "LOW must map to 1"
    print("  PASS: Priority question counts strictly HIGH: 5, MEDIUM: 3, LOW: 1.")

    # TEST 3: Benchmark Prediction on S24A003 features
    print("\n[TEST 3] Benchmark Sample Inference (Section 24 Specification)...")
    sample_features = {
        "backward_count": 13,
        "replay_count": 0,
        "study_pause_count": 0,
        "other_work_pause_count": 0,
        "forward_count": 4,
        "speed_increase_count": 1
    }
    pred_res = ml_service.predict(sample_features)
    print(f"  Input: {sample_features}")
    print(f"  Prediction: {pred_res.priority.value}")
    print(f"  Confidence: {pred_res.score:.6f}")
    assert pred_res.priority.value == "HIGH", f"Expected HIGH, got {pred_res.priority.value}"
    assert pred_res.score > 0.9999, f"Expected confidence > 0.9999, got {pred_res.score}"
    q_count = quiz_settings.PRIORITY_QUESTION_COUNTS[pred_res.priority.value]
    assert q_count == 5, f"Expected 5 questions, got {q_count}"
    print("  PASS: Benchmark sample S24A003 predicted HIGH with 5 questions.")

    # TEST 4: Live MongoDB Telemetry Aggregation (No CSV runtime)
    print("\n[TEST 4] Live MongoDB Feature Aggregation...")
    db = await get_database()
    student_id = "S24A003"
    course_id = "6a7f29a87959ed0a44852fc7"  # Intoduction to ML
    concept_features = await FeatureServiceAdapter.get_concept_features(student_id, course_id)
    print(f"  Retrieved {len(concept_features)} concept feature sets for {student_id}:")
    
    found_high = False
    for cf in concept_features:
        pred = ml_service.predict(cf.features)
        count = quiz_settings.PRIORITY_QUESTION_COUNTS[pred.priority.value]
        print(f"    - Concept: '{cf.concept_name}'")
        print(f"      Features: {cf.features}")
        print(f"      Priority: {pred.priority.value}, Confidence: {pred.score:.6f}, Questions: {count}")
        if cf.concept_name == "Intoduction To Ml Fundamentals":
            assert pred.priority.value == "HIGH", f"Expected HIGH for Intoduction To Ml Fundamentals, got {pred.priority.value}"
            assert count == 5
            found_high = True
        elif cf.concept_name in ["Introduction & Concepts", "Search Fundamentals"]:
            assert pred.priority.value == "LOW", f"Expected LOW for {cf.concept_name}, got {pred.priority.value}"
            assert count == 1
    assert found_high, "Did not find Intoduction To Ml Fundamentals in concepts!"
    print("  PASS: Live MongoDB telemetry aggregated into concept-level features and correct priorities.")

    # TEST 5: Question Validation & Forbidden Patterns Filter
    print("\n[TEST 5] Question Validation Rules...")
    # Good conceptual question
    good_mcq = GeneratedMCQ(
        question="Why does supervised machine learning require labeled input-output pairs during training?",
        options=[
            "To allow the model to learn mapping functions from inputs to correct targets",
            "To format the display text inside terminal user interfaces",
            "To bypass standard system memory hierarchy during execution",
            "To eliminate the need for numerical weights or parameters"
        ],
        correct_answer="To allow the model to learn mapping functions from inputs to correct targets",
        difficulty="MEDIUM",
        explanation="Supervised learning infers a function from labeled training data consisting of training examples.",
        concept="Supervised Learning"
    )
    assert is_valid_conceptual_question(good_mcq), "Valid conceptual question was incorrectly rejected!"
    print("  PASS: High-quality conceptual question accepted.")

    # Bad video-meta / greeting questions
    bad_q1 = GeneratedMCQ(
        question="What did the instructor say at the beginning of the video?",
        options=["Welcome to the lecture", "Good morning students", "Hello everyone", "Thank you"],
        correct_answer="Good morning students",
        difficulty="EASY",
        explanation="Instructor greeting",
        concept="Supervised Learning"
    )
    assert not is_valid_conceptual_question(bad_q1), "Forbidden greeting question was NOT rejected!"
    print("  PASS: Question 'What did the instructor say at the beginning' successfully rejected.")

    bad_q2 = GeneratedMCQ(
        question="Who welcomed the students and introduced the topic?",
        options=["The instructor", "A guest speaker", "The course TA", "The department dean"],
        correct_answer="The instructor",
        difficulty="EASY",
        explanation="Video opening",
        concept="Supervised Learning"
    )
    assert not is_valid_conceptual_question(bad_q2), "Forbidden speaker identity question was NOT rejected!"
    print("  PASS: Question 'Who welcomed the students' successfully rejected.")

    bad_q3 = GeneratedMCQ(
        question="How does supervised learning classify data?",
        options=["Good morning", "By learning decision boundaries", "Welcome to the video", "Thank you"],
        correct_answer="By learning decision boundaries",
        difficulty="MEDIUM",
        explanation="Classification mechanism",
        concept="Supervised Learning"
    )
    assert not is_valid_conceptual_question(bad_q3), "Forbidden greeting options were NOT rejected!"
    print("  PASS: MCQ with greeting options successfully rejected.")

    # TEST 6: Conceptual MCQ Generation
    print("\n[TEST 6] Conceptual MCQ Generation for Concept...")
    sample_transcript = """
    In machine learning, supervised learning algorithms build a mathematical model of a set of data that contains both the inputs and the desired outputs.
    The data is known as training data, and consists of a set of training examples.
    Each training example has one or more inputs and the desired output, also known as a supervisory signal.
    In the mathematical model, each training example is represented by an array or vector, sometimes called a feature vector.
    Through iterative optimization of an objective function, supervised learning algorithms learn a function that can be used to predict the output associated with new inputs.
    Classification and regression are the two primary categories of supervised learning tasks.
    In classification, the output is restricted to a limited set of categorical values, whereas in regression, the output may have any numerical value within a continuous range.
    """
    mcqs = await ClaudeService.generate_mcqs_from_transcript(
        transcript_text=sample_transcript,
        concept_name="Supervised Learning Fundamentals",
        count=3,
        target_difficulty="MEDIUM",
        course_name="Machine Learning"
    )
    assert len(mcqs) == 3, f"Expected 3 MCQs, got {len(mcqs)}"
    for i, m in enumerate(mcqs, 1):
        print(f"\n  Question {i}: {m.question}")
        for opt in m.options:
            marker = " [CORRECT]" if opt == m.correct_answer else ""
            print(f"    - {opt}{marker}")
        print(f"    Difficulty: {m.difficulty}")
        print(f"    Explanation: {m.explanation}")
        assert is_valid_conceptual_question(m), f"Generated question failed validation: {m.question}"
        assert m.correct_answer in m.options, "Correct answer not in options!"
    print("\n  PASS: All generated questions are purely conceptual and pass strict validation.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
