import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app
from app.core.security import create_access_token
from app.schemas.quiz import (
    StartQuizResponse,
    CurrentQuestionResponse,
    SubmitAnswerResponse,
    FinishQuizResponse,
    QuizResultResponse,
    SafeQuizQuestion,
    QuizSessionStatus
)
from app.services.adaptive_quiz_service import AdaptiveQuizService


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(), "identifier": "S1001", "role": "student"})
    db.students.find_one = AsyncMock(return_value={"name": "Test Student", "year": "2026"})
    db.courses.find_one = AsyncMock(return_value={"_id": ObjectId(), "year": "2026", "course_name": "DSA"})
    return db


@pytest.mark.asyncio
async def test_api_start_quiz_success(mock_db):
    """Test POST /api/v1/quiz/start with valid course and authorized student."""
    course_id = str(ObjectId())
    mock_db.courses.find_one = AsyncMock(return_value={"_id": ObjectId(course_id), "year": "2026", "course_name": "DSA"})

    safe_q = SafeQuizQuestion(
        quiz_session_id="sess-123",
        question_id="q1",
        concept_id="c1",
        concept_name="Arrays",
        question_text="What is time complexity of O(1)?",
        options=["Constant", "Linear", "Logarithmic", "Quadratic"],
        difficulty="MEDIUM",
        question_number=1,
        total_questions=5
    )
    mock_start_res = StartQuizResponse(
        quiz_session_id="sess-123",
        course_id=course_id,
        student_id="S1001",
        status=QuizSessionStatus.ACTIVE,
        current_question=safe_q,
        question_number=1,
        total_questions=5,
        started_at="2026-08-31T00:00:00Z"
    )

    with patch("app.api.v1.quiz.get_database", AsyncMock(return_value=mock_db)), \
         patch("app.api.deps.get_database", AsyncMock(return_value=mock_db)), \
         patch.object(AdaptiveQuizService, "start_quiz", return_value=mock_start_res):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = create_access_token({"sub": "user123", "identifier": "S1001", "role": "student"})
            resp = await client.post(
                "/api/v1/quiz/start",
                json={"course_id": course_id, "total_questions": 5},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["quiz_session_id"] == "sess-123"
            assert data["current_question"]["question_id"] == "q1"
            assert "correct_answer" not in data["current_question"]


@pytest.mark.asyncio
async def test_api_submit_answer(mock_db):
    """Test POST /api/v1/quiz/{session_id}/answer."""
    mock_submit_res = SubmitAnswerResponse(
        quiz_session_id="sess-123",
        question_id="q1",
        is_correct=True,
        answered_questions=1,
        remaining_questions=4,
        total_questions=5,
        current_score=20.0,
        is_completed=False,
        feedback="Correct!",
        correct_answer="Constant"
    )

    with patch("app.api.deps.get_database", AsyncMock(return_value=mock_db)), \
         patch.object(AdaptiveQuizService, "submit_answer", return_value=mock_submit_res):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = create_access_token({"sub": "user123", "identifier": "S1001", "role": "student"})
            resp = await client.post(
                "/api/v1/quiz/sess-123/answer",
                json={"question_id": "q1", "answer": "Constant"},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_correct"] is True
            assert data["answered_questions"] == 1
            assert data["remaining_questions"] == 4


@pytest.mark.asyncio
async def test_api_get_result(mock_db):
    """Test GET /api/v1/quiz/{session_id}/result."""
    mock_res = QuizResultResponse(
        quiz_session_id="sess-123",
        student_id="S1001",
        course_id=str(ObjectId()),
        status=QuizSessionStatus.COMPLETED,
        total_questions=5,
        answered_questions=5,
        correct_answers=4,
        wrong_answers=1,
        score_percentage=80.0,
        started_at="2026-08-31T00:00:00Z",
        completed_at="2026-08-31T00:10:00Z",
        concept_breakdown=[]
    )

    with patch("app.api.deps.get_database", AsyncMock(return_value=mock_db)), \
         patch.object(AdaptiveQuizService, "get_quiz_result", return_value=mock_res):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = create_access_token({"sub": "user123", "identifier": "S1001", "role": "student"})
            resp = await client.get(
                "/api/v1/quiz/sess-123/result",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["score_percentage"] == 80.0
            assert data["status"] == "completed"
