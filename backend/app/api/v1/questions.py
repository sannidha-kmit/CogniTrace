from typing import Optional, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.question import (
    GenerateQuestionsRequest,
    TeacherQuestionResponse,
    StudentQuestionResponse,
    QuestionSubmissionRequest,
    QuestionSubmissionResponse,
    TeacherQuestionListResponse,
    StudentQuestionListResponse
)
from app.services.question_service import QuestionService, derive_concept_ref

router = APIRouter()


@router.post("/teacher/courses/{course_id}/questions/generate", response_model=TeacherQuestionListResponse, status_code=status.HTTP_201_CREATED)
async def generate_questions_for_concept(
    course_id: str,
    body: GenerateQuestionsRequest,
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Generate MCQs using Claude API from transcript text belonging to the specified concept segment.
    Validates JSON schema, prevents duplicates, and stores questions in MongoDB 'questions' collection.
    Enforces strict teacher ownership of the course.
    """
    if not ObjectId.is_valid(course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )

    if course["teacher_id"] != current_teacher["identifier"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only generate questions for your own courses."
        )

    try:
        questions = await QuestionService.generate_and_store_questions(
            course_id=course_id,
            concept_identifier=body.concept_identifier,
            count=body.count,
            target_difficulty=body.difficulty
        )

        concept_ref = questions[0].concept_ref if questions else None
        concept_name = questions[0].concept_name if questions else None

        return TeacherQuestionListResponse(
            course_id=course_id,
            concept_ref=concept_ref,
            concept_name=concept_name,
            total=len(questions),
            questions=questions
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {str(err)}"
        )


@router.get("/teacher/courses/{course_id}/questions", response_model=TeacherQuestionListResponse)
async def get_teacher_questions(
    course_id: str,
    concept_ref: Optional[str] = Query(None, description="Optional concept reference filter (e.g. course_id:Concept_Name)"),
    concept_id: Optional[str] = Query(None, description="Alias for concept_ref"),
    concept_name: Optional[str] = Query(None, description="Alias for concept_ref"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: EASY, MEDIUM, HARD"),
    count: Optional[int] = Query(None, ge=1, le=50, description="Limit maximum number of returned questions"),
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve Question Bank items for a course (Teacher View).
    Includes correct_answer and explanation fields.
    Enforces strict teacher ownership.
    """
    if not ObjectId.is_valid(course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )

    if course["teacher_id"] != current_teacher["identifier"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view questions for your own courses."
        )

    target_concept = concept_ref or concept_id or concept_name
    questions = await QuestionService.get_questions_for_teacher(
        course_id=course_id,
        concept_ref=target_concept,
        difficulty=difficulty,
        count=count
    )
    return TeacherQuestionListResponse(
        course_id=course_id,
        concept_ref=target_concept,
        concept_name=questions[0].concept_name if questions else None,
        total=len(questions),
        questions=questions
    )


@router.get("/student/courses/{course_id}/questions", response_model=StudentQuestionListResponse)
async def get_student_questions(
    course_id: str,
    concept_ref: Optional[str] = Query(None, description="Optional concept reference filter"),
    concept_id: Optional[str] = Query(None, description="Alias for concept_ref"),
    concept_name: Optional[str] = Query(None, description="Alias for concept_ref"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: EASY, MEDIUM, HARD"),
    count: Optional[int] = Query(None, ge=1, le=50, description="Limit maximum number of returned questions"),
    current_user: dict = Depends(require_role(["student", "teacher"]))
):
    """
    STUDENT SECURITY ENDPOINT:
    Retrieve questions for student practice/quiz.
    SECURITY GUARANTEE: correct_answer and explanation are NEVER returned in this payload.
    """
    if not ObjectId.is_valid(course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )

    target_concept = concept_ref or concept_id or concept_name
    questions = await QuestionService.get_questions_for_student(
        course_id=course_id,
        concept_ref=target_concept,
        difficulty=difficulty,
        count=count
    )
    return StudentQuestionListResponse(
        course_id=course_id,
        concept_ref=target_concept,
        concept_name=questions[0].concept_name if questions else None,
        total=len(questions),
        questions=questions
    )


@router.post("/student/questions/{question_id}/submit", response_model=QuestionSubmissionResponse)
async def submit_student_question_answer(
    question_id: str,
    body: QuestionSubmissionRequest,
    current_user: dict = Depends(require_role(["student", "teacher"]))
):
    """
    Submit answer for a question.
    Evaluates correctness and returns correct_answer and explanation ONLY AFTER submission.
    """
    try:
        return await QuestionService.submit_student_answer(question_id, body.selected_option)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer submission failed: {str(err)}"
        )


@router.post("/student/courses/{course_id}/auto-generate", response_model=StudentQuestionListResponse)
async def auto_generate_questions_from_student_telemetry(
    course_id: str,
    current_student: dict = Depends(require_role(["student", "teacher"]))
):
    """
    ACTUAL STUDENT FLOW ENDPOINT:
    Automatically inspects student's pause telemetry for the course, maps pause count to question count,
    matches pause timestamps to concept segments, triggers Claude generation for paused concepts,
    stores questions, and returns student-safe questions.
    Returns real Claude API errors to the frontend — does NOT hide or replace errors with 404.
    """
    if not ObjectId.is_valid(course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format."
        )

    database = await get_database()
    course = await database.courses.find_one({"_id": ObjectId(course_id)})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )

    student_id = current_student["identifier"]

    try:
        questions = await QuestionService.auto_generate_for_student_telemetry(course_id, student_id)
        return StudentQuestionListResponse(
            course_id=course_id,
            total=len(questions),
            questions=questions
        )
    except ValueError as err:
        # ValueError includes: missing API key, Claude auth errors, rate limits,
        # missing transcript, missing concepts — all real configuration/state errors.
        # Return 400 with the REAL error message so the student UI can display it.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {str(err)}"
        )

