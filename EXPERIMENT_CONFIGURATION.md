# CogniTrace Research Experimentation Guide

This guide describes how to configure, execute, and analyze experiments for research evaluations and ablation studies using the CogniTrace platform.

---

## 1. Experiment Presets

CogniTrace provides built-in experimental presets that can be selected via the API or modified in Python:

### Preset Overview

| Preset | Description | Toggles |
|---|---|---|
| `EXPERIMENT_A` / `BASELINE` | Unweighted, static baseline | `evidence_weighting=False`, `temporal_decay=False`, `closed_loop=False`, `validation=False` |
| `EXPERIMENT_B` / `CURRENT_COGNITRACE` | Count-based ML with static batch allocation | `evidence_weighting=False`, `temporal_decay=False`, `closed_loop=False`, `validation=True` |
| `EXPERIMENT_C` / `PROPOSED_MODEL` | Proposed Evidence-Aware Closed-Loop Framework | `evidence_weighting=True`, `temporal_decay=True`, `closed_loop=True`, `validation=True` |
| `ABLATION_A` | Closed-loop without evidence weighting | `evidence_weighting=False`, `temporal_decay=False`, `closed_loop=True`, `validation=True` |
| `ABLATION_B` | Evidence weighting only | `evidence_weighting=True`, `temporal_decay=False`, `closed_loop=False`, `validation=True` |
| `ABLATION_C` | Evidence weighting + temporal decay | `evidence_weighting=True`, `temporal_decay=True`, `closed_loop=False`, `validation=True` |
| `ABLATION_D` | Full proposed framework | `evidence_weighting=True`, `temporal_decay=True`, `closed_loop=True`, `validation=True` |

---

## 2. Setting Configuration via API

Teachers and researchers can dynamically configure the system without restarting the backend service:

### Set Preset:
```http
POST /api/v1/research/config
Content-Type: application/json
Authorization: Bearer <TEACHER_OR_ADMIN_TOKEN>

{
  "preset": "EXPERIMENT_C"
}
```

### Custom Parameter Tuning:
```http
POST /api/v1/research/config
Content-Type: application/json
Authorization: Bearer <TEACHER_OR_ADMIN_TOKEN>

{
  "evidence_weighting": true,
  "temporal_decay": true,
  "temporal_decay_lambda": 0.015,
  "interaction_weights": {
    "study_pause": 1.0,
    "replay": 0.9,
    "backward_seek": 0.8,
    "normal_pause": 0.4,
    "other_work_pause": 0.1,
    "forward_seek": 0.1,
    "speed_decrease": 0.7,
    "speed_increase": 0.2
  }
}
```

---

## 3. Retrieving Research Evaluation Reports

### Get Full Experiment Report:
```http
GET /api/v1/research/metrics?course_id=6601f4...&experiment_id=exp_01
Authorization: Bearer <TOKEN>
```

Sample Response:
```json
{
  "experiment_id": "exp_01",
  "preset_name": "Proposed Model (Evidence + Temporal + Closed-Loop)",
  "student_modeling": {
    "accuracy": 0.885,
    "precision": 0.862,
    "recall": 0.910,
    "f1_score": 0.885
  },
  "adaptive_assessment": {
    "concept_selection_accuracy": 0.912,
    "priority_prediction_accuracy": 0.875,
    "difficulty_adaptation_accuracy": 0.940
  },
  "question_quality": {
    "grounding_rate": 0.965,
    "concept_relevance_rate": 0.980,
    "duplicate_rate": 0.015,
    "validation_acceptance_rate": 0.945,
    "total_validated": 120
  },
  "learning_metrics": {
    "pre_test_score": 0.44,
    "post_test_score": 0.79,
    "learning_gain": 0.35,
    "concept_level_improvements": {
      "Binary Search": 0.42,
      "Bubble Sort": 0.28
    },
    "retention_score": 0.75
  },
  "total_sessions_analyzed": 45,
  "ablation_comparison": {
    "A_No_Evidence_Weighting": { "student_modeling_f1": 0.68, "learning_gain": 0.18, "adaptive_accuracy": 0.72 },
    "B_Evidence_Weighting_Only": { "student_modeling_f1": 0.76, "learning_gain": 0.24, "adaptive_accuracy": 0.79 },
    "C_Evidence_Plus_Temporal_Decay": { "student_modeling_f1": 0.82, "learning_gain": 0.28, "adaptive_accuracy": 0.84 },
    "D_Proposed_Full_Framework": { "student_modeling_f1": 0.885, "learning_gain": 0.35, "adaptive_accuracy": 0.940 }
  }
}
```

---

## 4. Exporting Granular Evidence for Offline Statistical Analysis

Researchers can export full granular interaction evidence records for reproducibility and offline statistical packages (R, Pandas, SPSS):

```http
GET /api/v1/research/evidence/6601f4...?student_id=ST001
Authorization: Bearer <TEACHER_OR_ADMIN_TOKEN>
```

Each record contains:
- `student_id`, `course_id`, `video_id`, `concept_id`
- `interaction_type`, `interaction_weight`
- `mapping_confidence`
- `timestamp`, `event_time`, `delta_t`, `temporal_weight`
- `evidence_contribution`, `cumulative_evidence`
