"""
Post-Answer Learning & Revision — Comprehensive Test Suite
===========================================================
12 isolated tests covering all requirements from the Post-Answer Learning spec.
All tests use mocked dependencies (no real DB, no real AI, no network calls).
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import patch, MagicMock, AsyncMock

from app.schemas.quiz import (
    LearningSupport,
    RevisionResource,
    QuizSessionStatus,
    InternalQuizQuestion,
)
from app.services.adaptive_quiz_service import AdaptiveQuizService
from app.services.explanation_service import ExplanationService
from app.services.learning_resource_service import LearningResourceService
from app.services.revision_link_service import RevisionLinkService
from app.repositories.quiz_session_repository import QuizSessionRepository


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_questions_raw():
    """Raw question dicts as stored in a MongoDB quiz session document."""
    return [
        {
            "question_id": "q1",
            "concept_id": "CSE101:Stack",
            "concept_name": "Stack",
            "question_text": "Which data structure follows LIFO?",
            "options": ["Queue", "Stack", "Array", "Tree"],
            "correct_answer": "Stack",
            "difficulty": "MEDIUM",
            "explanation": "A stack follows the LIFO principle.",
            "answered": False,
            "selected_option": None,
            "is_correct": None,
            "answered_at": None,
            "learning_support": None,
        },
        {
            "question_id": "q2",
            "concept_id": "CSE101:BinarySearch",
            "concept_name": "Binary Search",
            "question_text": "Binary search requires the input to be?",
            "options": ["Sorted", "Reversed", "Random", "Empty"],
            "correct_answer": "Sorted",
            "difficulty": "EASY",
            "explanation": "Binary search requires sorted input.",
            "answered": False,
            "selected_option": None,
            "is_correct": None,
            "answered_at": None,
            "learning_support": None,
        },
    ]


@pytest.fixture
def active_session(sample_questions_raw):
    """A standard active quiz session for testing."""
    return {
        "quiz_session_id": str(uuid.uuid4()),
        "student_id": "S1001",
        "course_id": str(ObjectId()),
        "status": "active",
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "current_question_index": 0,
        "total_questions": 2,
        "answered_questions": 0,
        "correct_count": 0,
        "wrong_count": 0,
        "score": 0.0,
        "current_difficulty": "MEDIUM",
        "questions": sample_questions_raw,
        "history": [],
    }


@pytest.fixture
def mock_revision_resource():
    """A realistic RevisionResource for use in mocked returns."""
    return RevisionResource(
        video_id="dQw4w9WgXcQ",
        video_title="Data Structures — Stack",
        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        timestamp_seconds=272,
        timestamp_display="04:32",
        revision_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=272s",
    )


# =====================================================================
# TEST 1 — Correct Answer Returns Explanation
# =====================================================================
@pytest.mark.asyncio
async def test_correct_answer_returns_explanation(active_session, mock_revision_resource):
    """
    Verify: correct=True, explanation returned, learning_support populated.
    """
    session = active_session
    session_id = session["quiz_session_id"]
    student_id = session["student_id"]

    with patch.object(QuizSessionRepository, "get_session", return_value=session), \
         patch.object(QuizSessionRepository, "record_answer_submission", return_value=session), \
         patch.object(ExplanationService, "generate_explanation",
                      return_value=("Correct! A stack follows the LIFO principle.", "available")), \
         patch.object(LearningResourceService, "get_revision_resource",
                      return_value=mock_revision_resource):

        res = await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "Stack")

        assert res.is_correct is True
        assert res.learning_support is not None
        assert res.learning_support.explanation is not None
        assert len(res.learning_support.explanation) > 0
        assert res.learning_support.explanation_status == "available"
        assert res.learning_support.concept_id == "CSE101:Stack"
        assert res.learning_support.concept_name == "Stack"


# =====================================================================
# TEST 2 — Wrong Answer Returns Explanation AND Revision Resource
# =====================================================================
@pytest.mark.asyncio
async def test_wrong_answer_returns_explanation_and_revision(active_session, mock_revision_resource):
    """
    Verify: correct=False, explanation returned, revision resource with video + timestamp returned.
    """
    session = active_session
    session_id = session["quiz_session_id"]
    student_id = session["student_id"]

    wrong_explanation = (
        "Your answer is incorrect. The correct answer is Stack. "
        "A stack follows the LIFO (Last In, First Out) principle. "
        "A queue follows FIFO, which is why Queue is not correct."
    )

    with patch.object(QuizSessionRepository, "get_session", return_value=session), \
         patch.object(QuizSessionRepository, "record_answer_submission", return_value=session), \
         patch.object(ExplanationService, "generate_explanation",
                      return_value=(wrong_explanation, "available")), \
         patch.object(LearningResourceService, "get_revision_resource",
                      return_value=mock_revision_resource):

        res = await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "Queue")

        assert res.is_correct is False
        assert res.learning_support is not None
        assert res.learning_support.explanation is not None
        assert "incorrect" in res.learning_support.explanation.lower() or "stack" in res.learning_support.explanation.lower()
        assert res.learning_support.revision is not None
        assert res.learning_support.revision.video_id == "dQw4w9WgXcQ"
        assert res.learning_support.revision.timestamp_seconds == 272
        assert res.learning_support.revision.timestamp_display == "04:32"
        assert "t=272s" in res.learning_support.revision.revision_url


# =====================================================================
# TEST 3 — Correctness Determined by Backend, NOT AI
# =====================================================================
@pytest.mark.asyncio
async def test_correctness_determined_by_backend(active_session):
    """
    Verify correctness comes from trusted Question Bank data (backend comparison),
    NOT from the AI explanation service. The AI receives is_correct as a parameter,
    it does not determine it.
    """
    session = active_session
    session_id = session["quiz_session_id"]
    student_id = session["student_id"]

    # Track the arguments passed to ExplanationService.generate_explanation
    explanation_call_args = {}

    async def mock_generate_explanation(**kwargs):
        explanation_call_args.update(kwargs)
        return ("Mocked explanation", "available")

    with patch.object(QuizSessionRepository, "get_session", return_value=session), \
         patch.object(QuizSessionRepository, "record_answer_submission", return_value=session), \
         patch.object(ExplanationService, "generate_explanation", side_effect=mock_generate_explanation), \
         patch.object(LearningResourceService, "get_revision_resource", return_value=None):

        # Submit wrong answer
        res = await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "Queue")

        # Backend determined correctness independently
        assert res.is_correct is False

        # AI was told the correct answer and the result — it did not decide correctness
        assert explanation_call_args.get("is_correct") is False
        assert explanation_call_args.get("correct_answer") == "Stack"
        assert explanation_call_args.get("student_answer") == "Queue"


# =====================================================================
# TEST 4 — AI Failure Does NOT Break Quiz Submission
# =====================================================================
@pytest.mark.asyncio
async def test_ai_failure_does_not_break_submission(active_session):
    """
    Mock AI failure. Expected: answer submission succeeds, quiz continues,
    explanation_status = 'unavailable', explanation is None or fallback.
    """
    session = active_session
    session_id = session["quiz_session_id"]
    student_id = session["student_id"]

    with patch.object(QuizSessionRepository, "get_session", return_value=session), \
         patch.object(QuizSessionRepository, "record_answer_submission", return_value=session), \
         patch.object(ExplanationService, "generate_explanation",
                      return_value=(None, "unavailable")), \
         patch.object(LearningResourceService, "get_revision_resource", return_value=None):

        # Answer submission must succeed even when AI fails
        res = await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "Queue")

        assert res.is_correct is False  # Correctness still determined
        assert res.question_id == "q1"
        assert res.learning_support is not None
        assert res.learning_support.explanation_status == "unavailable"
        # Quiz continues — remaining_questions still correct
        assert res.remaining_questions == 1
        assert res.is_completed is False


# =====================================================================
# TEST 5 — Video Mapping from Concept Segments
# =====================================================================
@pytest.mark.asyncio
async def test_video_mapping_from_concept_segments():
    """
    Verify: course_id + concept_id -> correct video from concept_segments collection.
    """
    course_id = str(ObjectId())

    mock_course = {
        "_id": ObjectId(course_id),
        "course_name": "Data Structures",
        "youtube_url": "https://www.youtube.com/watch?v=abc12345678",
    }
    mock_concept_doc = {
        "course_id": course_id,
        "segments": [
            {"Concept": "Stack", "ConceptStart": "04:32"},
            {"Concept": "Queue", "ConceptStart": "12:15"},
        ],
    }

    mock_db = MagicMock()
    mock_db.courses.find_one = AsyncMock(return_value=mock_course)
    mock_db.concept_segments.find_one = AsyncMock(return_value=mock_concept_doc)

    with patch("app.services.learning_resource_service.get_database", AsyncMock(return_value=mock_db)):
        result = await LearningResourceService.get_revision_resource(
            course_id=course_id,
            concept_id="CSE101:Stack",
            concept_name="Stack",
        )

    assert result is not None
    assert result.video_id == "abc12345678"
    assert result.timestamp_seconds == 272  # 04:32 = 4*60 + 32 = 272
    assert result.timestamp_display == "04:32"
    assert "t=272s" in result.revision_url


# =====================================================================
# TEST 6 — Timestamp Conversion (seconds <-> display)
# =====================================================================
def test_timestamp_conversion():
    """
    Verify: 272 seconds -> '04:32', 3725 -> '01:02:05'.
    Verify: '04:32' -> 272, '01:02:05' -> 3725.
    """
    # Seconds -> Display
    assert RevisionLinkService.format_seconds_to_timestamp(272) == "04:32"
    assert RevisionLinkService.format_seconds_to_timestamp(0) == "00:00"
    assert RevisionLinkService.format_seconds_to_timestamp(3725) == "01:02:05"
    assert RevisionLinkService.format_seconds_to_timestamp(60) == "01:00"
    assert RevisionLinkService.format_seconds_to_timestamp(None) is None
    assert RevisionLinkService.format_seconds_to_timestamp(-1) is None

    # Display -> Seconds
    assert RevisionLinkService.parse_timestamp_to_seconds("04:32") == 272
    assert RevisionLinkService.parse_timestamp_to_seconds("00:00") == 0
    assert RevisionLinkService.parse_timestamp_to_seconds("01:02:05") == 3725
    assert RevisionLinkService.parse_timestamp_to_seconds("01:00") == 60
    assert RevisionLinkService.parse_timestamp_to_seconds(None) is None
    assert RevisionLinkService.parse_timestamp_to_seconds("") is None
    assert RevisionLinkService.parse_timestamp_to_seconds(272) == 272


# =====================================================================
# TEST 7 — Revision URL Generation
# =====================================================================
def test_revision_url_generation():
    """
    Verify the generated URL contains the correct video ID and timestamp.
    """
    base_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # With timestamp
    url_with_ts = RevisionLinkService.create_revision_url(base_url, 272)
    assert "dQw4w9WgXcQ" in url_with_ts
    assert "t=272s" in url_with_ts

    # Without timestamp — returns clean base URL
    url_without_ts = RevisionLinkService.create_revision_url(base_url, None)
    assert "dQw4w9WgXcQ" in url_without_ts
    assert "t=" not in url_without_ts

    # youtu.be short URL format
    short_url = "https://youtu.be/dQw4w9WgXcQ"
    url_short = RevisionLinkService.create_revision_url(short_url, 418)
    assert "dQw4w9WgXcQ" in url_short
    assert "t=418s" in url_short

    # Empty URL
    assert RevisionLinkService.create_revision_url("", 100) == ""
    assert RevisionLinkService.create_revision_url("  ", 100) == ""


# =====================================================================
# TEST 8 — Missing Timestamp Not Invented
# =====================================================================
@pytest.mark.asyncio
async def test_missing_timestamp_not_invented():
    """
    Verify the system does NOT invent a timestamp when none exists in the data.
    Returns timestamp_seconds=None.
    """
    course_id = str(ObjectId())

    mock_course = {
        "_id": ObjectId(course_id),
        "course_name": "Algorithms",
        "youtube_url": "https://www.youtube.com/watch?v=xyz12345678",
    }
    # Concept segments exist but target concept has no matching segment
    mock_concept_doc = {
        "course_id": course_id,
        "segments": [
            {"Concept": "Sorting", "ConceptStart": "10:00"},
        ],
    }

    mock_db = MagicMock()
    mock_db.courses.find_one = AsyncMock(return_value=mock_course)
    mock_db.concept_segments.find_one = AsyncMock(return_value=mock_concept_doc)

    with patch("app.services.learning_resource_service.get_database", AsyncMock(return_value=mock_db)):
        result = await LearningResourceService.get_revision_resource(
            course_id=course_id,
            concept_id="CSE101:BinarySearch",
            concept_name="Binary Search",
        )

    assert result is not None
    # Timestamp must be None since "Binary Search" has no matching segment
    assert result.timestamp_seconds is None
    assert result.timestamp_display is None
    # URL should still be returned (base video URL without timestamp)
    assert "xyz12345678" in result.revision_url
    assert "t=" not in result.revision_url


# =====================================================================
# TEST 9 — Missing Video, Answer Still Succeeds
# =====================================================================
@pytest.mark.asyncio
async def test_missing_video_answer_succeeds(active_session):
    """
    Verify the answer submission still succeeds when no video resource exists.
    revision is None, but explanation and correctness are returned.
    """
    session = active_session
    session_id = session["quiz_session_id"]
    student_id = session["student_id"]

    with patch.object(QuizSessionRepository, "get_session", return_value=session), \
         patch.object(QuizSessionRepository, "record_answer_submission", return_value=session), \
         patch.object(ExplanationService, "generate_explanation",
                      return_value=("Stack follows LIFO.", "available")), \
         patch.object(LearningResourceService, "get_revision_resource",
                      return_value=None):  # No video resource available

        res = await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "Stack")

        assert res.is_correct is True
        assert res.learning_support is not None
        assert res.learning_support.explanation is not None
        assert res.learning_support.revision is None  # No video, but that's fine
        assert res.remaining_questions == 1


# =====================================================================
# TEST 10 — Cross-Student Access Prevented
# =====================================================================
@pytest.mark.asyncio
async def test_cross_student_access_prevented(active_session):
    """
    Verify Student A cannot access Student B's explanations, answers, or session.
    """
    session = active_session  # Belongs to S1001
    session_id = session["quiz_session_id"]
    student_b = "S9999"

    async def mock_get_session(sid, uid, cid=None):
        # Only return session for the rightful owner
        if uid.strip().upper() == session["student_id"]:
            return session
        return None

    with patch.object(QuizSessionRepository, "get_session", side_effect=mock_get_session):
        # Student B tries to get question -> rejected
        with pytest.raises(ValueError, match="not found or you do not have permission"):
            await AdaptiveQuizService.get_current_question(session_id, student_b)

        # Student B tries to submit answer -> rejected
        with pytest.raises(ValueError, match="not found or you do not have permission"):
            await AdaptiveQuizService.submit_answer(session_id, student_b, "q1", "Stack")

        # Student B tries to get results -> rejected
        with pytest.raises(ValueError, match="not found or you do not have permission"):
            await AdaptiveQuizService.get_quiz_result(session_id, student_b)


# =====================================================================
# TEST 11 — Question Ownership in Session
# =====================================================================
@pytest.mark.asyncio
async def test_question_ownership_in_session(active_session):
    """
    Verify an explanation/answer cannot be requested for a question
    that doesn't belong to the student's session.
    """
    session = active_session
    session_id = session["quiz_session_id"]
    student_id = session["student_id"]

    with patch.object(QuizSessionRepository, "get_session", return_value=session):
        # Attempt to submit answer for a question NOT in this session
        with pytest.raises(ValueError, match="does not belong to this quiz session"):
            await AdaptiveQuizService.submit_answer(
                session_id, student_id, "foreign_question_xyz", "Some Answer"
            )


# =====================================================================
# TEST 12 — No Answer Leakage Before Submission
# =====================================================================
@pytest.mark.asyncio
async def test_no_answer_leakage_before_submission(active_session):
    """
    Verify the pre-submission question endpoint does NOT expose:
    correct_answer, answer_key, explanation, or learning_support.
    """
    session = active_session
    session_id = session["quiz_session_id"]
    student_id = session["student_id"]

    with patch.object(QuizSessionRepository, "get_session", return_value=session):
        res = await AdaptiveQuizService.get_current_question(session_id, student_id)

        # Dump safe question response to verify no sensitive data
        dumped = res.question.model_dump()
        assert "correct_answer" not in dumped
        assert "answer_key" not in dumped
        assert "explanation" not in dumped
        assert "learning_support" not in dumped

        # Verify the response model itself has no leaky fields
        assert not hasattr(res.question, "correct_answer")
        assert not hasattr(res.question, "explanation")
        assert not hasattr(res.question, "learning_support")
