import os
import pathlib
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute paths resolved from THIS file's location, so they work
# regardless of the working directory uvicorn is started from.
_THIS_FILE   = pathlib.Path(__file__).resolve()          # backend/app/core/config.py
_BACKEND_DIR = _THIS_FILE.parent.parent.parent            # backend/
_PROJECT_DIR = _BACKEND_DIR.parent                        # CogniTrace-main/

# backend/.env  — local override, highest priority (EDIT THIS for your API key)
_BACKEND_ENV = _BACKEND_DIR / ".env"
# CogniTrace-main/.env — shared project settings, lower priority
_PROJECT_ENV = _PROJECT_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "CogniTrace Dataset Collection Platform"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "dev_secret_key_cognitrace_2026_dataset_collection_platform"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "cognitrace_db"

    # Faster-Whisper Configuration
    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Anthropic Claude API Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    # Required for identity-linked API keys (starts with wrkspc_).
    # Find yours at: https://console.anthropic.com/settings/workspaces
    ANTHROPIC_WORKSPACE_ID: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-latest"

    # Gemini API Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: Optional[str] = None

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        # Absolute paths — work regardless of uvicorn start directory.
        # pydantic-settings 2.x: LAST file in the tuple has highest priority.
        #   _PROJECT_ENV  = CogniTrace-main/.env   (base shared settings)
        #   _BACKEND_ENV  = backend/.env            (local override — HIGHEST PRIORITY)
        #
        # To set your ANTHROPIC_API_KEY / ANTHROPIC_WORKSPACE_ID, edit:
        #   backend/.env  →  ANTHROPIC_API_KEY=sk-ant-api03-...
        #   backend/.env  →  ANTHROPIC_WORKSPACE_ID=wrkspc_...
        env_file=(_PROJECT_ENV, _BACKEND_ENV),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

