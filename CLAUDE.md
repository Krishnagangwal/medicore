# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MediCore is an AI-powered hospital intelligence platform — a final year BE capstone project (TCET Mumbai). Two engineers with strict ownership boundaries:

- **Krishna** — owns everything in `ai-models/` and `ai-gateway/`. Python only.
- **Khushi** — owns everything in `frontend/` and `backend/`. JS/React only.

Never touch the other engineer's files. Never create files outside your ownership boundary.

## Repository Structure

```
medicore/
├── frontend/          (Khushi — React 18, Vite, Tailwind)
│   └── src/portals/{patient,nurse,doctor,admin}/
├── backend/           (Khushi — Node.js 20, Express 4)
│   └── src/{routes,middleware,models,services,socket,jobs}/
├── ai-gateway/        (Krishna — FastAPI)
│   └── {main.py,orchestrator.py,schemas.py,middleware.py}
├── ai-models/         (Krishna — FastAPI, one dir per model)
│   └── model_{1_triage,2_deterioration,3_lab_parser,4_drug_interaction,5_readmission,6_diff_dx}/
└── docs/              (Both — API contracts, schema, event taxonomy)
```

## Running Services

**Backend (Node.js):**
```bash
cd backend && node src/server.js
# Health check: GET http://localhost:5000/api/health
```

**AI Gateway:**
```bash
cd ai-gateway && uvicorn main:app --reload --port 8000
# Health check: GET http://localhost:8000/health
```

**Individual AI model:**
```bash
cd ai-models/model_1_triage && uvicorn endpoint:app --reload --port 8001
```

**Frontend portals (each runs on its own port):**
```bash
cd frontend && npm run dev
# patient=3000, nurse=3001, doctor=3002, admin=3003
```

**Run a single test (backend):**
```bash
cd backend && npx jest src/tests/auth.test.js
```

## Tech Stack

| Layer | Stack |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Axios, Socket.io-client v4, Recharts |
| Backend | Node.js 20, Express 4, Mongoose 8, Socket.io 4, Bull, node-cron, bcrypt, jsonwebtoken |
| Database | MongoDB Atlas (512MB free) + Cloudinary (file storage) |
| AI layer | Python 3.11, FastAPI, uvicorn, scikit-learn, CatBoost, PyTorch, SHAP, pytesseract, pdf2image |

## Architecture: The Six AI Models

All models are separate FastAPI services. All use CatBoost (not neural networks) unless noted — chosen for SHAP TreeExplainer compatibility. All produce SHAP values in this format:
```json
[{"feature": "heart_rate", "display_name": "Heart Rate", "value": 118, "impact": 0.34, "direction": "increases_risk"}]
```

| # | Model | Input | Output |
|---|---|---|---|
| 1 | Triage Classifier | Symptom text + structured intake | triage category + confidence + SHAP |
| 2 | Deterioration Risk | Time-series vitals for inpatient | risk score (alert if >0.65) + SHAP |
| 3 | Lab Report Parser | PDF/image via OCR | structured values + patient summary + clinical summary |
| 4 | Drug Interaction | Medication list | pairwise severity ratings + graph JSON |
| 5 | Readmission Predictor | Discharge-point patient data | 30-day readmission probability + SHAP |
| 6 | Differential Dx | Symptoms + demographics | ranked diagnoses with confidence |

Model 2 is based on Krishna's ClinSepsis-XAI work (PhysioNet 2019 Challenge, CatBoost, AUROC 0.779). Reuse the feature engineering approach: NEWS2-style features, 3×8-hour temporal windows, shock index (HR/SBP).

## AI Gateway

`POST /gateway/predict` — orchestrates parallel calls to all requested models using `asyncio.gather`. Each model has a 10-second timeout via `asyncio.wait_for`. Returns 200 even on partial timeout; failing models get `status: "timeout"`.

Unified response envelope for every model block:
```json
{"status": "success|error|timeout|skipped", "latency_ms": 342, "result": {}, "error_message": null}
```

Full schema: `docs/gateway-schema.md`

## Backend Conventions

**JWT structure** (shared secret between Node.js and FastAPI — same `JWT_SECRET` in both `.env` files):
```json
{"sub": "userId", "email": "...", "role": "patient|nurse|doctor|specialist|admin", "full_name": "...", "patient_id": null, "iat": ..., "exp": ...}
```
Access token: 24h. Refresh token: 7d in httpOnly cookie.

**All REST errors:**
```json
{"error": "message", "code": "ERROR_CODE", "statusCode": 400}
```

**All dates:** ISO 8601 strings.

**Async JS:** `async/await` only — no callbacks. `try/catch` on every async function.

**React:** functional components only. No class components.

## Socket.io

Three namespaces: `/nurse`, `/doctor`, `/admin`. JWT verified before namespace connection is allowed.

Server-emitted events (client never emits business events):
- `triage:new_patient`, `triage:updated` — nurse queue updates
- `risk:alert` — deterioration score crossed 0.65 threshold
- `lab:ready`, `drug:interaction` — async AI completion
- `ai:patient_loaded` — gateway response ready
- `bed:updated`, `metrics:refresh` — admin dashboard

Full taxonomy: `docs/event-types.md`. Never emit events outside the defined taxonomy.

## MongoDB Design Constraints

512MB hard limit on Atlas free tier.
- TTL index on `predictions`: 90 days
- TTL index on `notifications`: 30 days
- Store only the **latest** AI result per model per encounter — never accumulate history

Core collections: `patients`, `encounters`, `vitals`, `medications`, `labReports`, `predictions`, `triageQueue`, `appointments`, `users`, `notifications`.

## Environment Variables

Never committed. Every variable must appear in `.env.example` with a descriptive comment.

- `backend/.env.example` — `MONGODB_URI`, `JWT_SECRET`, `AI_GATEWAY_URL`, `CLOUDINARY_*`
- `ai-gateway/.env.example` — `JWT_SECRET`, `MODEL_1_URL` through `MODEL_6_URL`

## Deployment (all free tier)

- React portals → Vercel
- Node.js backend → Render (`/api/health` used as health check)
- AI Gateway + models → Hugging Face Spaces (each model is a separate Space)
  - `app.py` at root imports the FastAPI app
  - `packages.txt` for Model 3: `poppler-utils tesseract-ocr`
  - Model weights uploaded to HF Hub (not committed to repo)
- MongoDB → Atlas, files → Cloudinary

## Current Phase

```
Phase: [Update each morning — e.g. "Phase 1 Day 5 | Drug interaction model"]
Done (merged to main): []
In progress: []
Blocked: []
```

## Git Workflow

Feature branches only. Never commit directly to `main`. One feature branch per session, PR to merge.
