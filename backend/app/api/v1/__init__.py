# API v1 Package Router
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.courses import router as courses_router
from app.api.v1.students import router as students_router
from app.api.v1.student_courses import router as student_courses_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.transcripts import router as transcripts_router
from app.api.v1.teacher_datasets import router as teacher_datasets_router
from app.api.v1.concepts import router as concepts_router
from app.api.v1.dataset_viewer import router as dataset_viewer_router
from app.api.v1.questions import router as questions_router
from app.api.v1.quiz import router as quiz_router

api_router = APIRouter()
print("Initialized api_router")
api_router.include_router(health_router, tags=["Health"])
print("Included health_router")
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(courses_router, prefix="/courses", tags=["Courses"])
api_router.include_router(students_router, prefix="/students", tags=["Students"])
api_router.include_router(student_courses_router, prefix="/student", tags=["Student Access"])
api_router.include_router(telemetry_router, prefix="/student", tags=["Telemetry Collection"])
api_router.include_router(transcripts_router, prefix="/teacher", tags=["Transcript Generation"])
api_router.include_router(teacher_datasets_router, prefix="/teacher", tags=["Teacher Datasets"])
api_router.include_router(concepts_router, prefix="/teacher", tags=["Concept Extraction"])
api_router.include_router(dataset_viewer_router, prefix="/teacher/datasets", tags=["Dataset Viewer"])
api_router.include_router(questions_router, tags=["Question Bank & MCQs"])
api_router.include_router(quiz_router, prefix="/quiz", tags=["Adaptive Quiz Backend"])
print("Finished including all routers in api_router")

