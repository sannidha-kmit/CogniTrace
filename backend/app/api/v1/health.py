from fastapi import APIRouter, status
from app.core.config import settings
from app.db.mongodb import check_db_health

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Application Health Check Endpoint.
    Returns backend status, environment configuration metadata, and MongoDB status.
    Does NOT seed or modify any database collections.
    """
    db_status = await check_db_health()
    
    return {
        "status": "online",
        "app_name": settings.PROJECT_NAME,
        "version": "1.0.0-foundation",
        "environment": "development" if settings.DEBUG else "production",
        "database": db_status,
        "features": {
            "authentication": "active",
            "course_management": "active",
            "telemetry_collection": "active",
            "adaptive_quiz": "active"
        }
    }
