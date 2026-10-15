# Evidence-Aware Concept-Level Student Modeling & Closed-Loop Adaptive Assessment

> **Research Investigation Statement**:
> "The proposed framework investigates whether reliability-aware and temporally weighted educational-video interaction evidence, combined with closed-loop adaptive assessment, can improve concept-level learner modeling and learning outcomes."

---

## 1. Problem Definition & Motivation

Modern intelligent learning analytics platforms commonly capture clickstream and video interaction telemetry (pauses, seeks, replays, speed changes). However, traditional learning systems typically rely on **raw count-based heuristics** where:
1. Every pause is treated equally, failing to distinguish between **active study pauses** (high cognitive struggle/comprehension effort) and **extraneous task pauses** (other-work distractions).
2. All past interactions contribute statically without accounting for **temporal forgetting** or memory decay.
3. Telemetry events are mapped to concepts without a **confidence metric** reflecting timestamp boundary alignment.
4. Quizzes are generated statically before assessment begins (**open-loop**), failing to dynamically adapt subsequent questions based on real-time answer performance.

---

## 2. Existing vs. Proposed Architecture

### Existing CogniTrace Architecture (Open-Loop):
```text
Video Playback
      ↓
Student Telemetry Ingestion
      ↓
Concept Boundary Mapping (Binary Containment)
      ↓
Feature Aggregation (6 raw count features)
      ↓
ML Model Inference (Static Priority: HIGH / MEDIUM / LOW)
      ↓
Batch Question Generation / Selection
      ↓
Static Assessment (All questions fixed at start)
```

### Proposed Evidence-Aware Closed-Loop Architecture:
```text
Video Playback
      ↓
Student Telemetry Ingestion
      ↓
Concept Boundary Mapping + Mapping Confidence Score c ∈ [0.0, 1.0]
      ↓
Interaction Reliability Weighting (w_i for study pause, replay, seeks, etc.)
      ↓
Temporal Decay Weighting (exp(-λ · Δt))
      ↓
Concept-Level Evidence Aggregation (Granular audit logging)
      ↓
Student Concept State (Behavioral Evidence + Assessment Mastery + Knowledge Gap)
      ↓
Integrated Research Priority + Dynamic Difficulty Policy
      ↓
Dynamic Question Selection / Dynamic Generation
      ↓
Multi-Dimensional Question Validation Layer (Structural, Semantic, Quality)
      ↓
Student Answer Submission
      ↓
Closed-Loop State Update (Mastery Recalculated, Priority Recalculated)
      ↓
Next Question Adaptively Selected
      ↓
Final Concept-Level Learning Report & Gain Analytics
```

---

## 3. Core Mathematical Formulations

### 3.1 Interaction Reliability Weighting
Not all interaction types represent conceptual difficulty. CogniTrace applies configurable reliability weights:

$$\text{Interaction Type} \xrightarrow{} w_i$$

| Interaction Type | Default Weight $w_i$ | Evidence Interpretation |
|---|---|---|
| `study_pause` | `1.00` | Strongest evidence of cognitive struggle/reflection |
| `replay` | `0.90` | Explicit content re-examination |
| `backward_seek` | `0.80` | Rewinding to revisit previous explanations |
| `speed_decrease` | `0.70` | Slowing down playback for difficult segments |
| `normal_pause` | `0.40` | Baseline video pause |
| `speed_increase` | `0.20` | Fast-forwarding (low difficulty evidence) |
| `other_work_pause` | `0.10` | Extraneous distraction (weak struggle evidence) |
| `forward_seek` | `0.10` | Skipping ahead |

*Note: All weights are fully configurable via `research_settings`.*

### 3.2 Concept Mapping Confidence Score
For an event occurring at video timestamp $t_{event}$ and a concept segment spanning $[C_{start}, C_{end}]$:

$$c(t_{event}) = \text{base\_depth}(t_{event}) + \text{transcript\_bonus}$$

Events positioned centrally inside concept intervals receive higher confidence ($c \approx 0.95 - 0.98$), while events near boundary edges decay smoothly ($c \approx 0.75 - 0.85$).

### 3.3 Temporal Decay
Recent interaction events provide stronger diagnostic evidence than stale interactions:

$$\text{temporal\_weight}(t) = \exp(-\lambda \cdot \Delta t)$$

where:
- $\Delta t$ is the elapsed time in hours since the interaction.
- $\lambda$ is the configurable decay rate (default $\lambda = 0.01$).

### 3.4 Concept Evidence Score
For each concept $k$, total behavioral struggle evidence is the sum of granular contributions:

$$\text{Evidence}(k) = \sum_{j \in \text{Events}(k)} \left( w_j \times c_j \times \exp(-\lambda \cdot \Delta t_j) \right)$$

Normalized behavioral evidence is computed via non-linear saturation:

$$\text{NormEvidence}(k) = 1 - \exp(-0.35 \cdot \text{Evidence}(k)) \in [0.0, 1.0]$$

### 3.5 Interpretable Concept Mastery & Knowledge Gap
For $N$ quiz attempts with $C$ correct answers on concept $k$:

$$\text{Mastery}(k) = \begin{cases} \text{None (Prior = 0.50)}, & \text{if } N = 0 \\ \frac{C}{N}, & \text{if } N > 0 \end{cases}$$

$$\text{KnowledgeGap}(k) = 1.0 - \text{Mastery}(k)$$

Zero attempts are safely handled without falsely penalizing the student with 0% mastery.

### 3.6 Combined Research Priority
The final concept priority is a weighted combination of behavioral evidence, empirical knowledge gap, and base ML inference:

$$\text{Priority}(k) = \alpha \cdot \text{NormEvidence}(k) + \beta \cdot \text{KnowledgeGap}(k) + \gamma \cdot \text{ML\_Score}(k)$$

Default parameters: $\alpha = 0.45$, $\beta = 0.35$, $\gamma = 0.20$.

---

## 4. Closed-Loop Adaptive Assessment Policy

1. **Question Difficulty Mapping**:
   - $\text{Mastery} < 0.40 \implies \text{EASY}$
   - $0.40 \le \text{Mastery} \le 0.75 \implies \text{MEDIUM}$
   - $\text{Mastery} > 0.75 \implies \text{HARD}$

2. **Closed-Loop Adaptation Loop**:
   - Each answer submission immediately triggers:
     1. Correctness evaluation on the backend.
     2. Update of $(N, C)$ in `student_concept_state`.
     3. Recalculation of $\text{Mastery}(k)$, $\text{KnowledgeGap}(k)$, and $\text{Priority}(k)$.
     4. Dynamic adjustment of target difficulty for subsequent questions.

---

## 5. Question Validation Layer

Before entering the question bank or active quiz, every generated question undergoes multi-dimensional validation:
1. **Structural**: Exactly 4 options, exactly 1 matching correct answer, required fields non-empty.
2. **Semantic**: Concept keyword alignment, transcript text grounding overlap, valid correct answer, distinct non-trivial distractors, difficulty alignment.
3. **Quality**: SHA256 duplicate detection, prompt answer leakage prevention, language clarity.

Validation results and rejection reasons are persisted in MongoDB collection `question_validation`.

---

## 6. Experimental Configurations & Ablation Methodology

CogniTrace includes built-in experimental presets to support empirical evaluation in research papers:

| Preset Name | Evidence Weighting | Temporal Decay | Closed-Loop | Question Validation |
|---|---|---|---|---|
| **Experiment A (Baseline)** | ❌ No | ❌ No | ❌ No | ❌ No |
| **Experiment B (Current CogniTrace)** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Experiment C (Proposed Model)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Ablation A** | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Ablation B** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Ablation C** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **Ablation D (Full Framework)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

---

## 7. Research Evaluation Metrics

1. **Student Modeling Accuracy**:
   - Precision, Recall, F1-score evaluating behavioral struggle vs. empirical assessment performance.
2. **Adaptive Assessment Quality**:
   - Concept selection accuracy and difficulty adaptation transition accuracy.
3. **Question Quality**:
   - Transcript grounding rate, concept relevance rate, duplicate rate, validation acceptance rate.
4. **Educational Learning Gain**:
   $$\text{Learning Gain} = \text{Post-Test Score} - \text{Pre-Test Score}$$
