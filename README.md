# PatientTriage.ai

**Clinical Decision Support System for Emergency Department Triage**

> **The AI recommends. The nurse decides.**
> Every AI recommendation is reviewable, overridable, and audit logged.
> The system never autonomously moves a patient in the queue.

---

## Overview

PatientTriage.ai is a full-stack clinical decision support platform for emergency department triage. It combines a **rule-based safety engine** with a **trained ML ensemble** (XGBoost, LightGBM, CatBoost, HistGradientBoosting) to recommend patient priority (P1–P4), surface explainability via SHAP, and flag high-risk conditions in real time over WebSocket.

The system is trained on the **MIMIC-IV-ED dataset** and follows ESI (Emergency Severity Index) acuity levels.

---

## Clinical Safety Principles

These principles are enforced in code, not just documented:

- **Under-triage is worse than over-triage.** When uncertain, the system biases toward flagging higher acuity, never lower.
- **Missing data increases uncertainty**, not confidence — missing vitals/history are never silently treated as "normal." A per-prediction confidence score accounts for data completeness.
- **Age-specific thresholds are mandatory.** Infant, child, adolescent, adult, and geriatric patients use separate physiological baselines throughout the rule engine.
- **The rule engine always runs first.** Deterministic red-flag rules set a priority *floor* that the ML ensemble can never soften. A probabilistic estimate can raise concern; it cannot dismiss a named clinical red flag.
- **Data sufficiency guard.** When ≥ 6 of 7 vital signs are missing and no rule has fired, the ML output is capped at P3 with low confidence — the system cannot responsibly issue a high-acuity recommendation from demographics alone.
- **Every recommendation is audit logged.** The `audit_logs` table captures every input and output, permanently.

---

## Features

### Backend
| Feature | Description |
|---|---|
| **Hybrid Intelligence Layer** | Rule engine → Ensemble ML → Uncertainty → SHAP → Recommendation |
| **ML Ensemble** | XGBoost, LightGBM, CatBoost, HistGradientBoosting stacked with a logistic meta-learner; calibrated with Isotonic Regression |
| **Rule Engine** | 9 deterministic red-flag rules (critical hypoxia, shock, stroke/FAST, airway compromise, seizure, chest pain + diaphoresis, neonate fever, severe resp distress, moderate derangement) |
| **Confidence System** | Three-signal score: calibrated probability + ensemble agreement + data completeness penalty |
| **SHAP Explanations** | Per-prediction top-3 feature importance surfaced in the API response |
| **Sepsis Screening** | qSOFA + SIRS criteria evaluated on every intake |
| **Protocol Triggers** | Rule-based detection of time-critical protocol activations (STEMI, stroke, sepsis, etc.) |
| **Clinical Priority Score (CPS)** | 0–100 composite urgency score for queue sorting |
| **Live Queue** | Real-time patient queue with WebSocket push on every new intake |
| **Waiting Room Monitor** | Background service that escalates patients who deteriorate while waiting |
| **Audit Log** | Every triage recommendation persisted with full input/output |
| **Nurse Override** | Priority overrides recorded and logged separately from AI recommendations |

### Frontend
| Page | Description |
|---|---|
| **Command Center** | Real-time ED dashboard — acuity distribution, bed occupancy, surge toggle |
| **Patient Intake** | Live AI preview as fields are entered (debounced); full triage submission with protocol modal |
| **Live Queue** | Sortable patient queue with CPS, priority badge, sepsis alerts, WebSocket live updates |
| **Explainability** | SHAP feature importance panel per patient |
| **Comparison** | Side-by-side radar chart comparison of two patients |
| **Digital Twin** | Physiological simulation view |
| **Audit Logs** | Full audit trail with actor, event type, resource, and timestamp |

---

## Architecture

```
                                   ┌────────────────────────────┐
                                   │        Clinician / Nurse    │
                                   └──────────────┬──────────────┘
                                                  │ HTTPS / WSS
                                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                 Frontend — React + Vite  (port 5173)              │
│                                                                    │
│  pages/                    components/         services/           │
│  ├─ CommandCenter.jsx      ├─ Layout.jsx        └─ api.js (axios) │
│  ├─ PatientIntake.jsx      ├─ ConfidenceGauge                     │
│  ├─ LiveQueue.jsx          ├─ SepsisAlert                         │
│  ├─ Explainability.jsx     ├─ ProtocolModal                       │
│  ├─ PatientComparison.jsx  ├─ QueueTable                          │
│  ├─ DigitalTwin.jsx        └─ SHAPPanel                           │
│  └─ AuditLogs.jsx                                                  │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ REST /api/v1/*  +  WebSocket /ws
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Backend — FastAPI  (port 8000)                    │
│                                                                    │
│  app/api/routes/                                                   │
│  ├─ triage.py        POST /triage — intake → predict → queue      │
│  ├─ queue.py         GET  /queue  — live patient list              │
│  ├─ override.py      POST /override — nurse priority override      │
│  ├─ audit.py         GET  /audit  — audit log                      │
│  ├─ vitals.py        POST /vitals — vitals stream update           │
│  ├─ model.py         GET  /model  — model metadata & retrain       │
│  └─ health.py        GET  /health                                  │
│                                                                    │
│  ml/                                                               │
│  ├─ predict.py       Public predict() entry point                  │
│  ├─ rule_engine.py   9 deterministic red-flag rules                │
│  ├─ features.py      Feature engineering from patient dict         │
│  ├─ model_utils.py   Ensemble load + feature row builder           │
│  ├─ uncertainty.py   3-signal confidence scoring                   │
│  ├─ explain.py       SHAP explanations                             │
│  ├─ sepsis.py        qSOFA + SIRS screening                        │
│  ├─ protocol_triggers.py  Time-critical protocol detection         │
│  ├─ train.py / train_model.py  Full training pipeline             │
│  └─ preprocess.py    MIMIC-IV-ED feature preprocessing             │
│                                                                    │
│  app/services/                                                     │
│  ├─ patient_registry.py   Create & update triage stays            │
│  ├─ monitor.py            Background waiting room escalation       │
│  └─ cps.py                Clinical Priority Score                  │
│                                                                    │
│  websocket/connection_manager.py  — real-time broadcast            │
│                         │                                          │
│                         ▼                                          │
│           SQLite  backend/data/patient_triage.db                   │
│           (schema managed by Alembic migrations)                   │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                    backend/data/  (MIMIC-IV-ED)
                    edstays.csv.gz   triage.csv.gz
                    vitalsign.csv.gz diagnosis.csv.gz
                    medrecon.csv.gz  pyxis.csv.gz
```

### Directory Layout

```
PatientTriageAI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # triage, queue, override, audit, vitals, model, health
│   │   │   ├── router.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings, reads .env
│   │   │   ├── database.py      # SQLAlchemy engine/session/Base
│   │   │   └── logging_config.py
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # patient_registry, monitor, cps
│   │   ├── simulator/           # ED patient-flow simulator
│   │   └── websocket/           # ConnectionManager
│   ├── ml/                      # Full ML pipeline
│   │   ├── predict.py           # Main prediction interface
│   │   ├── rule_engine.py       # Deterministic red-flag rules
│   │   ├── features.py          # Feature engineering
│   │   ├── model_utils.py       # Ensemble utilities
│   │   ├── uncertainty.py       # Confidence scoring
│   │   ├── explain.py           # SHAP explanations
│   │   ├── sepsis.py            # Sepsis screening
│   │   ├── protocol_triggers.py # Protocol activation detection
│   │   ├── preprocess.py        # MIMIC-IV-ED preprocessing
│   │   ├── train.py             # Training pipeline (Optuna, MLflow)
│   │   └── train_model.py       # Model training utilities
│   ├── alembic/                 # DB migrations
│   ├── tests/                   # pytest suite
│   ├── data/                    # MIMIC-IV-ED CSVs + SQLite DB (gitignored)
│   ├── reports/                 # ML artifacts, MLflow runs (gitignored)
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # ConfidenceGauge, SepsisAlert, ProtocolModal, etc.
│   │   ├── pages/               # All 8 pages
│   │   ├── services/            # api.js (axios client)
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | FastAPI, SQLAlchemy, Alembic, WebSockets, SQLite |
| **ML** | XGBoost, LightGBM, CatBoost, HistGradientBoosting, SHAP, Optuna, MLflow, scikit-learn |
| **Frontend** | React 18, Vite 6, TailwindCSS 3, Recharts, Framer Motion, axios |
| **Deployment** | Docker, Docker Compose |
| **Training Data** | MIMIC-IV-ED (PhysioNet) |

---

## Prerequisites

- Python 3.11
- Node.js ≥ 18.18 and npm  
  *(on Apple Silicon with Homebrew: add `/opt/homebrew/bin` to your PATH)*
- Docker + Docker Compose (optional)
- MIMIC-IV-ED demo files in `backend/data/`:  
  `edstays.csv.gz`, `triage.csv.gz`, `vitalsign.csv.gz`,  
  `diagnosis.csv.gz`, `medrecon.csv.gz`, `pyxis.csv.gz`

---

## Setup — Option A: Run Locally

### 1. Backend

```bash
cd PatientTriageAI/backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Apply database migrations:

```bash
python -m alembic upgrade head
```

*(Optional) Train the ML model on MIMIC-IV-ED data:*

```bash
python -m ml.train
```

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

Run tests:

```bash
pytest -v
```

### 2. Frontend

In a second terminal:

```bash
cd PatientTriageAI/frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173

The Vite dev server proxies `/api` and `/ws` to `http://localhost:8000`
(configured in `vite.config.js`). The backend must be running for live
triage to function.

---

## Setup — Option B: Docker Compose

```bash
cd PatientTriageAI
docker compose up --build
```

- Backend docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

Run migrations inside the container on first start:

```bash
docker compose exec backend python -m alembic upgrade head
```

Stop everything:

```bash
docker compose down
```

---

## ML Pipeline

The prediction pipeline runs end-to-end on every `POST /api/v1/triage` call:

```
Patient input
    │
    ├─▶ Rule Engine (rule_engine.py)
    │       9 deterministic red-flag rules
    │       Sets priority floor — ensemble cannot override
    │
    ├─▶ Feature Engineering (features.py)
    │       Age-banded vitals, shock index, pulse pressure,
    │       MAP, abnormal_vitals_count, vitals_missing_count, ...
    │
    ├─▶ ML Ensemble (model_utils.py)
    │       XGBoost + LightGBM + CatBoost + HistGradientBoosting
    │       → Logistic meta-learner (stacked)
    │       → Isotonic calibration
    │
    ├─▶ Data Sufficiency Guard (predict.py)
    │       ≥6 vitals missing + no rule fired → cap at P3, low confidence
    │
    ├─▶ Confidence Scoring (uncertainty.py)
    │       calibrated_prob × 0.5 + ensemble_agreement × 0.3
    │       + data_completeness × 0.2
    │
    ├─▶ SHAP Explanation (predict.py / explain.py)
    │       Top-3 features driving this prediction
    │
    ├─▶ Sepsis Screen (sepsis.py)  — qSOFA + SIRS
    │
    └─▶ Protocol Triggers (protocol_triggers.py)
            Time-critical activations (STEMI, stroke, sepsis, etc.)
```

Priorities map to ESI acuity:

| Priority | ESI Level | Meaning |
|---|---|---|
| **P1** | 1 | Immediate — life threat |
| **P2** | 2 | Emergent — high risk |
| **P3** | 3 | Urgent |
| **P4** | 4 | Less urgent / non-urgent |

---

## Database Migrations

When adding or modifying a SQLAlchemy model under `backend/app/models/`:

```bash
cd backend
source venv/bin/activate
python -m alembic revision --autogenerate -m "describe the change"
python -m alembic upgrade head
```

---

---

## Changelog

### 2026-08-30

**Bug: Spurious P1 prediction from demographics only** (`ml/predict.py`, `pages/PatientIntake.jsx`)
- **Frontend:** `hasEnoughSignal()` previously triggered a live API call as soon as age was entered. Now requires at least one vital sign, a chief complaint, or a clinical finding (e.g. chest pain checkbox) before hitting the backend.
- **Backend (data-sufficiency guard):** When ≥ 6 of 7 vital signs are missing *and* no rule-engine red flag has fired, the ML output is now capped: priority → P3, risk score → ≤ 35, confidence → ≤ 0.35, with a clear uncertainty message. The ensemble was previously misinterpreting a high `vitals_missing_count` feature as risk and returning P1 with 87/100 risk from demographics alone.

**Bug: Waiting-room monitor crash every cycle** (`app/services/monitor.py`, `app/models/triage_stay.py`)
- `monitor.py` was accessing `stay.priority` — an attribute that never existed on `TriageStay`. The model had `acuity` (MIMIC ground truth) and `predicted_high_acuity` (bool), but no priority string.
- **Fix:** Added `recommended_priority` (str, indexed) and `recommended_confidence` (float) columns to `TriageStay`. `POST /triage` now writes these immediately after prediction. The monitor reads `stay.recommended_priority` and skips pre-loaded MIMIC rows that have never been live-scored.
- Migration: `b6e03f4cb0d0_add_recommended_priority_and_confidence_to_triage_stay`

---

## Known Limitations

- **Authentication is not implemented.** All endpoints are open. Do not deploy to any network without adding auth.
- **SQLite is used for development.** For production, set `DATABASE_URL` in `.env` to a PostgreSQL connection string.
- **The ML model requires MIMIC-IV-ED data to train.** A pre-trained artifact is expected at `backend/ml/` — run `python -m ml.train` to generate it.
- **Age is not persisted on intake stays.** `TriageStay` has no `age` column (the MIMIC-IV-ED extract lacks source age). Age is used for scoring at intake but is not stored; re-scoring a live-intake patient from the queue uses `age=None`.

---

## License

Internal project — license terms to be determined.
