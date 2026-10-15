from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ResearchConfiguration(BaseModel):
    """
    CogniTrace Research & Experimentation Configuration.
    Supports ablation studies, parameter sweeps, and comparative evaluations:
    - Experiment A: Baseline (No evidence weighting, No temporal decay, No closed-loop adaptation)
    - Experiment B: Current CogniTrace (Count-based ML priority + static allocation)
    - Experiment C: Proposed Model (Evidence-aware weighting + Temporal decay + Closed-loop adaptive assessment)
    - Ablations A, B, C, D
    """

    # Feature Toggles for Research Ablation
    evidence_weighting: bool = Field(
        default=True,
        description="Enable reliability-weighted interaction modeling vs raw counts"
    )
    temporal_decay: bool = Field(
        default=True,
        description="Enable exponential temporal decay on interaction events"
    )
    closed_loop_adaptation: bool = Field(
        default=True,
        description="Enable real-time dynamic question selection based on updated mastery state"
    )
    question_validation: bool = Field(
        default=True,
        description="Enable multi-dimensional structural, semantic, and quality validation layer"
    )

    # Interaction Reliability Weights (Configurable baseline, not hard-coded scientific claims)
    interaction_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "study_pause": 1.0,
            "replay": 0.9,
            "backward_seek": 0.8,
            "normal_pause": 0.4,
            "other_work_pause": 0.1,
            "forward_seek": 0.1,
            "speed_decrease": 0.7,
            "speed_increase": 0.2
        }
    )

    # Temporal Decay Parameter (lambda in exp(-lambda * delta_t_hours))
    temporal_decay_lambda: float = Field(
        default=0.01,
        description="Exponential decay factor per hour elapsed since interaction event"
    )

    # Mastery Model Configuration
    default_prior_mastery: float = Field(
        default=0.5,
        description="Neutral prior mastery score for concepts with 0 quiz attempts"
    )
    low_mastery_threshold: float = Field(
        default=0.40,
        description="Mastery threshold below which questions target Easy/Medium difficulty"
    )
    high_mastery_threshold: float = Field(
        default=0.75,
        description="Mastery threshold above which questions target Medium/Hard difficulty"
    )

    # Combined Priority Weights: Priority = alpha * norm_behavioral + beta * knowledge_gap + gamma * ml_priority
    alpha_behavioral: float = Field(
        default=0.45,
        description="Weight assigned to normalized behavioral evidence in combined priority"
    )
    beta_knowledge_gap: float = Field(
        default=0.35,
        description="Weight assigned to knowledge gap (1 - mastery) in combined priority"
    )
    gamma_ml_priority: float = Field(
        default=0.20,
        description="Weight assigned to base ML prediction score in combined priority"
    )

    # Validation Thresholds
    min_validation_score_threshold: float = Field(
        default=0.70,
        description="Minimum validation score required for an LLM generated question to be approved"
    )

    def set_experiment_preset(self, preset_name: str) -> None:
        """
        Configure preset flags for experimental ablation benchmarking.
        """
        p = preset_name.strip().upper()
        if p in ["EXPERIMENT_A", "BASELINE"]:
            self.evidence_weighting = False
            self.temporal_decay = False
            self.closed_loop_adaptation = False
            self.question_validation = False
        elif p in ["EXPERIMENT_B", "CURRENT_COGNITRACE"]:
            self.evidence_weighting = False
            self.temporal_decay = False
            self.closed_loop_adaptation = False
            self.question_validation = True
        elif p in ["EXPERIMENT_C", "PROPOSED_MODEL"]:
            self.evidence_weighting = True
            self.temporal_decay = True
            self.closed_loop_adaptation = True
            self.question_validation = True
        elif p == "ABLATION_A":  # No evidence weighting
            self.evidence_weighting = False
            self.temporal_decay = False
            self.closed_loop_adaptation = True
            self.question_validation = True
        elif p == "ABLATION_B":  # Evidence weighting only
            self.evidence_weighting = True
            self.temporal_decay = False
            self.closed_loop_adaptation = False
            self.question_validation = True
        elif p == "ABLATION_C":  # Evidence weighting + temporal decay
            self.evidence_weighting = True
            self.temporal_decay = True
            self.closed_loop_adaptation = False
            self.question_validation = True
        elif p == "ABLATION_D":  # Full proposed framework
            self.evidence_weighting = True
            self.temporal_decay = True
            self.closed_loop_adaptation = True
            self.question_validation = True
        else:
            raise ValueError(f"Unknown experiment preset: {preset_name}")


research_settings = ResearchConfiguration()
