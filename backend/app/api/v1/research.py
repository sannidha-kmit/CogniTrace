from typing import List, Dict, Any, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.core.research_config import research_settings, ResearchConfiguration
from app.schemas.student_state import StudentCourseConceptStatesResponse, ConceptStateResponse
from app.schemas.evidence import GranularEvidenceRecord, ConceptEvidenceSummary
from app.schemas.research import ExperimentEvaluationReport
from app.services.student_state_service import StudentConceptStateService
from app.services.evidence_engine import EvidenceEngine
from app.services.research_analytics_service import ResearchAnalyticsService

router = APIRouter()


class ResearchConfigUpdateRequest(BaseModel):
    preset: Optional[str] = None  # "EXPERIMENT_A", "EXPERIMENT_B", "EXPERIMENT_C", "ABLATION_A", etc.
    evidence_weighting: Optional[bool] = None
    temporal_decay: Optional[bool] = None
    closed_loop_adaptation: Optional[bool] = None
    question_validation: Optional[bool] = None
    temporal_decay_lambda: Optional[float] = None
    interaction_weights: Optional[Dict[str, float]] = None


@router.get("/config")
async def get_research_config(
    current_user: dict = Depends(require_role(["student", "teacher", "admin"]))
):
    """
    Retrieve current research experiment configuration and ablation toggles.
    """
    return {
        "evidence_weighting": research_settings.evidence_weighting,
        "temporal_decay": research_settings.temporal_decay,
        "closed_loop_adaptation": research_settings.closed_loop_adaptation,
        "question_validation": research_settings.question_validation,
        "interaction_weights": research_settings.interaction_weights,
        "temporal_decay_lambda": research_settings.temporal_decay_lambda,
        "low_mastery_threshold": research_settings.low_mastery_threshold,
        "high_mastery_threshold": research_settings.high_mastery_threshold,
        "alpha_behavioral": research_settings.alpha_behavioral,
        "beta_knowledge_gap": research_settings.beta_knowledge_gap,
        "gamma_ml_priority": research_settings.gamma_ml_priority
    }


@router.post("/config")
async def update_research_config(
    req: ResearchConfigUpdateRequest,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """
    Update research configuration or apply an experimental preset (Ablation / Baseline).
    """
    if req.preset:
        research_settings.set_experiment_preset(req.preset)

    if req.evidence_weighting is not None:
        research_settings.evidence_weighting = req.evidence_weighting
    if req.temporal_decay is not None:
        research_settings.temporal_decay = req.temporal_decay
    if req.closed_loop_adaptation is not None:
        research_settings.closed_loop_adaptation = req.closed_loop_adaptation
    if req.question_validation is not None:
        research_settings.question_validation = req.question_validation
    if req.temporal_decay_lambda is not None:
        research_settings.temporal_decay_lambda = req.temporal_decay_lambda
    if req.interaction_weights is not None:
        research_settings.interaction_weights = req.interaction_weights

    return {
        "message": "Research configuration updated successfully.",
        "config": research_settings.model_dump()
    }


@router.get("/metrics", response_model=ExperimentEvaluationReport)
async def get_research_metrics(
    course_id: Optional[str] = Query(None, description="Optional course filter"),
    experiment_id: str = Query("exp_01", description="Experiment ID"),
    current_user: dict = Depends(require_role(["student", "teacher", "admin"]))
):
    """
    Retrieve research evaluation metrics: Student Modeling, Adaptive Assessment,
    Question Quality, Learning Gains, and Ablation Comparison.
    """
    return await ResearchAnalyticsService.generate_experiment_report(
        experiment_id=experiment_id,
        course_id=course_id
    )


@router.get("/student/{student_id}/concept-state", response_model=StudentCourseConceptStatesResponse)
async def get_student_concept_state(
    student_id: str,
    course_id: str = Query(..., description="Target course ID"),
    current_user: dict = Depends(require_role(["student", "teacher", "admin"]))
):
    """
    Retrieve concept-level student state for a student and course.
    Enforces authorization check (students can only access their own state).
    """
    clean_student = student_id.strip().upper()
    if current_user.get("role") == "student" and current_user.get("identifier") != clean_student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You cannot view another student's concept state."
        )

    return await StudentConceptStateService.sync_and_get_all_concept_states(
        student_id=clean_student,
        course_id=course_id
    )


@router.get("/student/{student_id}/concept-state/{concept_id}")
async def get_single_student_concept_state(
    student_id: str,
    concept_id: str,
    course_id: str = Query(..., description="Target course ID"),
    current_user: dict = Depends(require_role(["student", "teacher", "admin"]))
):
    """
    Retrieve state for a specific concept.
    """
    clean_student = student_id.strip().upper()
    if current_user.get("role") == "student" and current_user.get("identifier") != clean_student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    all_states = await StudentConceptStateService.sync_and_get_all_concept_states(
        student_id=clean_student,
        course_id=course_id
    )

    for c in all_states.concepts:
        if c.concept_id == concept_id or c.concept_name.lower() == concept_id.lower():
            return c

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Concept state not found."
    )


@router.get("/evidence/{course_id}")
async def get_granular_evidence(
    course_id: str,
    student_id: Optional[str] = Query(None, description="Optional student ID filter"),
    current_user: dict = Depends(require_role(["student", "teacher", "admin"]))
):
    """
    Retrieve granular interaction evidence records for research reproducibility and ablation studies.
    """
    database = await get_database()
    query: Dict[str, Any] = {"course_id": str(course_id)}
    if student_id:
        clean_student = student_id.strip().upper()
        if current_user.get("role") == "student" and current_user.get("identifier") != clean_student:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        query["student_id"] = clean_student
    elif current_user.get("role") == "student":
        query["student_id"] = current_user.get("identifier")

    cursor = database.concept_evidence.find(query).sort("event_time", -1).limit(500)
    records = await cursor.to_list(length=500)

    for r in records:
        r["_id"] = str(r["_id"])

    return {
        "course_id": course_id,
        "count": len(records),
        "records": records
    }
