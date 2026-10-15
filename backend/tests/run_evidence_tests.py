import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import test target modules
from app.core.research_config import research_settings
from app.schemas.question import GeneratedMCQ
from app.services.evidence_engine import EvidenceEngine
from app.services.student_state_service import StudentConceptStateService
from app.services.question_validation_service import QuestionValidationService


def run_all_tests():
    print("=" * 70)
    print("Running CogniTrace Evidence-Aware Modeling Test Suite")
    print("=" * 70)

    # Test 1
    print("[TEST 1] Testing interaction reliability weights...")
    w_study_pause = EvidenceEngine.get_interaction_weight("study_pause")
    w_replay = EvidenceEngine.get_interaction_weight("replay")
    w_backward_seek = EvidenceEngine.get_interaction_weight("backward_seek")
    w_normal_pause = EvidenceEngine.get_interaction_weight("normal_pause")
    w_other_work_pause = EvidenceEngine.get_interaction_weight("other_work_pause")
    w_forward_seek = EvidenceEngine.get_interaction_weight("forward_seek")

    assert w_study_pause == 1.0, f"Expected 1.0, got {w_study_pause}"
    assert w_replay >= 0.9, f"Expected >= 0.9, got {w_replay}"
    assert w_backward_seek >= 0.8, f"Expected >= 0.8, got {w_backward_seek}"
    assert w_replay > w_other_work_pause, "Replay should outweigh other-work pause"
    assert w_study_pause > w_normal_pause, "Study pause should outweigh normal pause"
    assert w_backward_seek > w_forward_seek, "Backward seek should outweigh forward seek"
    print("  -> PASSED: Interaction reliability weights correctly prioritized.")

    # Test 2
    print("[TEST 2] Testing concept mapping confidence score...")
    concept_seg = {
        "Concept": "Binary Search",
        "ConceptStart": "01:00",  # 60s
        "ConceptEnd": "03:00"     # 180s
    }
    conf_central = EvidenceEngine.calculate_mapping_confidence(
        event_secs=120.0,
        concept_segment=concept_seg,
        transcript_matched=True
    )
    conf_boundary = EvidenceEngine.calculate_mapping_confidence(
        event_secs=61.0,
        concept_segment=concept_seg,
        transcript_matched=True
    )
    conf_distant = EvidenceEngine.calculate_mapping_confidence(
        event_secs=300.0,
        concept_segment=concept_seg,
        transcript_matched=False
    )
    assert 0.0 <= conf_central <= 1.0
    assert 0.0 <= conf_boundary <= 1.0
    assert 0.0 <= conf_distant <= 1.0
    assert conf_central > conf_boundary, f"Central ({conf_central}) should > boundary ({conf_boundary})"
    assert conf_boundary > conf_distant, f"Boundary ({conf_boundary}) should > distant ({conf_distant})"
    print(f"  -> PASSED: Central={conf_central}, Boundary={conf_boundary}, Distant={conf_distant}")

    # Test 3
    print("[TEST 3] Testing exponential temporal decay weighting...")
    now = datetime.now(timezone.utc)
    recent_time = now - timedelta(minutes=15)
    old_time = now - timedelta(days=5)
    w_recent, d_recent = EvidenceEngine.calculate_temporal_weight(recent_time, now, 0.01)
    w_old, d_old = EvidenceEngine.calculate_temporal_weight(old_time, now, 0.01)

    assert w_recent > w_old, f"Recent ({w_recent}) should > Old ({w_old})"
    assert w_recent > 0.99, f"Recent should retain >99%, got {w_recent}"
    assert w_old < 0.40, f"Old should decay to <40%, got {w_old}"
    print(f"  -> PASSED: Recent temporal weight={w_recent}, Old temporal weight={w_old}")

    # Test 4
    print("[TEST 4] Testing mastery model & zero-attempts safety...")
    m0, k0, g0 = StudentConceptStateService.calculate_mastery_score(0, 0)
    assert k0 is False, "Zero attempts should not be marked as known mastery"
    assert m0 is None, "Zero attempts should return None mastery"
    assert g0 == 0.5, "Zero attempts should return neutral knowledge gap"

    m1, k1, g1 = StudentConceptStateService.calculate_mastery_score(1, 1)
    assert m1 == 1.0 and k1 is True and g1 == 0.0

    m3, k3, g3 = StudentConceptStateService.calculate_mastery_score(1, 3)
    m4, k4, g4 = StudentConceptStateService.calculate_mastery_score(2, 4)
    assert m4 > m3, "Correct answer should increase mastery"
    print(f"  -> PASSED: Mastery correctly transitions: 0 att -> None, 1/3 -> {m3}, 2/4 -> {m4}")

    # Test 5
    print("[TEST 5] Testing adaptive difficulty policy...")
    d_low = StudentConceptStateService.determine_target_difficulty(0.20)
    d_med = StudentConceptStateService.determine_target_difficulty(0.60)
    d_high = StudentConceptStateService.determine_target_difficulty(0.85)
    d_none = StudentConceptStateService.determine_target_difficulty(None)
    assert d_low == "EASY"
    assert d_med == "MEDIUM"
    assert d_high == "HARD"
    assert d_none == "MEDIUM"
    print(f"  -> PASSED: Target difficulties: low={d_low}, med={d_med}, high={d_high}, none={d_none}")

    # Test 6
    print("[TEST 6] Testing combined research priority calculation...")
    p_high, l_high = StudentConceptStateService.compute_combined_priority(0.9, 0.8, 0.85)
    p_low, l_low = StudentConceptStateService.compute_combined_priority(0.1, 0.1, 0.2)
    assert l_high == "HIGH" and p_high >= 0.65
    assert l_low == "LOW" and p_low < 0.35
    print(f"  -> PASSED: High struggle priority={p_high} ({l_high}), Low struggle priority={p_low} ({l_low})")

    # Test 7
    print("[TEST 7] Testing question validation layer...")

    async def async_validation_tests():
        # Valid Question
        valid_mcq = GeneratedMCQ(
            concept="Binary Search",
            question="What is the time complexity of Binary Search in the worst case?",
            options=["O(1)", "O(log n)", "O(n)", "O(n^2)"],
            correct_answer="O(log n)",
            difficulty="MEDIUM",
            explanation="Binary search divides search interval in half every step.",
            learning_point="Logarithmic search complexity",
            source_evidence="Binary search splits the range repeatedly"
        )
        res_valid = await QuestionValidationService.validate_mcq(
            mcq=valid_mcq,
            course_id="test_course_123",
            concept_name="Binary Search",
            target_difficulty="MEDIUM",
            transcript_text="Binary search divides the array into halves, giving O(log n) time complexity."
        )
        assert res_valid.status == "approved", f"Expected approved, got {res_valid.status}"
        assert res_valid.options_count_valid is True
        assert res_valid.single_correct_valid is True
        assert res_valid.validation_score >= 0.80

        # Invalid Question: Answer leaked
        leaked_mcq = GeneratedMCQ(
            concept="Binary Search",
            question="Since Binary Search has O(log n) time complexity, what is its complexity?",
            options=["O(1)", "O(log n)", "O(n)", "O(n^2)"],
            correct_answer="O(log n)",
            difficulty="MEDIUM",
            explanation="Leaked answer test.",
            learning_point="Complexity",
            source_evidence="Evidence"
        )
        res_leaked = await QuestionValidationService.validate_mcq(
            mcq=leaked_mcq,
            course_id="test_course_123",
            concept_name="Binary Search",
            target_difficulty="MEDIUM"
        )
        assert res_leaked.no_answer_leakage is False
        print("  -> PASSED: Question validation approves valid MCQs and rejects malformed/leaked ones.")

    asyncio.run(async_validation_tests())

    print("=" * 70)
    print("ALL 7 RESEARCH REQUIREMENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
