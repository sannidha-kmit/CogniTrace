# CogniTrace Platform API Documentation

This document describes all REST API endpoints provided by the CogniTrace Intelligent Learning Analytics Platform, including the new Research Contribution APIs.

---

## Base URL
`/api/v1`

---

## 1. Research & Concept-Level Student State APIs

### 1.1 Get Research Configuration
- **Method**: `GET /research/config`
- **Access**: `student`, `teacher`, `admin`
- **Response**: JSON object with current experimental toggles, weights, lambda decay, and thresholds.

### 1.2 Update Research Configuration / Preset
- **Method**: `POST /research/config`
- **Access**: `teacher`, `admin`
- **Body**:
  ```json
  {
    "preset": "EXPERIMENT_C",
    "evidence_weighting": true,
    "temporal_decay": true,
    "temporal_decay_lambda": 0.01,
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

### 1.3 Get Research Evaluation Metrics & Ablation Report
- **Method**: `GET /research/metrics?course_id={course_id}&experiment_id={experiment_id}`
- **Access**: `student`, `teacher`, `admin`
- **Response**: Comprehensive student modeling, adaptive assessment, question quality, and learning gain evaluation report.

### 1.4 Get Student Concept States
- **Method**: `GET /research/student/{student_id}/concept-state?course_id={course_id}`
- **Access**: `student` (own state only), `teacher`, `admin`
- **Response**: Full concept state array including behavioral evidence, raw interaction counts, quiz attempts, mastery score, knowledge gap, ML priority, research priority score, and target difficulty.

### 1.5 Get Granular Evidence Records
- **Method**: `GET /research/evidence/{course_id}?student_id={student_id}`
- **Access**: `student` (own records only), `teacher`, `admin`
- **Response**: Granular interaction records containing intermediate `interaction_weight`, `mapping_confidence`, `temporal_weight`, `evidence_contribution`, and `cumulative_evidence`.

---

## 2. Adaptive Quiz APIs

### 2.1 Start Step-by-Step Adaptive Quiz
- **Method**: `POST /quiz/start`
- **Access**: `student`, `teacher`
- **Body**:
  ```json
  {
    "course_id": "6601f4a1...",
    "total_questions": 10
  }
  ```
- **Response**: `StartQuizResponse` with safe first question (excludes `correct_answer` and `explanation`).

### 2.2 Get Current / Next Question
- **Method**: `GET /quiz/{quiz_session_id}/question` or `GET /quiz/{quiz_session_id}/next-question`
- **Access**: `student`, `teacher` (session owner)
- **Response**: Current safe unanswered question.

### 2.3 Submit Answer (Closed-Loop Step)
- **Method**: `POST /quiz/{quiz_session_id}/answer`
- **Access**: `student`, `teacher` (session owner)
- **Body**:
  ```json
  {
    "question_id": "q123",
    "answer": "Option B"
  }
  ```
- **Response**: Correctness, explanation, concept revision video link, updated score, and immediate learning feedback. Atomically updates concept-level student mastery on backend.

### 2.4 Get Quiz Session State
- **Method**: `GET /quiz/{quiz_session_id}/state`
- **Access**: `student`, `teacher`
- **Response**: Current session status, answered questions, score, and synced concept states.

### 2.5 Finish Quiz Session
- **Method**: `POST /quiz/{quiz_session_id}/finish`
- **Access**: `student`, `teacher`

### 2.6 Get Final Quiz Result
- **Method**: `GET /quiz/{quiz_session_id}/result`
- **Access**: `student`, `teacher`
- **Response**: Comprehensive score, concept accuracy breakdown, and revision resources.

---

## 3. Full Adaptive Quiz (Batch & Concept Map)

### 3.1 Get Full Adaptive Quiz with Concept Map
- **Method**: `GET /student/courses/{course_id}/adaptive-quiz`
- **Access**: `student`

### 3.2 Submit Full Adaptive Quiz
- **Method**: `POST /student/courses/{course_id}/adaptive-quiz/submit`
- **Access**: `student`

---

## 4. Telemetry Collection APIs

### 4.1 Record Telemetry Event
- **Method**: `POST /student/events`
- **Access**: `student`
- **Body**:
  ```json
  {
    "course_id": "6601f4a1...",
    "event_type": "PAUSE",
    "event_timestamp": "02:45",
    "event_duration": 12.5,
    "playback_speed": 1.0,
    "pause_reason": "study"
  }
  ```

### 4.2 Start Learning Session
- **Method**: `POST /student/learning/start`

### 4.3 End Learning Session
- **Method**: `POST /student/learning/end`
