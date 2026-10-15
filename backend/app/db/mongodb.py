import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.core.config import settings

logger = logging.getLogger(__name__)


class Database:
    client: Optional[AsyncIOMotorClient] = None


db = Database()


async def get_database():
    """Retrieve the database, lazily connecting if the client is None.

    Motor's AsyncIOMotorClient manages its own connection pool and handles
    reconnections internally — no per-request ping needed.
    """
    if db.client is None:
        logger.warning("Database client is None — attempting lazy reconnect...")
        await connect_to_mongo()
    if db.client is None:
        raise RuntimeError(
            "MongoDB is not available. Ensure MongoDB is running and accessible."
        )
    return db.client[settings.MONGODB_DB_NAME]


async def init_db_indexes():
    """Ensure unique constraints and indexes on users, students, teachers, courses, interaction_events, and student_learning collections."""
    if db.client is None:
        return
    database = db.client[settings.MONGODB_DB_NAME]
    try:
        # Create unique index on users.identifier
        await database.users.create_index("identifier", unique=True)
        # Create unique index on students.roll_number
        await database.students.create_index("roll_number", unique=True)
        # Create unique index on teachers.teacher_id
        await database.teachers.create_index("teacher_id", unique=True)
        
        # Create compound unique index on courses (teacher_id, course_name, youtube_url)
        await database.courses.create_index(
            [("teacher_id", 1), ("course_name", 1), ("youtube_url", 1)],
            unique=True
        )
        await database.courses.create_index("teacher_id")
        await database.courses.create_index("year")
        await database.courses.create_index([("created_at", -1)])
        
        # Telemetry indexes
        await database.interaction_events.create_index("StudentID")
        await database.interaction_events.create_index("CourseName")
        await database.interaction_events.create_index([("created_at", -1)])
        
        await database.student_learning.create_index("StudentID")
        await database.student_learning.create_index("CourseName")
        
        # Course Transcripts unique constraint (One Course = One Transcript Document)
        await database.course_transcripts.create_index("course_id", unique=True)
        await database.course_transcripts.create_index("teacher_id")
        
        # Transcription Jobs Queue indexes
        await database.transcription_jobs.create_index("course_id", unique=True)
        await database.transcription_jobs.create_index("status")
        await database.transcription_jobs.create_index([("created_at", -1)])

        # Phase 6 Concept Extraction indexes
        await database.concept_segments.create_index("course_id", unique=True)
        await database.concept_segments.create_index("teacher_id")
        await database.concept_extraction_jobs.create_index("course_id", unique=True)
        await database.concept_extraction_jobs.create_index("status")

        # Question Bank indexes
        await database.questions.create_index("course_id")
        await database.questions.create_index("concept_ref")
        await database.questions.create_index([("course_id", 1), ("concept_ref", 1)])
        await database.questions.create_index([("course_id", 1), ("question_hash", 1)], unique=True)

        # Member 3 Adaptive Quiz Session indexes
        await database.quiz_sessions.create_index("quiz_session_id", unique=True)
        await database.quiz_sessions.create_index([("student_id", 1), ("course_id", 1)])
        await database.quiz_sessions.create_index([("student_id", 1), ("quiz_session_id", 1)])
        await database.quiz_sessions.create_index("status")
        await database.quiz_sessions.create_index([("created_at", -1)])

        # Evidence-Aware Concept Modeling & Research indexes
        await database.concept_evidence.create_index([("student_id", 1), ("course_id", 1)])
        await database.concept_evidence.create_index([("course_id", 1), ("concept_id", 1)])
        await database.concept_evidence.create_index("event_time")
        await database.concept_evidence.create_index([("created_at", -1)])

        await database.student_concept_state.create_index(
            [("student_id", 1), ("course_id", 1), ("concept_id", 1)],
            unique=True
        )
        await database.student_concept_state.create_index([("student_id", 1), ("course_id", 1)])
        await database.student_concept_state.create_index("research_priority_score")

        await database.question_validation.create_index([("course_id", 1), ("concept_id", 1)])
        await database.question_validation.create_index("question_hash")
        await database.question_validation.create_index("status")

        logger.info("Successfully initialized database unique indexes on all collections.")
    except Exception as err:
        logger.error("Failed to initialize database indexes: %s", err)



async def connect_to_mongo():
    """Connect to MongoDB on application startup (or on-demand lazy reconnect).
    
    Always creates a fresh AsyncIOMotorClient, discarding any stale or closed client.
    """
    logger.info("Initializing MongoDB connection to %s...", settings.MONGODB_URL)
    # Discard any old/closed client before creating a fresh one
    db.client = None
    try:
        new_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation="standard"
        )
        # Verify connection status
        await new_client.admin.command('ping')
        db.client = new_client
        logger.info("Successfully connected to MongoDB database '%s'.", settings.MONGODB_DB_NAME)
        # Ensure database indexes
        await init_db_indexes()
    except (ConnectionFailure, ServerSelectionTimeoutError) as err:
        logger.warning(
            "Could not establish initial connection to MongoDB at %s: %s. "
            "Application will run, but database features will fail gracefully until MongoDB is active.",
            settings.MONGODB_URL,
            err
        )
    except Exception as err:
        logger.error("Unexpected error during MongoDB initialization: %s", err)


async def close_mongo_connection():
    """Close MongoDB connection on application shutdown."""
    if db.client is not None:
        logger.info("Closing MongoDB connection...")
        db.client.close()
        db.client = None
        logger.info("MongoDB connection closed.")


async def check_db_health() -> dict:
    """Ping MongoDB server to return status telemetry without modifying DB state."""
    if db.client is None:
        return {
            "status": "disconnected",
            "message": "MongoDB client is not initialized",
            "database_name": settings.MONGODB_DB_NAME
        }
    try:
        # Ping with short timeout
        await db.client.admin.command('ping')
        return {
            "status": "connected",
            "message": "MongoDB server is healthy and responsive",
            "database_name": settings.MONGODB_DB_NAME
        }
    except Exception as err:
        return {
            "status": "unhealthy",
            "message": f"MongoDB server ping failed: {str(err)}",
            "database_name": settings.MONGODB_DB_NAME
        }
