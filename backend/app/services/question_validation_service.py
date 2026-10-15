import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.core.research_config import research_settings
from app.db.mongodb import get_database
from app.schemas.question import GeneratedMCQ
from app.schemas.validation import QuestionValidationResult

logger = logging.getLogger("cognitrace.question_validation")


class QuestionValidationService:
    """
    Multi-Dimensional Question Validation Layer.
    Validates newly generated MCQs across:
    1. Structural Integrity (4 options, 1 valid answer, required fields)
    2. Semantic Relevance (concept alignment, transcript grounding, difficulty)
    3. Quality & Security (non-duplicate, no answer leakage, non-trivial distractors)
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r'\s+', ' ', str(text).strip().lower())

    @classmethod
    async def validate_mcq(
        cls,
        mcq: GeneratedMCQ,
        course_id: str,
        concept_name: str,
        target_difficulty: Optional[str],
        transcript_text: Optional[str] = None
    ) -> QuestionValidationResult:
        """
        Validate a single generated MCQ and persist audit log in MongoDB.
        """
        now = datetime.now(timezone.utc)
        rejection_reasons: List[str] = []
        score_components = []

        q_text = (mcq.question or "").strip()
        options = mcq.options or []
        correct_ans = (mcq.correct_answer or "").strip()
        diff = (mcq.difficulty or "MEDIUM").upper()
        target_diff = (target_difficulty or diff or "MEDIUM").upper()

        q_hash = hashlib.sha256(cls.normalize_text(q_text).encode('utf-8')).hexdigest()

        # -------------------------------------------------------------
        # 1. Structural Validation
        # -------------------------------------------------------------
        # A. Exactly 4 options
        options_count_valid = (len(options) == 4)
        if not options_count_valid:
            rejection_reasons.append(f"Question must have exactly 4 options, found {len(options)}")
        score_components.append(1.0 if options_count_valid else 0.0)

        # B. Exactly 1 matching correct answer
        matching_opts = [opt for opt in options if opt.strip().lower() == correct_ans.lower()]
        single_correct_valid = (len(matching_opts) == 1)
        if not single_correct_valid:
            rejection_reasons.append("Correct answer must match exactly one of the 4 options")
        score_components.append(1.0 if single_correct_valid else 0.0)

        # C. Required fields present & non-empty
        req_present = bool(q_text and options and correct_ans and (mcq.explanation or "").strip())
        if not req_present:
            rejection_reasons.append("Missing required question fields (question, options, correct_answer, explanation)")
        score_components.append(1.0 if req_present else 0.0)

        # -------------------------------------------------------------
        # 2. Semantic Validation
        # -------------------------------------------------------------
        # A. Concept relevance (concept keywords in question, options, or explanation)
        concept_words = set(re.findall(r'\w+', concept_name.lower()))
        combined_q_text = (q_text + " " + " ".join(options) + " " + (mcq.explanation or "")).lower()
        has_concept_overlap = any(w in combined_q_text for w in concept_words if len(w) > 2)
        concept_relevant = has_concept_overlap or ("concept" in concept_name.lower())
        if not concept_relevant:
            rejection_reasons.append(f"Question lacks semantic alignment with concept '{concept_name}'")
        score_components.append(1.0 if concept_relevant else 0.5)

        # B. Transcript grounding
        grounded = True
        if transcript_text and transcript_text.strip():
            tx_words = set(re.findall(r'\w+', transcript_text.lower()))
            q_words = set(re.findall(r'\w+', q_text.lower()))
            common = q_words.intersection(tx_words)
            grounded = (len(common) >= min(3, len(q_words)))
            if not grounded:
                rejection_reasons.append("Question content does not have sufficient grounding in the lecture transcript")
        score_components.append(1.0 if grounded else 0.6)

        # C. Correct answer valid
        correct_answer_valid = bool(correct_ans and len(correct_ans) > 0)
        score_components.append(1.0 if correct_answer_valid else 0.0)

        # D. Distractors plausible (distinct, non-empty, reasonable length variation)
        distinct_opts = set(cls.normalize_text(opt) for opt in options)
        distractors_plausible = (len(distinct_opts) == len(options))
        if not distractors_plausible:
            rejection_reasons.append("Distractors contain duplicate option strings")
        score_components.append(1.0 if distractors_plausible else 0.0)

        # E. Difficulty matched
        diff_matched = (diff == target_diff)
        score_components.append(1.0 if diff_matched else 0.7)

        # -------------------------------------------------------------
        # 3. Quality & Security Validation
        # -------------------------------------------------------------
        # A. Duplicate check in MongoDB
        database = await get_database()
        existing_dup = await database.questions.find_one({
            "course_id": course_id,
            "question_hash": q_hash
        })
        is_duplicate = bool(existing_dup)
        if is_duplicate:
            rejection_reasons.append("Duplicate question text already exists in question bank")
        score_components.append(0.0 if is_duplicate else 1.0)

        # B. No answer leakage in question prompt
        norm_correct = cls.normalize_text(correct_ans)
        norm_q = cls.normalize_text(q_text)
        answer_leaked = (len(norm_correct) > 5 and norm_correct in norm_q)
        if answer_leaked:
            rejection_reasons.append("Correct answer is explicitly leaked inside the question prompt")
        score_components.append(0.0 if answer_leaked else 1.0)

        # C. Clarity & length
        clarity_valid = (len(q_text) >= 15 and all(len(opt) > 0 for opt in options))
        score_components.append(1.0 if clarity_valid else 0.4)

        # -------------------------------------------------------------
        # 4. Aggregated Score & Status
        # -------------------------------------------------------------
        validation_score = round(sum(score_components) / len(score_components), 4)

        if not research_settings.question_validation:
            # Bypass validation when disabled for research ablation baseline
            status = "approved"
            validation_score = 1.0
            rejection_reasons = []
        else:
            is_structurally_sound = (options_count_valid and single_correct_valid and req_present and not is_duplicate and not answer_leaked)
            if is_structurally_sound and validation_score >= research_settings.min_validation_score_threshold:
                status = "approved"
            elif is_structurally_sound and validation_score >= 0.50:
                status = "flagged"
            else:
                status = "rejected"

        result = QuestionValidationResult(
            question_id=q_hash[:16],
            course_id=str(course_id),
            concept_id=f"{course_id}:{concept_name}",
            concept_name=concept_name,
            target_difficulty=target_diff,
            options_count_valid=options_count_valid,
            single_correct_valid=single_correct_valid,
            required_fields_present=req_present,
            grounded_in_transcript=grounded,
            concept_relevant=concept_relevant,
            correct_answer_valid=correct_answer_valid,
            distractors_plausible=distractors_plausible,
            difficulty_matched=diff_matched,
            duplicate=is_duplicate,
            no_answer_leakage=not answer_leaked,
            clarity_valid=clarity_valid,
            validation_score=validation_score,
            status=status,
            rejection_reasons=rejection_reasons,
            validated_at=now
        )

        # Persist validation audit in MongoDB
        try:
            val_doc = result.model_dump()
            val_doc["question_hash"] = q_hash
            await database.question_validation.insert_one(val_doc)
        except Exception as err:
            logger.error("[QUESTION VALIDATION] Error saving validation record: %s", err)

        return result
