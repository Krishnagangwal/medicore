# MediCore — Claude Code Project Context

> Read this file completely before every session.
> Update "Current phase" each morning.

---

## What this project is

MediCore is an AI-powered sepsis care platform for inpatient hospitals.
Inspired by Sepsis Watch (Duke University, Sendak et al., FAccT 2020) —
the first deep learning system deployed in routine hospital clinical care.
Sepsis Watch reduced sepsis deaths by 27% at Duke. We are building a 
2026 version: explainable, real-time, with federated learning and LLM alerts.

Final year BE capstone. TCET, University of Mumbai. 2025–26.

---

## Team and ownership

Krishna — AI/ML. Owns: ai-models/, ai-gateway/, all Python code.
Khushi  — Frontend. Owns: frontend/ (Nurse Station + Doctor Portal).
Hitansh — Backend. Owns: backend/ (Node.js, PostgreSQL, Socket.io).

Never touch another engineer's directories.

---

## Repository structure
medicore/
├── ai-models/
│ ├── model_sepsis/ ← Time2Vec Transformer (sepsis risk + SOFA)
│ └── model_4_drug_interaction/ ← CatBoost antibiotic safety
├── ai-gateway/ ← FastAPI orchestrator
├── backend/ ← Node.js + Express (Hitansh/Khushi)
├── frontend/
│ └── src/portals/
│ ├── nurse/ ← Nurse Station
│ └── doctor/ ← Doctor Portal
└── docs/


---

## Tech stack

| Layer | Technology |
|---|---|
| Sepsis model | Python 3.11, PyTorch 2.1+, Time2Vec Transformer |
| Federated learning | Flower (flwr) — simulation across 3 data partitions |
| LLM alert | Qwen 3.5 — 2-sentence clinical summary from model output |
| Drug interaction | CatBoost + RDKit Morgan fingerprints |
| Gateway | FastAPI + uvicorn — parallel async dispatch |
| Backend | Node.js 20, Express, Prisma ORM, Socket.io, Bull, node-cron |
| Database | PostgreSQL via Supabase (500MB free) |
| Frontend | React 18, Vite, Tailwind CSS, Recharts, Socket.io-client, Axios |
| Deployment | HF Spaces (AI), Render (backend), Vercel (portals) |

---

## AI Gateway — unified response contract

POST /gateway/sepsis-assessment

Request:
```json
{
  "patient_id": "uuid",
  "encounter_id": "uuid",
  "vitals_readings": [
    {"hr": 118, "o2sat": 91, "temp": 38.5, "sbp": 88,
     "map": 58, "dbp": 45, "resp": 26, "iculos": 22}
  ],
  "medications": ["Vancomycin", "Piperacillin-Tazobactam"]
}
```

Response:
```json
{
  "sepsis": {
    "status": "success",
    "latency_ms": 120,
    "result": {
      "risk_score": 0.82,
      "risk_level": "high",
      "alert": true,
      "sofa_score": 7.1,
      "sofa_rounded": 7,
      "trend": "worsening",
      "attention_weights": [0.02, 0.03, "...24 values..."],
      "attention_peak_hour": 22,
      "top_attended_hours": [
        {"hour_index": 22, "attention": 0.31,
         "vitals": {"hr": 118, "o2sat": 91}}
      ],
      "alert_text": "Worsening sepsis suspected. SOFA increased by 2 in 6h. Primary drivers: elevated heart rate and declining SpO2.",
      "based_on_readings": 24,
      "model": "time2vec-transformer"
    }
  },
  "drug_interaction": {
    "status": "success",
    "latency_ms": 45,
    "result": {
      "total_pairs_checked": 1,
      "interaction_count": 1,
      "interactions": [
        {
          "drug_a": "Vancomycin",
          "drug_b": "Piperacillin-Tazobactam",
          "severity": "major",
          "severity_code": 3,
          "mechanism": "Combined nephrotoxicity risk",
          "recommendation": "Monitor renal function closely",
          "shap_values": []
        }
      ]
    }
  }
}
```

Timeout per model: 10 seconds. Always return partial results.
Status values: "success" | "error" | "timeout"

---

## Sepsis model — output contract

The Time2Vec Transformer at ai-models/model_sepsis/inference.py must
return exactly this shape from predict():

```python
{
  "risk_score": float,        # 0-1
  "risk_level": str,          # "low" <0.4 | "medium" 0.4-0.65 | "high" >0.65
  "alert": bool,              # risk_score > 0.65
  "alert_threshold": 0.65,
  "sofa_score": float,        # 0-24
  "sofa_rounded": int,
  "trend": str,               # "worsening"|"stable"|"improving"|"insufficient_data"
  "attention_weights": list,  # 24 floats summing to 1.0
  "attention_peak_hour": int, # index of highest attention weight
  "top_attended_hours": list, # top 3 hours by attention
  "based_on_readings": int,
  "model": "time2vec-transformer"
}
```

---

## Database — key tables (Prisma, PostgreSQL)

Full schema: backend/prisma/schema.prisma

Key tables for sepsis platform:

users       — id (uuid), email, passwordHash, role (NURSE|DOCTOR|ADMIN),
              fullName, isActive
patients    — id, patientCode, userId, fullName, dob, gender,
              chronicConditions (string[]), allergies (json)
encounters  — id, patientId, status (ACTIVE|DISCHARGED), admittedAt,
              dischargedAt, ward, bedId, treatingDoctorId
vitals      — id, encounterId, patientId, recordedBy, recordedAt,
              heartRate, systolicBp, diastolicBp, temperature,
              respiratoryRate, spo2, weightKg, painScale
              INDEX: (encounterId, recordedAt DESC)
medications — id, encounterId, patientId, prescribedBy, drugName,
              genericName, status (ACTIVE|DISCONTINUED)
predictions — id, encounterId, patientId, modelType, predictedAt,
              result (json), alertTriggered, latencyMs
              TTL: delete after 90 days via nightly cron
notifications — id, recipientId, type, title, body, severity
                (INFO|WARNING|CRITICAL), isRead, createdAt
                TTL: delete after 30 days via nightly cron

All IDs are UUID. All dates are ISO 8601 strings.
No MongoDB anywhere. PostgreSQL only.

---

## JWT structure

```json
{
  "sub": "user-uuid",
  "email": "nurse@medicore.local",
  "role": "NURSE",
  "fullName": "Nurse Priya",
  "patientId": null,
  "iat": 1720000000,
  "exp": 1720086400,
  "iss": "medicore-api"
}
```

Same JWT_SECRET in both backend/.env and ai-gateway/.env.
FastAPI verifies using python-jose without calling Node.js.
Access token: 24h. Refresh: 7d in httpOnly cookie.

---

## Socket.io — sepsis platform events

Namespaces: /nurse  /doctor  /admin

| Event | Namespace | Trigger |
|---|---|---|
| sepsis:alert | /nurse | risk_score > 0.65 OR SOFA increase ≥ 2 |
| sepsis:score_updated | /nurse | Hourly cron completes for a patient |
| drug:interaction | /doctor | Model 4 flags antibiotic interaction |
| vitals:logged | /nurse | Nurse submits vitals form |
| bed:updated | /admin | Patient admitted or discharged |

sepsis:alert payload:
```json
{
  "patient_id": "uuid",
  "encounter_id": "uuid",
  "patient_name": "Mrs. Priya Sharma",
  "risk_score": 0.82,
  "risk_level": "high",
  "sofa_rounded": 7,
  "alert_text": "Worsening sepsis suspected...",
  "attention_peak_hour": 22,
  "ward": "ICU-B",
  "bed_id": "B4"
}
```

---

## Datasets

| Dataset | Path | Used by |
|---|---|---|
| PhysioNet 2019 Sepsis | ~/Downloads/archive-2/Dataset.csv | Sepsis model (training now) |
| MIMIC-IV | Credentials pending | Sepsis model retrain (when approved) |
| DDIS drug interactions | ~/Downloads/ddis.csv | Drug interaction model |
| Drug SMILES | ~/Downloads/drug_smiles.csv | Drug interaction model |

---

## Coding conventions

Python (Krishna):
- PEP8. Type hints on every function signature.
- Docstring on every public function.
- Never raise unhandled exceptions in FastAPI — always return error JSON.
- Load models at module import time, never per request.
- Device detection: MPS → CUDA → CPU (in that order).

JavaScript (Khushi/Hitansh):
- async/await everywhere. No callbacks.
- try/catch on all async functions.
- All REST errors: { error: string, code: string, statusCode: number }
- React: functional components only.
- Prisma client: singleton in backend/src/lib/prisma.js

Git:
- Feature branches only. Never commit to main directly.
- Branch: krishna/session-name or khushi/session-name
- Merge to main after tests pass.
- Never commit .env files.

---

## Environment variables

backend/.env:
PORT=5000
DATABASE_URL=postgresql://...
JWT_SECRET=min-32-chars-same-as-gateway
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
AI_GATEWAY_URL=http://localhost:8000
NODE_ENV=development


ai-gateway/.env:

PORT=8000
JWT_SECRET=min-32-chars-same-as-backend
SEPSIS_MODEL_URL=http://localhost:8001
DRUG_MODEL_URL=http://localhost:8004
MODEL_TIMEOUT_SECONDS=10


---

## Current phase

Phase: Model build — Time2Vec Transformer sepsis model
Date: [update daily]
Merged: Drug interaction model (reframed), CLAUDE.md updated,
old models removed
In progress: Sepsis model training on PhysioNet 2019
Blocked: MIMIC-IV credentials (applied, pending 1-3 days)
Next: Federated learning wrapper, Qwen LLM alert, backend scaffold