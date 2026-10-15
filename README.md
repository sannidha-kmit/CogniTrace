# CogniTrace Intelligent Learning Analytics Platform

A comprehensive educational-video interaction analytics platform featuring **Evidence-Aware Concept-Level Student Modeling** and **Closed-Loop Adaptive Assessment**.

---

## Research Contribution

CogniTrace extends traditional count-based video telemetry with:
1. **Interaction Reliability Weighting**: Distinguishes study pause (1.0), replay (0.9), seek backward (0.8) from distraction pauses (0.1) and forward skips (0.1).
2. **Concept Mapping Confidence**: Calculates geometric and transcript-based confidence score $c \in [0.0, 1.0]$.
3. **Temporal Decay Weighting**: Applies exponential decay $\exp(-\lambda \cdot \Delta t)$ to prioritize recent interactions.
4. **Granular Evidence Auditing**: Persists intermediate audit trails in MongoDB collection `concept_evidence` for scientific reproducibility.
5. **Authoritative Concept-Level Student State**: Tracks $(N, C, \text{Mastery}, \text{KnowledgeGap})$ for each `StudentID + CourseID + ConceptID`.
6. **Closed-Loop Adaptive Assessment**: Dynamically recalculates student concept mastery upon answer submission to adapt next-question difficulty and concept priority.
7. **Multi-Dimensional Question Validation**: Validates generated MCQs across structural, semantic, and quality dimensions before entry into quizzes.
8. **Built-in Experimental & Ablation Presets**: Supports comparative benchmarking across Experiments A, B, C and Ablations A, B, C, D.

---

## Detailed Documentation

- [RESEARCH_CONTRIBUTION.md](RESEARCH_CONTRIBUTION.md) — Mathematical formulations, evidence equations, and methodology.
- [ARCHITECTURE.md](ARCHITECTURE.md) — System topology, component interactions, and data pipeline.
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) — Complete REST endpoint reference and schemas.
- [EXPERIMENT_CONFIGURATION.md](EXPERIMENT_CONFIGURATION.md) — Experimental presets, API configuration, and ablation studies.

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + Custom Design System
- **Routing**: React Router DOM v6
- **Icons**: Lucide React

### Backend
- **Framework**: Python 3.10+ & FastAPI
- **Server**: Uvicorn
- **Validation**: Pydantic & Pydantic Settings
- **Async Driver**: Motor (MongoDB)

### Database
- **Engine**: MongoDB (Document-oriented)

### Authentication & Processing Stack (Prepared for future phases)
- **JWT Authentication**: PyJWT & Passlib (Bcrypt)
- **Video Metadata & Transcripts**: `yt-dlp`, `faster-whisper`, `ffmpeg`
- **Data Analysis**: Pandas

---

## 3. Project Structure

```
cognitrace_dataset_collection/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── health.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── mongodb.py
│   │   ├── __init__.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
├── datasets/
│   └── .gitkeep
├── .env.example
├── .env
├── .gitignore
└── README.md
```

---

## 4. Environment Variables

The project uses `.env` files for configuration. A template is provided in `.env.example`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `HOST` | Backend server listen address | `0.0.0.0` |
| `PORT` | Backend server listen port | `8000` |
| `DEBUG` | FastAPI debug mode flag | `True` |
| `API_V1_STR` | Global API prefix path | `/api/v1` |
| `PROJECT_NAME` | Name of the platform | `CogniTrace Dataset Collection Platform` |
| `SECRET_KEY` | JWT secret signing key | *(Set securely)* |
| `ALGORITHM` | JWT signature algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration duration in minutes | `1440` |
| `MONGODB_URL` | MongoDB connection URI string | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Target database name | `cognitrace_db` |
| `CORS_ORIGINS` | Allowed client HTTP origins | `http://localhost:5173,http://localhost:3000` |

---

## 5. MongoDB Setup

1. Install MongoDB Community Server locally or use MongoDB Atlas.
2. Start MongoDB service locally on default port `27017`:
   ```bash
   mongod --dbpath /path/to/data/db
   ```
3. Update `MONGODB_URL` and `MONGODB_DB_NAME` in `.env` if using custom connection strings or authentication.
4. **Note**: The database begins completely empty. No demo accounts, mock videos, or placeholder collections are created automatically.

---

## 6. Backend Setup

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## 7. Frontend Setup

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install Node.js package dependencies:
   ```bash
   npm install
   ```

---

## 8. Local Run Commands

### Running Backend Server
From the project root:
```bash
uvicorn backend.app.main:app --reload --port 8000
```
Or inside `backend/`:
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive OpenAPI documentation will be accessible at: `http://localhost:8000/docs`

### Running Frontend Development Server
Inside `frontend/`:
```bash
npm run dev
```
Client application will be accessible at: `http://localhost:5173`

---

## 9. Testing Commands

### Frontend Production Build Test
```bash
cd frontend
npm run build
```

### Backend Health Check Test
```bash
curl http://localhost:8000/api/v1/health
```

---

## 10. Currently Implemented Features

- [x] Project workspace structure (`frontend/`, `backend/`, `datasets/`).
- [x] Environment configuration setup (`.env.example`, `.env`).
- [x] FastAPI modular backend framework with Pydantic v2 settings.
- [x] Async Motor MongoDB database connection lifecycle manager.
- [x] Operational API Health Check endpoint (`/api/v1/health`) with live DB ping.
- [x] Vite + React + Tailwind CSS foundation setup with custom design tokens.
- [x] Clean empty database enforcement (no dummy data or synthetic records).

---

## 11. Features Intentionally NOT Implemented Yet

The following modules are explicitly out of scope for the current foundation phase and will be added in subsequent development iterations:
- [ ] User authentication (Registration, Login, JWT issuing/verification)
- [ ] Role enforcement (Student / Teacher access guards)
- [ ] Teacher Course & Video Management
- [ ] Student Course & Video Catalog
- [ ] YouTube IFrame Player with telemetry event tracking (play, pause, seek, playback rate)
- [ ] Faster-Whisper transcript generation & processing pipeline
- [ ] Pause popups & Concept extraction
- [ ] Dataset Export utilities
- [ ] Quiz / Knowledge Tracing / RAG / LLM modules
