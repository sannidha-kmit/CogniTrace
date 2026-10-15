import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import patch, MagicMock, AsyncMock

from app.core.quiz_config import quiz_settings
from app.schemas.quiz import (
    QuizPriorityEnum,
    ConceptPriority,
    InternalQuizQuestion,
    ConceptFeatureData,
    BulkSubmitRequest,
    BulkAnswerItem
)
from app.services.adaptive_quiz_service import AdaptiveQuizService
from app.services.adapters.ml_inference_service import AdaptiveModelService, ModelPrediction
from app.services.adapters.feature_service_adapter import FeatureServiceAdapter
from app.services.adapters.question_bank_adapter import QuestionBankAdapter
from app.services.explanation_service import ExplanationService
from app.repositories.quiz_session_repository import QuizSessionRepository


@pytest.fixture
def mock_ml_service():
    return AdaptiveModelService()


@pytest.fixture
def sample_concept_features():
    return [
        ConceptFeatureData(
            concept_id="c101:ConceptHIGH",
            concept_name="ConceptHIGH",
            features={"difficulty_score": 10.0} # HIGH priority mock
        ),
        ConceptFeatureData(
            concept_id="c101:ConceptMEDIUM",
            concept_name="ConceptMEDIUM",
            features={"difficulty_score": 5.0} # MEDIUM priority mock
        ),
        ConceptFeatureData(
            concept_id="c101:ConceptLOW",
            concept_name="ConceptLOW",
            features={"difficulty_score": 1.0} # LOW priority mock
        )
    ]

def get_mock_prediction(features):
    score = features.get("difficulty_score", 0.0)
    if score >= 10.0:
        return ModelPrediction(priority=QuizPriorityEnum.HIGH, score=0.9, confidence=0.8)
    elif score >= 5.0:
        return ModelPrediction(priority=QuizPriorityEnum.MEDIUM, score=0.5, confidence=0.8)
    else:
        return ModelPrediction(priority=QuizPriorityEnum.LOW, score=0.1, confidence=0.8)

def generate_mock_questions(count, concept_name):
    return [
        InternalQuizQuestion(
            question_id=f"q_{concept_name}_{i}",
            concept_id=f"c101:{concept_name}",
            concept_name=concept_name,
            question_text=f"Question {i} for {concept_name}",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            difficulty="MEDIUM",
            explanation=f"Explanation for {i}"
        ) for i in range(count)
    ]

@pytest.mark.asyncio
async def test_generate_full_adaptive_quiz(sample_concept_features):
    student_id = "S1001"
    course_id = str(ObjectId())
    
    async def mock_get_features(s_id, c_id):
        return sample_concept_features
        
    async def mock_get_questions(course_id, concept_id, difficulty, count, excluded_ids):
        concept_name = concept_id.split(":")[1]
        return generate_mock_questions(count, concept_name)

    with patch.object(FeatureServiceAdapter, "get_concept_features", side_effect=mock_get_features), \
         patch("app.services.adapters.ml_inference_service.ml_service.predict", side_effect=get_mock_prediction), \
         patch.object(QuestionBankAdapter, "get_questions", side_effect=mock_get_questions), \
         patch.object(QuizSessionRepository, "create_session", side_effect=lambda doc: doc):

        res = await AdaptiveQuizService.generate_full_adaptive_quiz(
            student_id=student_id, 
            course_id=course_id, 
            course_name="Test Course"
        )

        assert res.total_questions == 5 + 3 + 2 # HIGH=5, MEDIUM=3, LOW=2
        assert len(res.questions) == 10
        
        # Verify no answers leaked
        dumped_q = res.questions[0].model_dump()
        assert "correct_answer" not in dumped_q
        assert "explanation" not in dumped_q
        
        # Count by concept
        high_count = sum(1 for q in res.questions if q.concept == "ConceptHIGH")
        med_count = sum(1 for q in res.questions if q.concept == "ConceptMEDIUM")
        low_count = sum(1 for q in res.questions if q.concept == "ConceptLOW")
        
        assert high_count == 5
        assert med_count == 3
        assert low_count == 2


@pytest.mark.asyncio
async def test_submit_full_adaptive_quiz():
    session_id = str(uuid.uuid4())
    student_id = "S1001"
    course_id = str(ObjectId())
    
    mock_questions = generate_mock_questions(5, "ConceptHIGH") + generate_mock_questions(3, "ConceptMEDIUM")
    
    mock_session = {
        "quiz_session_id": session_id,
        "student_id": student_id,
        "course_id": course_id,
        "course_name": "Test Course",
        "status": "active",
        "questions": [q.model_dump() for q in mock_questions]
    }
    
    submission = BulkSubmitRequest(
        quiz_session_id=session_id,
        answers=[
            BulkAnswerItem(question_id=mock_questions[0].question_id, selected_answer="A"), # Correct
            BulkAnswerItem(question_id=mock_questions[1].question_id, selected_answer="B"), # Wrong
            BulkAnswerItem(question_id=mock_questions[5].question_id, selected_answer="A")  # Correct for ConceptMEDIUM
        ]
    )
    
    async def mock_get_session(s_id, u_id):
        if s_id == session_id and u_id == student_id:
            return mock_session
        return None
        
    async def mock_explanation(*args, **kwargs):
        return ("AI Explanation", "available")
        
    with patch.object(QuizSessionRepository, "get_session", side_effect=mock_get_session), \
         patch.object(QuizSessionRepository, "update_session", return_value=mock_session), \
         patch.object(ExplanationService, "generate_explanation", side_effect=mock_explanation):
             
        res = await AdaptiveQuizService.submit_full_adaptive_quiz(
            student_id=student_id,
            course_id=course_id,
            submission=submission
        )
        
        assert res.total_questions == 8
        assert res.correct_count == 2
        assert res.wrong_count == 1
        assert res.score_percentage == 25.0 # (2 / 8) * 100
        assert len(res.results) == 3
        
        # Check concept performance
        assert len(res.concept_performance) == 2
        high_perf = next(c for c in res.concept_performance if c.concept == "ConceptHIGH")
        assert high_perf.correct == 1
        assert high_perf.wrong == 1
        assert high_perf.total_questions == 2
        assert high_perf.accuracy_percentage == 50.0
        
        med_perf = next(c for c in res.concept_performance if c.concept == "ConceptMEDIUM")
        assert med_perf.correct == 1
        assert med_perf.wrong == 0
        assert med_perf.total_questions == 1
        assert med_perf.accuracy_percentage == 100.0


@pytest.mark.asyncio
async def test_submit_full_adaptive_quiz_authorization_failure():
    session_id = str(uuid.uuid4())
    student_id = "S1001"
    course_id = str(ObjectId())
    
    mock_session = {
        "quiz_session_id": session_id,
        "student_id": "S9999", # Different student
        "course_id": course_id,
        "status": "active",
        "questions": []
    }
    
    submission = BulkSubmitRequest(quiz_session_id=session_id, answers=[BulkAnswerItem(question_id="q1", selected_answer="A")])
    
    async def mock_get_session(s_id, u_id):
        # The repo returns None if student_id doesn't match
        return None
        
    with patch.object(QuizSessionRepository, "get_session", side_effect=mock_get_session):
        with pytest.raises(ValueError, match="not found or access denied"):
            await AdaptiveQuizService.submit_full_adaptive_quiz(
                student_id=student_id,
                course_id=course_id,
                submission=submission
            )


@pytest.mark.asyncio
async def test_two_courses_same_name_different_ids(sample_concept_features):
    """
    Verify two courses with identical CourseName ("Machine Learning")
    are strictly isolated by unique course_id.
    """
    student_id = "S1001"
    course_id_1 = str(ObjectId())
    course_id_2 = str(ObjectId())
    assert course_id_1 != course_id_2

    captured_course_ids = []

    async def mock_get_features(s_id, c_id):
        captured_course_ids.append(c_id)
        return sample_concept_features

    async def mock_get_questions(course_id, concept_id, difficulty, count, excluded_ids):
        concept_name = concept_id.split(":")[1]
        return generate_mock_questions(count, concept_name)

    with patch.object(FeatureServiceAdapter, "get_concept_features", side_effect=mock_get_features), \
         patch("app.services.adapters.ml_inference_service.ml_service.predict", side_effect=get_mock_prediction), \
         patch.object(QuestionBankAdapter, "get_questions", side_effect=mock_get_questions), \
         patch.object(QuizSessionRepository, "create_session", side_effect=lambda doc: doc):

        res1 = await AdaptiveQuizService.generate_full_adaptive_quiz(student_id, course_id_1, "Machine Learning")
        res2 = await AdaptiveQuizService.generate_full_adaptive_quiz(student_id, course_id_2, "Machine Learning")

        assert res1.course_id == course_id_1
        assert res2.course_id == course_id_2
        assert res1.quiz_session_id != res2.quiz_session_id
        assert captured_course_ids == [course_id_1, course_id_2]


@pytest.mark.asyncio
async def test_no_available_questions_raises_error(sample_concept_features):
    """
    Verify that if the question bank returns 0 questions, a clean ValueError is raised.
    """
    student_id = "S1001"
    course_id = str(ObjectId())

    with patch.object(FeatureServiceAdapter, "get_concept_features", return_value=sample_concept_features), \
         patch("app.services.adapters.ml_inference_service.ml_service.predict", side_effect=get_mock_prediction), \
         patch.object(QuestionBankAdapter, "get_questions", return_value=[]):

        with pytest.raises(ValueError, match="No questions are currently available"):
            await AdaptiveQuizService.generate_full_adaptive_quiz(student_id, course_id, "Test Course")


