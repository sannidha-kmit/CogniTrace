from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class GranularEvidenceRecord(BaseModel):
    """
    Granular interaction evidence record for research reproducibility,
    ablation studies, and statistical analysis.
    """
    student_id: str
    course_id: str
    video_id: Optional[str] = None
    concept_id: str
    concept_name: str
    event_id: str
    interaction_type: str
    interaction_weight: float
    mapping_confidence: float
    timestamp: float  # Video playback timestamp in seconds
    event_time: datetime  # Real-world wall-clock creation timestamp
    delta_t: float  # Elapsed time in hours (or normalized units)
    temporal_weight: float
    evidence_contribution: float  # weight * confidence * temporal
    cumulative_evidence: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConceptEvidenceSummary(BaseModel):
    """
    Aggregated evidence representation for a specific concept.
    """
    student_id: str
    course_id: str
    concept_id: str
    concept_name: str
    total_evidence: float
    normalized_evidence: float
    raw_event_count: int
    interaction_breakdown: Dict[str, float]
    weighted_breakdown: Dict[str, float]
    records: List[GranularEvidenceRecord] = Field(default_factory=list)
