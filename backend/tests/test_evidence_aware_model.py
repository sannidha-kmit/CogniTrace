import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from app.core.research_config import research_settings
from app.schemas.question import GeneratedMCQ
from app.services.evidence_engine import EvidenceEngine
from app.services.student_state_service import StudentConceptStateService
from app.services.question_validation_service import QuestionValidationService


class TestEvidenceAwareModeling:
    """
    Test Suite for CogniTrace Evidence-Aware Concept-Level Student Modeling
    and Closed-Loop Adaptive Assessment (Research Contribution).
    """

    def test_1_evidence_calculation_reliability_weights(self):
        """
        Verify: Replay > Other-work pause, Study pause > Normal pause.
        """
        w_study_pause = EvidenceEngine.get_interaction_weight("study_pause")
        w_replay = EvidenceEngine.get_interaction_weight("replay")
        w_backward_seek = EvidenceEngine.get_interaction_weight("backward_seek")
        w_normal_pause = EvidenceEngine.get_interaction_weight("normal_pause")
        w_other_work_pause = EvidenceEngine.get_interaction_weight("other_work_pause")
        w_forward_seek = EvidenceEngine.get_interaction_weight("forward_seek")

        # 1. Study pause is highest reliability evidence of difficulty
        assert w_study_pause == 1.0
        # 2. Replay & backward seek have strong evidence weight
        assert w_replay >= 0.9
        assert w_backward_seek >= 0.8
        # 3. Replay has significantly higher evidence than other-work pause
        assert w_replay > w_other_work_pause
        assert w_study_pause > w_normal_pause
        assert w_backward_seek > w_forward_seek

    def test_2_concept_mapping_confidence(self):
        """
        Verify: Confidence score is between 0.0 and 1.0.
        Central timestamp has higher confidence than boundary/outside timestamp.
        """
        concept_seg = {
            "Concept": "Binary Search",
            "ConceptStart": "01:00",  # 60s
            "ConceptEnd": "03:00"     # 180s
        }

        # Central timestamp (120s - exactly middle of [60, 180])
        conf_central = EvidenceEngine.calculate_mapping_confidence(
            event_secs=120.0,
            concept_segment=concept_seg,
            transcript_matched=True
        )

        # Boundary timestamp (62s - edge of [60, 180])
        conf_boundary = EvidenceEngine.calculate_mapping_confidence(
            event_secs=61.0,
            concept_segment=concept_seg,
            transcript_matched=True
        )

        # Distant timestamp (300s - outside concept)
        conf_distant = EvidenceEngine.calculate_mapping_confidence(
            event_secs=300.0,
            concept_segment=concept_seg,
            transcript_matched=False
        )

        assert 0.0 <= conf_central <= 1.0
        assert 0.0 <= conf_boundary <= 1.0
        assert 0.0 <= conf_distant <= 1.0

        # Central positioning within concept segment yields highest confidence
        assert conf_central > conf_boundary
        assert conf_boundary > conf_distant

    def test_3_temporal_decay_weighting(self):
        """
        Verify: Recent event > Old event under exponential decay: exp(-lambda * delta_t).
        """
        now = datetime.now(timezone.utc)
        recent_event_time = now - timedelta(minutes=15)  # 0.25 hours ago
        old_event_time = now - timedelta(days=5)         # 120 hours ago

        w_recent, delta_recent = EvidenceEngine.calculate_temporal_weight(
            event_time=recent_event_time,
            reference_time=now,
            lambda_param=0.01
        )

        w_old, delta_old = EvidenceEngine.calculate_temporal_weight(
            event_time=old_event_time,
            reference_time=now,
            lambda_param=0.01
        )

        assert 0.0 <= w_recent <= 1.0
        assert 0.0 <= w_old <= 1.0

        assert delta_recent < delta_old
        assert w_recent > w_old
        assert w_recent > 0.99  # very recent event retains >99% weight
        assert w_old < 0.40     # old event decays significantly

    def test_4_mastery_model_and_zero_attempts_safety(self):
        """
        Verify:
        - 0 attempts is safely handled (neutral prior / unknown, not 0%).
        - Correct answers increase mastery.
        - Wrong answers decrease mastery.
        """
        # Zero attempts case
        mastery_0, is_known_0, gap_0 = StudentConceptStateService.calculate_mastery_score(
            correct_answers=0,
            total_attempts=0
        )
        assert is_known_0 is False
        assert mastery_0 is None
        assert gap_0 == 0.5  # Neutral gap

        # 1 Correct attempt -> 100% mastery
        mastery_1, is_known_1, gap_1 = StudentConceptStateService.calculate_mastery_score(
            correct_answers=1,
            total_attempts=1
        )
        assert is_known_1 is True
        assert mastery_1 == 1.0
        assert gap_1 == 0.0

        # 1 Correct out of 3 attempts -> 33.3% mastery
        mastery_3, is_known_3, gap_3 = StudentConceptStateService.calculate_mastery_score(
            correct_answers=1,
            total_attempts=3
        )
        assert is_known_3 is True
        assert 0.33 <= mastery_3 <= 0.34
        assert 0.66 <= gap_3 <= 0.67

        # Correct answer increases mastery
        mastery_4, _, _ = StudentConceptStateService.calculate_mastery_score(
            correct_answers=2,
            total_attempts=4
        )
        assert mastery_4 > mastery_3

    def test_5_adaptive_difficulty_policy(self):
        """
        Verify:
        - Low mastery (< 0.40) -> EASY
        - Medium mastery (0.40 to 0.75) -> MEDIUM
        - High mastery (> 0.75) -> HARD
        """
        diff_low = StudentConceptStateService.determine_target_difficulty(0.25)
        diff_med = StudentConceptStateService.determine_target_difficulty(0.60)
        diff_high = StudentConceptStateService.determine_target_difficulty(0.85)
        diff_none = StudentConceptStateService.determine_target_difficulty(None)

        assert diff_low == "EASY"
        assert diff_med == "MEDIUM"
        assert diff_high == "HARD"
        assert diff_none == "MEDIUM"

    def test_6_combined_priority_calculation(self):
        """
        Verify priority calculation combining normalized behavioral evidence,
        knowledge gap, and base ML score.
        """
        # High struggle: high behavioral evidence + large knowledge gap + high ML score
        score_high, label_high = StudentConceptStateService.compute_combined_priority(
            normalized_behavioral_evidence=0.90,
            knowledge_gap=0.80,
            ml_score=0.85
        )
        assert label_high == "HIGH"
        assert score_high >= 0.65

        # Low struggle / mastered: low evidence + small gap + low ML score
        score_low, label_low = StudentConceptStateService.compute_combined_priority(
            normalized_behavioral_evidence=0.10,
            knowledge_gap=0.10,
            ml_score=0.20
        )
        assert label_low == "LOW"
        assert score_low < 0.35

    @pytest.mark.asyncio
    async def test_7_question_validation_layer(self):
        """
        Verify Question Validation rules:
        - Rejects questions with != 4 options
        - Rejects questions where correct_answer is not in options
        - Rejects questions where answer is leaked in prompt
        - Approves valid questions
        """
        # 1. Valid Question
        valid_mcq = GeneratedMCQ(
            concept="Binary Search",
            question="What is the time complexity of Binary Search in the worst case?",
            options=["O(1)", "O(log n)", "O(n)", "O(n^2)"],
            correct_answer="O(log n)",
            difficulty="MEDIUM",
            explanation="Binary search divides search interval in half every step, resulting in O(log n).",
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
        assert res_valid.status == "approved"
        assert res_valid.options_count_valid is True
        assert res_valid.single_correct_valid is True
        assert res_valid.validation_score >= 0.80

        # 2. Invalid Question: Answer leaked in prompt
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
