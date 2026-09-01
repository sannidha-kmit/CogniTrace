import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import patch, MagicMock

from app.core.quiz_config import quiz_settings
from app.schemas.quiz import (
    QuizPriorityEnum,
    ConceptPriority,
    InternalQuizQuestion,
    ConceptFeatureData,
    SafeQuizQuestion,
    QuizSessionStatus
)
from app.services.adaptive_quiz_service import AdaptiveQuizService
from app.services.adapters.ml_inference_service import AdaptiveModelService, ModelPrediction
from app.services.adapters.feature_service_adapter import FeatureServiceAdapter
from app.services.adapters.question_bank_adapter import QuestionBankAdapter
from app.services.explanation_service import ExplanationService
from app.services.learning_resource_service import LearningResourceService
from app.repositories.quiz_session_repository import QuizSessionRepository


@pytest.fixture
def mock_ml_service():
    """Returns an instance of AdaptiveModelService."""
    return AdaptiveModelService()


@pytest.fixture
def sample_concept_features():
    return [
        ConceptFeatureData(
            concept_id="c101:Arrays",
            concept_name="Arrays",
            features={
                "replay_count": 5.0,
                "pause_count": 8.0,
                "seek_backward_count": 4.0,
                "seek_forward_count": 1.0,
                "understand_pause_count": 6.0,
                "difficulty_score": 9.5
            }
        ),
        ConceptFeatureData(
            concept_id="c101:LinkedLists",
            concept_name="LinkedLists",
            features={
                "replay_count": 0.0,
                "pause_count": 1.0,
                "seek_backward_count": 0.0,
                "seek_forward_count": 2.0,
                "understand_pause_count": 0.0,
                "difficulty_score": 1.0
            }
        )
    ]


@pytest.fixture
def sample_internal_questions():
    return [
        InternalQuizQuestion(
            question_id="q1",
            concept_id="c101:Arrays",
            concept_name="Arrays",
            question_text="What is time complexity of accessing an array element by index?",
            options=["O(1)", "O(n)", "O(log n)", "O(n^2)"],
            correct_answer="O(1)",
            difficulty="MEDIUM",
            explanation="Array indexing is O(1) constant time."
        ),
        InternalQuizQuestion(
            question_id="q2",
            concept_id="c101:Arrays",
            concept_name="Arrays",
            question_text="How are elements stored in a standard array?",
            options=["Contiguous memory locations", "Linked nodes", "Binary tree", "Hash table"],
            correct_answer="Contiguous memory locations",
            difficulty="EASY",
            explanation="Arrays use contiguous memory."
        ),
        InternalQuizQuestion(
            question_id="q3",
            concept_id="c101:LinkedLists",
            concept_name="LinkedLists",
            question_text="What does each node in a singly linked list contain?",
            options=["Data and next pointer", "Two child pointers", "Array index", "Hash key"],
            correct_answer="Data and next pointer",
            difficulty="MEDIUM",
            explanation="Singly linked list nodes hold data and next node pointer."
        )
    ]


# =====================================================================
# TEST 1 — Start Quiz
# =====================================================================
@pytest.mark.asyncio
async def test_start_quiz(sample_concept_features, sample_internal_questions):
    """
    Verify:
    authenticated student + valid course + features + ML prediction + allocation + question retrieval
    = active quiz session
    """
    student_id = "S1001"
    course_id = str(ObjectId())

    def mock_get_q(course_id, concept_id=None, difficulty=None, count=3, excluded_ids=None):
        return sample_internal_questions[:count]

    with patch.object(FeatureServiceAdapter, "get_concept_features", return_value=sample_concept_features), \
         patch.object(QuestionBankAdapter, "get_questions", side_effect=mock_get_q), \
         patch.object(QuizSessionRepository, "create_session", side_effect=lambda doc: doc):

        res = await AdaptiveQuizService.start_quiz(student_id, course_id, total_questions=3)

        assert res.quiz_session_id is not None
        assert res.student_id == student_id
        assert res.course_id == course_id
        assert res.status == QuizSessionStatus.ACTIVE
        assert res.question_number == 1
        assert res.total_questions == 3
        assert res.current_question.question_id == "q1"
        # No correct answer in safe question response!
        assert not hasattr(res.current_question, "correct_answer")



# =====================================================================
# TEST 2 — Ownership (Student A cannot access Student B's session)
# =====================================================================
@pytest.mark.asyncio
async def test_session_ownership():
    """
    Verify Student A cannot access Student B's session.
    """
    session_id = str(uuid.uuid4())
    student_a = "S1001"
    student_b = "S1002"

    mock_session = {
        "quiz_session_id": session_id,
        "student_id": student_a,
        "course_id": str(ObjectId()),
        "status": "active",
        "questions": []
    }

    async def mock_get_session(sid, uid, cid=None):
        if sid == session_id and uid == student_a:
            return mock_session
        return None

    with patch.object(QuizSessionRepository, "get_session", side_effect=mock_get_session):
        # Student B attempts to access Student A's session
        with pytest.raises(ValueError, match="not found or you do not have permission"):
            await AdaptiveQuizService.get_current_question(session_id, student_b)

        # Student B attempts to submit answer to Student A's session
        with pytest.raises(ValueError, match="not found or you do not have permission"):
            await AdaptiveQuizService.submit_answer(session_id, student_b, "q1", "O(1)")


# =====================================================================
# TEST 3 — Question Retrieval (Correct current question is returned)
# =====================================================================
@pytest.mark.asyncio
async def test_question_retrieval(sample_internal_questions):
    """
    Verify the correct current question is returned.
    """
    session_id = str(uuid.uuid4())
    student_id = "S1001"

    # q1 is already answered, q2 is next
    questions = [q.model_dump() for q in sample_internal_questions]
    questions[0]["answered"] = True
    questions[0]["selected_option"] = "O(1)"
    questions[0]["is_correct"] = True

    mock_session = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "status": "active",
        "answered_questions": 1,
        "questions": questions
    }

    with patch.object(QuizSessionRepository, "get_session", return_value=mock_session):
        res = await AdaptiveQuizService.get_current_question(session_id, student_id)
        assert res.question_number == 2
        assert res.question.question_id == "q2"
        assert res.question.question_text == "How are elements stored in a standard array?"
        assert res.answered_questions == 1


# =====================================================================
# TEST 4 — Answer Validation
# =====================================================================
@pytest.mark.asyncio
async def test_answer_validation(sample_internal_questions):
    """
    Verify:
    correct answer -> correct=True
    wrong answer -> correct=False
    invalid answer -> rejected
    """
    session_id = str(uuid.uuid4())
    student_id = "S1001"
    questions = [q.model_dump() for q in sample_internal_questions]

    mock_session = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "status": "active",
        "answered_questions": 0,
        "correct_count": 0,
        "wrong_count": 0,
        "questions": questions,
        "current_difficulty": "MEDIUM"
    }

    with patch.object(QuizSessionRepository, "get_session", return_value=mock_session), \
         patch.object(QuizSessionRepository, "record_answer_submission", return_value=mock_session), \
         patch.object(ExplanationService, "generate_explanation", return_value=("Test explanation", "available")), \
         patch.object(LearningResourceService, "get_revision_resource", return_value=None):

        # 1. Correct answer
        res_corr = await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "O(1)")
        assert res_corr.is_correct is True
        assert res_corr.correct_answer == "O(1)"

        # 2. Wrong answer
        res_wrong = await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "O(n^2)")
        assert res_wrong.is_correct is False

        # 3. Non-existent question ID
        with pytest.raises(ValueError, match="does not belong to this quiz session"):
            await AdaptiveQuizService.submit_answer(session_id, student_id, "non_existent_q", "O(1)")


# =====================================================================
# TEST 5 — No Answer Leakage
# =====================================================================
@pytest.mark.asyncio
async def test_no_answer_leakage(sample_concept_features, sample_internal_questions):
    """
    Verify API responses before submission do NOT contain correct_answer or explanation.
    """
    student_id = "S1001"
    course_id = str(ObjectId())

    with patch.object(FeatureServiceAdapter, "get_concept_features", return_value=sample_concept_features), \
         patch.object(QuestionBankAdapter, "get_questions", return_value=sample_internal_questions), \
         patch.object(QuizSessionRepository, "create_session", side_effect=lambda doc: doc):

        start_res = await AdaptiveQuizService.start_quiz(student_id, course_id, total_questions=3)
        dumped_start = start_res.current_question.model_dump()
        assert "correct_answer" not in dumped_start
        assert "explanation" not in dumped_start

    # Also test get_current_question
    mock_session = {
        "quiz_session_id": start_res.quiz_session_id,
        "student_id": student_id,
        "status": "active",
        "answered_questions": 0,
        "questions": [q.model_dump() for q in sample_internal_questions]
    }
    with patch.object(QuizSessionRepository, "get_session", return_value=mock_session):
        curr_res = await AdaptiveQuizService.get_current_question(start_res.quiz_session_id, student_id)
        dumped_curr = curr_res.question.model_dump()
        assert "correct_answer" not in dumped_curr
        assert "explanation" not in dumped_curr


# =====================================================================
# TEST 6 — Adaptive Difficulty
# =====================================================================
@pytest.mark.asyncio
async def test_adaptive_difficulty_transitions(sample_internal_questions):
    """
    Verify correct/wrong responses modify later difficulty according to deterministic rules:
    EASY + correct -> MEDIUM
    MEDIUM + correct -> HARD
    HARD + correct -> HARD
    HARD + wrong -> MEDIUM
    MEDIUM + wrong -> EASY
    EASY + wrong -> EASY
    """
    session_id = str(uuid.uuid4())
    student_id = "S1001"

    # Test Correct Transitions
    assert quiz_settings.DIFFICULTY_TRANSITIONS_CORRECT["EASY"] == "MEDIUM"
    assert quiz_settings.DIFFICULTY_TRANSITIONS_CORRECT["MEDIUM"] == "HARD"
    assert quiz_settings.DIFFICULTY_TRANSITIONS_CORRECT["HARD"] == "HARD"

    # Test Wrong Transitions
    assert quiz_settings.DIFFICULTY_TRANSITIONS_WRONG["HARD"] == "MEDIUM"
    assert quiz_settings.DIFFICULTY_TRANSITIONS_WRONG["MEDIUM"] == "EASY"
    assert quiz_settings.DIFFICULTY_TRANSITIONS_WRONG["EASY"] == "EASY"

    # Verify transition in submit_answer
    questions = [q.model_dump() for q in sample_internal_questions]
    questions[0]["difficulty"] = "MEDIUM"

    mock_session = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "status": "active",
        "answered_questions": 0,
        "correct_count": 0,
        "wrong_count": 0,
        "questions": questions,
        "current_difficulty": "MEDIUM"
    }

    recorded_calls = []

    async def mock_record(**kwargs):
        recorded_calls.append(kwargs)
        return mock_session

    with patch.object(QuizSessionRepository, "get_session", return_value=mock_session), \
         patch.object(QuizSessionRepository, "record_answer_submission", side_effect=mock_record), \
         patch.object(ExplanationService, "generate_explanation", return_value=("Test explanation", "available")), \
         patch.object(LearningResourceService, "get_revision_resource", return_value=None):

        # Correct answer on MEDIUM difficulty -> next difficulty is HARD
        await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "O(1)")
        assert recorded_calls[-1]["next_difficulty"] == "HARD"

        # Wrong answer on MEDIUM difficulty -> next difficulty is EASY
        await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "Wrong")
        assert recorded_calls[-1]["next_difficulty"] == "EASY"


# =====================================================================
# TEST 7 — Concept Adaptation
# =====================================================================
def test_concept_priority_and_allocation(mock_ml_service):
    """
    Verify concept allocation follows ML-derived priority.
    High struggle -> HIGH priority -> more questions allocated.
    Low struggle -> LOW priority -> fewer questions allocated.
    """
    high_struggle_features = {
        "replay_count": 10.0,
        "pause_count": 12.0,
        "seek_backward_count": 6.0,
        "seek_forward_count": 0.0,
        "understand_pause_count": 8.0,
        "difficulty_score": 15.0
    }
    low_struggle_features = {
        "replay_count": 0.0,
        "pause_count": 1.0,
        "seek_backward_count": 0.0,
        "seek_forward_count": 3.0,
        "understand_pause_count": 0.0,
        "difficulty_score": 0.0
    }

    pred_high = mock_ml_service.predict(high_struggle_features)
    pred_low = mock_ml_service.predict(low_struggle_features)

    assert pred_high.priority == QuizPriorityEnum.HIGH
    assert pred_low.priority == QuizPriorityEnum.LOW

    priorities = [
        ConceptPriority(concept_id="c1", concept_name="Arrays", priority=pred_high.priority, score=pred_high.score),
        ConceptPriority(concept_id="c2", concept_name="LinkedLists", priority=pred_low.priority, score=pred_low.score)
    ]

    allocated = AdaptiveQuizService.calculate_question_allocation(priorities, total_questions=10)

    # Total must equal 10 exactly
    assert sum(p.allocated_count for p in allocated) == 10
    # High priority concept must have strictly more questions than Low priority concept
    high_alloc = next(p.allocated_count for p in allocated if p.concept_id == "c1")
    low_alloc = next(p.allocated_count for p in allocated if p.concept_id == "c2")
    assert high_alloc > low_alloc


# =====================================================================
# TEST 8 — Completion
# =====================================================================
@pytest.mark.asyncio
async def test_quiz_completion():
    """
    Verify active -> completed, completed_at populated.
    """
    session_id = str(uuid.uuid4())
    student_id = "S1001"
    course_id = str(ObjectId())

    mock_session_active = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "course_id": course_id,
        "status": "active",
        "total_questions": 5,
        "answered_questions": 5,
        "correct_count": 4,
        "wrong_count": 1,
        "completed_at": None
    }

    now = datetime.now(timezone.utc)
    mock_session_completed = {**mock_session_active, "status": "completed", "completed_at": now}

    call_count = 0
    async def mock_get(sid, uid, cid=None):
        nonlocal call_count
        call_count += 1
        return mock_session_active if call_count == 1 else mock_session_completed

    with patch.object(QuizSessionRepository, "get_session", side_effect=mock_get), \
         patch.object(QuizSessionRepository, "finish_session", return_value=mock_session_completed):

        res = await AdaptiveQuizService.finish_quiz(session_id, student_id)
        assert res.status == QuizSessionStatus.COMPLETED
        assert res.completed_at is not None
        assert res.score_percentage == 80.0


# =====================================================================
# TEST 9 — Result Calculation
# =====================================================================
@pytest.mark.asyncio
async def test_quiz_result_breakdown(sample_internal_questions):
    """
    Verify score / result calculation and concept breakdown.
    """
    session_id = str(uuid.uuid4())
    student_id = "S1001"
    course_id = str(ObjectId())

    questions = [q.model_dump() for q in sample_internal_questions]
    questions[0]["answered"] = True
    questions[0]["is_correct"] = True
    questions[1]["answered"] = True
    questions[1]["is_correct"] = False
    questions[2]["answered"] = True
    questions[2]["is_correct"] = True

    mock_session = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "course_id": course_id,
        "status": "completed",
        "total_questions": 3,
        "answered_questions": 3,
        "correct_count": 2,
        "wrong_count": 1,
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
        "concept_priorities": [
            {"concept_id": "c101:Arrays", "concept_name": "Arrays", "priority": "HIGH"},
            {"concept_id": "c101:LinkedLists", "concept_name": "LinkedLists", "priority": "LOW"}
        ],
        "questions": questions
    }

    with patch.object(QuizSessionRepository, "get_session", return_value=mock_session):
        result = await AdaptiveQuizService.get_quiz_result(session_id, student_id)
        assert result.total_questions == 3
        assert result.correct_answers == 2
        assert result.wrong_answers == 1
        assert result.score_percentage == 66.67
        assert len(result.concept_breakdown) == 2

        arrays_stat = next(b for b in result.concept_breakdown if "Arrays" in b.concept_name)
        assert arrays_stat.total_questions == 2
        assert arrays_stat.correct_answers == 1
        assert arrays_stat.accuracy_percentage == 50.0


# =====================================================================
# TEST 10 — Completed Session Protection
# =====================================================================
@pytest.mark.asyncio
async def test_completed_session_protection():
    """
    Verify answers cannot be submitted after completion.
    """
    session_id = str(uuid.uuid4())
    student_id = "S1001"

    mock_session_done = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "status": "completed",
        "questions": [{"question_id": "q1", "answered": True}]
    }

    with patch.object(QuizSessionRepository, "get_session", return_value=mock_session_done):
        with pytest.raises(ValueError, match="already completed"):
            await AdaptiveQuizService.submit_answer(session_id, student_id, "q1", "Option A")

        with pytest.raises(ValueError, match="already been completed"):
            await AdaptiveQuizService.get_current_question(session_id, student_id)


# =====================================================================
# TEST 11 — StudentID + CourseID Filtering
# =====================================================================
@pytest.mark.asyncio
async def test_student_and_course_filtering():
    """
    Verify all session queries filter strictly by student_id and course_id.
    """
    student_id = "S1001"
    other_student = "S9999"
    course_id = str(ObjectId())
    other_course = str(ObjectId())

    # Direct repository check with fake query engine
    recorded_queries = []

    from unittest.mock import AsyncMock
    mock_db = MagicMock()
    mock_db.quiz_sessions.find_one = AsyncMock(return_value=None)

    with patch("app.repositories.quiz_session_repository.get_database", AsyncMock(return_value=mock_db)):
        await QuizSessionRepository.get_session("session123", student_id, course_id)
        mock_db.quiz_sessions.find_one.assert_called_with({
            "quiz_session_id": "session123",
            "student_id": student_id,
            "course_id": course_id
        })



# =====================================================================
# TEST 12 — Question Ownership in Session
# =====================================================================
@pytest.mark.asyncio
async def test_question_session_membership():
    """
    Verify a question from another session or course cannot be submitted.
    """
    session_id = str(uuid.uuid4())
    student_id = "S1001"

    mock_session = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "status": "active",
        "questions": [
            {"question_id": "valid_q1", "answered": False, "correct_answer": "A"}
        ]
    }

    with patch.object(QuizSessionRepository, "get_session", return_value=mock_session):
        with pytest.raises(ValueError, match="does not belong to this quiz session"):
            await AdaptiveQuizService.submit_answer(session_id, student_id, "foreign_question_999", "A")
