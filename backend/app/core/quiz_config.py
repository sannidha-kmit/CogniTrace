from typing import Dict, List
from pydantic import BaseModel


class QuizConfiguration(BaseModel):
    DEFAULT_TOTAL_QUESTIONS: int = 10
    MIN_TOTAL_QUESTIONS: int = 3
    MAX_TOTAL_QUESTIONS: int = 30

    # Question allocation weights for priorities
    ALLOCATION_WEIGHTS: Dict[str, float] = {
        "HIGH": 0.5,
        "MEDIUM": 0.3,
        "LOW": 0.2
    }

    # Thresholds for ML priority mapping (score: 0.0 - 1.0)
    PRIORITY_THRESHOLDS: Dict[str, float] = {
        "HIGH": 0.65,
        "MEDIUM": 0.35
    }

    # Strict feature ordering for Member 1 ML inference
    FEATURE_ORDER: List[str] = [
        "replay_count",
        "pause_count",
        "seek_backward_count",
        "seek_forward_count",
        "understand_pause_count",
        "difficulty_score"
    ]

    # Difficulty transitions
    DIFFICULTY_TRANSITIONS_CORRECT: Dict[str, str] = {
        "EASY": "MEDIUM",
        "MEDIUM": "HARD",
        "HARD": "HARD"
    }

    DIFFICULTY_TRANSITIONS_WRONG: Dict[str, str] = {
        "HARD": "MEDIUM",
        "MEDIUM": "EASY",
        "EASY": "EASY"
    }

    # Initial start difficulty
    INITIAL_DIFFICULTY: str = "MEDIUM"


quiz_settings = QuizConfiguration()
