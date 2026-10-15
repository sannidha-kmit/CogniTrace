from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.quiz import (
    StartQuizRequest,
    StartQuizResponse,
    CurrentQuestionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    ExplanationResponse,
    FinishQuizResponse,
    QuizResultResponse,
    LearningSupport,
    RevisionResource
)
from app.services.adaptive_quiz_service import AdaptiveQuizService

router = APIRouter()


@router.post("/start", response_model=StartQuizResponse, status_code=status.HTTP_201_CREATED)
async def start_adaptive_quiz(
    body: StartQuizRequest,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    START ADAPTIVE QUIZ ENDPOINT:
    1. Authenticates student and validates Course ID & Year Access.
    2. Retrieves concept features from Member 5 Feature Service.
    3. Runs Member 1 ML Model inference with strict feature ordering to generate Concept Priorities.
    4. Calculates deterministic question allocation across concepts.
    5. Retrieves questions from Member 2 Question Bank.
    6. Initializes persistent MongoDB quiz session.
    7. Returns safe first question (SECURITY: correct_answer is NEVER exposed).
    """
    database = await get_database()
    course_id = body.course_id

    # 1. Validate Course ID format and existence
    if not ObjectId.is_valid(course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    course = await database.courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )

    # 2. Enforce Academic Year Authorization for Students
    if current_student.get("role") == "student":
        student_year = current_student.get("year")
        if course.get("year") != student_year:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not authorized to access courses outside your academic year."
            )

    student_id = current_student["identifier"]

    try:
        response = await AdaptiveQuizService.start_quiz(
            student_id=student_id,
            course_id=course_id,
            total_questions=body.total_questions
        )
        return response
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start adaptive quiz: {str(err)}"
        )


@router.get("/{quiz_session_id}/question", response_model=CurrentQuestionResponse)
@router.get("/{quiz_session_id}/next-question", response_model=CurrentQuestionResponse)
async def get_current_quiz_question(
    quiz_session_id: str,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    CURRENT / NEXT QUESTION ENDPOINT:
    Retrieves the current unanswered question for the student's active session.
    SECURITY GUARANTEE: Never exposes correct_answer or internal scoring before submission.
    Enforces strict session ownership (Student A cannot access Student B's session).
    """
    student_id = current_student["identifier"]
    try:
        return await AdaptiveQuizService.get_current_question(
            quiz_session_id=quiz_session_id,
            student_id=student_id
        )
    except ValueError as err:
        msg = str(err)
        if "not found" in msg.lower() or "permission" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve current question: {str(err)}"
        )


@router.get("/{quiz_session_id}/state")
async def get_quiz_session_state(
    quiz_session_id: str,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    QUIZ SESSION STATE ENDPOINT:
    Returns the secure backend-maintained session state (progress, score, concept mastery).
    """
    from app.repositories.quiz_session_repository import QuizSessionRepository
    from app.services.student_state_service import StudentConceptStateService

    clean_student = current_student["identifier"].strip().upper()
    session = await QuizSessionRepository.get_session(quiz_session_id, clean_student)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz session not found or unauthorized.")

    course_id = session.get("course_id", "")
    concept_states = await StudentConceptStateService.sync_and_get_all_concept_states(
        student_id=clean_student,
        course_id=course_id
    )

    return {
        "quiz_session_id": quiz_session_id,
        "student_id": clean_student,
        "course_id": course_id,
        "status": session.get("status", "active"),
        "answered_questions": session.get("answered_questions", 0),
        "total_questions": session.get("total_questions", 0),
        "current_score": session.get("score", 0.0),
        "concept_states": concept_states.model_dump()
    }


@router.post("/{quiz_session_id}/answer", response_model=SubmitAnswerResponse)
async def submit_quiz_answer(
    quiz_session_id: str,
    body: SubmitAnswerRequest,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    SUBMIT ANSWER ENDPOINT:
    1. Authenticates student and verifies session ownership.
    2. Validates that the session is active and question belongs to this session.
    3. Evaluates answer correctness securely on the backend.
    4. Applies deterministic difficulty adaptation for subsequent questions.
    5. Returns safe feedback (correct_answer revealed only after submission).
    """
    student_id = current_student["identifier"]
    try:
        return await AdaptiveQuizService.submit_answer(
            quiz_session_id=quiz_session_id,
            student_id=student_id,
            question_id=body.question_id,
            selected_answer=body.answer
        )
    except ValueError as err:
        msg = str(err)
        if "not found" in msg.lower() or "permission" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer submission failed: {str(err)}"
        )


@router.get("/{quiz_session_id}/question/{question_id}/explanation", response_model=ExplanationResponse)
async def get_question_explanation(
    quiz_session_id: str,
    question_id: str,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    EXPLANATION RE-FETCH ENDPOINT:
    Retrieves the persisted learning support (AI explanation + revision link) for an
    already-answered question. Enforces session ownership and only returns data
    for questions that have been submitted — never leaks correct_answer before submission.
    """
    student_id = current_student["identifier"]
    try:
        from app.repositories.quiz_session_repository import QuizSessionRepository

        clean_student = student_id.strip().upper()
        session = await QuizSessionRepository.get_session(quiz_session_id, clean_student)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz session not found or you do not have permission to access it."
            )

        # Locate the question in the session
        target_q = None
        for q in session.get("questions", []):
            if q.get("question_id") == question_id:
                target_q = q
                break

        if not target_q:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The specified question does not belong to this quiz session."
            )

        # Only return explanation for already-answered questions (prevent answer leakage)
        if not target_q.get("answered", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explanation is only available after the question has been answered."
            )

        # Reconstruct LearningSupport from persisted data
        ls_data = target_q.get("learning_support")
        learning_support = None
        if ls_data and isinstance(ls_data, dict):
            learning_support = LearningSupport(**ls_data)

        return ExplanationResponse(
            quiz_session_id=quiz_session_id,
            question_id=question_id,
            is_correct=target_q.get("is_correct", False),
            learning_support=learning_support
        )

    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve explanation: {str(err)}"
        )


@router.post("/{quiz_session_id}/finish", response_model=FinishQuizResponse)
async def finish_quiz_session(
    quiz_session_id: str,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    FINISH QUIZ ENDPOINT:
    Finalizes the quiz session, prevents further answer submissions, and records completion time.
    """
    student_id = current_student["identifier"]
    try:
        return await AdaptiveQuizService.finish_quiz(
            quiz_session_id=quiz_session_id,
            student_id=student_id
        )
    except ValueError as err:
        msg = str(err)
        if "not found" in msg.lower() or "permission" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finish quiz session: {str(err)}"
        )


@router.get("/{quiz_session_id}/result", response_model=QuizResultResponse)
async def get_quiz_result(
    quiz_session_id: str,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    QUIZ RESULT ENDPOINT:
    Returns final score and concept-wise accuracy breakdown for the authorized student.
    """
    student_id = current_student["identifier"]
    try:
        return await AdaptiveQuizService.get_quiz_result(
            quiz_session_id=quiz_session_id,
            student_id=student_id
        )
    except ValueError as err:
        msg = str(err)
        if "not found" in msg.lower() or "permission" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quiz results: {str(err)}"
        )
