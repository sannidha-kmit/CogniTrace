import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath("."))

from app.services.claude_service import ClaudeService, is_valid_conceptual_question
from app.services.question_service import QuestionService
from app.db.mongodb import get_database

async def test_gemini_ml_priority():
    print("=" * 70)
    print("TESTING GEMINI ML ADAPTIVE PRIORITY CONTEXT & QUESTION GENERATION")
    print("=" * 70)

    course_id = "6a7f29a87959ed0a44852fc7"  # Intoduction to ML

    # -------------------------------------------------------------
    # 1. HIGH CONCEPT TEST
    # Concept: 'Intoduction To Ml Fundamentals'
    # Priority: HIGH, Confidence: 0.999978, Count: 5
    # -------------------------------------------------------------
    high_concept = "Intoduction To Ml Fundamentals"
    high_priority = "HIGH"
    high_confidence = 0.999978
    high_count = 5

    print(f"\n[SCENARIO 1] HIGH Priority Concept: '{high_concept}'")
    print(f"  ML Priority: {high_priority}")
    print(f"  ML Model Confidence: {high_confidence:.6f}")
    print(f"  Required Question Count: {high_count}")

    # Extract concept-specific transcript (strictly for this concept)
    _, _, high_tx = await QuestionService.extract_transcript_for_concept(course_id, high_concept)
    print(f"  Concept Transcript Length: {len(high_tx)} characters")
    print(f"  Concept Transcript Preview: '{high_tx[:160]}...'")

    # Show structured context equivalent sent to Gemini
    high_context = {
        "concept_name": high_concept,
        "quiz_priority": high_priority,
        "confidence": high_confidence,
        "question_count": high_count,
        "transcript": high_tx[:120] + "... [concept-specific text]"
    }
    print(f"\n  Structured Context Passed to Gemini:")
    print(json.dumps(high_context, indent=4))

    # Generate questions via ClaudeService (Gemini / fallback)
    high_mcqs = await ClaudeService.generate_mcqs_from_transcript(
        transcript_text=high_tx,
        concept_name=high_concept,
        count=high_count,
        target_difficulty="EASY",
        course_name="Intoduction to ML",
        quiz_priority=high_priority,
        confidence=high_confidence
    )

    print(f"\n  Gemini Generated {len(high_mcqs)} questions (Requested: {high_count}):")
    assert len(high_mcqs) == high_count, f"Expected {high_count} questions, got {len(high_mcqs)}"

    for idx, q in enumerate(high_mcqs, 1):
        print(f"\n    Q{idx}: {q.question}")
        for opt in q.options:
            marker = " [CORRECT]" if opt == q.correct_answer else ""
            print(f"        * {opt}{marker}")
        print(f"        Difficulty: {q.difficulty}")
        print(f"        Explanation: {q.explanation}")
        assert is_valid_conceptual_question(q), f"Question failed validation: {q.question}"

    print(f"\n  [PASS] HIGH concept received priority HIGH, count 5, and all 5 questions are purely conceptual.")

    # -------------------------------------------------------------
    # 2. LOW CONCEPT TEST
    # Concept: 'Introduction & Concepts'
    # Priority: LOW, Confidence: 1.000000, Count: 1
    # -------------------------------------------------------------
    low_concept = "Introduction & Concepts"
    low_priority = "LOW"
    low_confidence = 1.000000
    low_count = 1

    print(f"\n" + "-" * 70)
    print(f"[SCENARIO 2] LOW Priority Concept: '{low_concept}'")
    print(f"  ML Priority: {low_priority}")
    print(f"  ML Model Confidence: {low_confidence:.6f}")
    print(f"  Required Question Count: {low_count}")

    # Extract concept-specific transcript (strictly for this concept)
    _, _, low_tx = await QuestionService.extract_transcript_for_concept(course_id, low_concept)
    print(f"  Concept Transcript Length: {len(low_tx)} characters")
    print(f"  Concept Transcript Preview: '{low_tx[:160]}...'")

    # Show structured context equivalent sent to Gemini
    low_context = {
        "concept_name": low_concept,
        "quiz_priority": low_priority,
        "confidence": low_confidence,
        "question_count": low_count,
        "transcript": low_tx[:120] + "... [concept-specific text]"
    }
    print(f"\n  Structured Context Passed to Gemini:")
    print(json.dumps(low_context, indent=4))

    # Generate questions via ClaudeService (Gemini / fallback)
    low_mcqs = await ClaudeService.generate_mcqs_from_transcript(
        transcript_text=low_tx,
        concept_name=low_concept,
        count=low_count,
        target_difficulty="HARD",
        course_name="Intoduction to ML",
        quiz_priority=low_priority,
        confidence=low_confidence
    )

    print(f"\n  Gemini Generated {len(low_mcqs)} questions (Requested: {low_count}):")
    assert len(low_mcqs) == low_count, f"Expected {low_count} questions, got {len(low_mcqs)}"

    for idx, q in enumerate(low_mcqs, 1):
        print(f"\n    Q{idx}: {q.question}")
        for opt in q.options:
            marker = " [CORRECT]" if opt == q.correct_answer else ""
            print(f"        * {opt}{marker}")
        print(f"        Difficulty: {q.difficulty}")
        print(f"        Explanation: {q.explanation}")
        assert is_valid_conceptual_question(q), f"Question failed validation: {q.question}"

    print(f"\n  [PASS] LOW concept received priority LOW, count 1, and the question is purely conceptual.")

    print("\n" + "=" * 70)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_gemini_ml_priority())
