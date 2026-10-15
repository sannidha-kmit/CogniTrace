import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api.v1 import api_router
from app.workers.transcript_worker import run_worker_loop
from app.workers.concept_worker import run_concept_worker_loop

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cognitrace")


_KNOWN_PLACEHOLDERS = {
    "sk-ant-your-real-key-here",
    "your_key_here",
    "REPLACE_ME",
    "your-api-key-here",
}


def _log_claude_config_check() -> None:
    """
    Safe startup check for ANTHROPIC_API_KEY.
    Never prints or logs the actual key value.
    """
    key = settings.ANTHROPIC_API_KEY
    key_exists = key is not None
    key_non_empty = bool(key)
    key_is_placeholder = key in _KNOWN_PLACEHOLDERS if key else False

    logger.info("[CONFIG CHECK] ANTHROPIC_API_KEY variable exists  : %s", "YES" if key_exists else "NO")
    logger.info("[CONFIG CHECK] ANTHROPIC_API_KEY appears non-empty : %s", "YES" if key_non_empty else "NO")
    if key_is_placeholder:
        logger.warning(
            "[CONFIG CHECK] ANTHROPIC_API_KEY is still the placeholder value. "
            "Claude question generation will fail with 401. "
            "Set a real key in: CogniTrace-main/.env"
        )
    elif key_non_empty:
        logger.info("[CONFIG CHECK] ANTHROPIC_API_KEY appears to be a real key (length=%d).", len(key))
    logger.info("[CONFIG CHECK] CLAUDE_MODEL                        : %s", settings.CLAUDE_MODEL)

    workspace_id = settings.ANTHROPIC_WORKSPACE_ID
    if workspace_id:
        logger.info("[CONFIG CHECK] ANTHROPIC_WORKSPACE_ID             : SET (prefix=%s...)", workspace_id[:16])
    else:
        logger.warning(
            "[CONFIG CHECK] ANTHROPIC_WORKSPACE_ID             : NOT SET — "
            "Required for identity-linked API keys. "
            "Add ANTHROPIC_WORKSPACE_ID=wrkspc_... to backend/.env"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle events."""
    logger.info("Starting %s foundation service...", settings.PROJECT_NAME)
    _log_claude_config_check()
    await connect_to_mongo()

    # Start Transcript Worker and Concept Worker in background tasks during FastAPI startup
    logger.info("[TRANSCRIPT WORKER] Starting background processing service...")
    tx_task = asyncio.create_task(run_worker_loop(run_once=False))
    cp_task = asyncio.create_task(run_concept_worker_loop(run_once=False))
    
    app.state.tx_worker_task = tx_task
    app.state.cp_worker_task = cp_task

    yield

    logger.info("Shutting down %s foundation service...", settings.PROJECT_NAME)
    tx_task.cancel()
    cp_task.cancel()
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="CogniTrace Dataset Collection Platform API Foundation",
    version="1.0.0-foundation",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Exception Handlers for graceful error processing
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle API input validation failures gracefully."""
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    raw_errors = exc.errors()
    clean_errors = []
    for err in raw_errors:
        err_copy = dict(err)
        if "ctx" in err_copy and isinstance(err_copy["ctx"], dict):
            err_copy["ctx"] = {k: str(v) for k, v in err_copy["ctx"].items()}
        clean_errors.append(err_copy)

    first_msg = clean_errors[0].get("msg", "Invalid API input provided.") if clean_errors else "Invalid API input provided."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": first_msg,
            "detail": first_msg,
            "details": clean_errors
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unexpected server errors gracefully without leaking raw internal stack traces."""
    logger.error("Unhandled error processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request. Please try again later."
        }
    )


# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Static files for Attention Monitoring & Lecture UI
import pathlib
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_STATIC_DIR = pathlib.Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/lecture")
@app.get("/monitor")
async def lecture_ui():
    """Serve the Real-Time Privacy-Preserving Attention & Video Lecture UI."""
    lecture_file = _STATIC_DIR / "lecture-player.html"
    if lecture_file.exists():
        return FileResponse(str(lecture_file))
    return JSONResponse(
        status_code=404,
        content={"message": "Lecture player interface file not found."}
    )


@app.get("/")
async def root():
    """Root landing endpoint."""
    return {
        "message": "Welcome to CogniTrace Dataset Collection Platform API Foundation",
        "health_check": f"{settings.API_V1_STR}/health",
        "lecture_portal": "/lecture",
        "documentation": "/docs"
    }

