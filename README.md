# MediCore : Deep Learning and Transformer based Sepsis Care Platform

> A 2026 reimagining of Sepsis Watch (Duke University, Sendak et al., FAccT 2020) — the first deep learning system deployed in routine hospital clinical care.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-red)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)](https://fastapi.tiangolo.com)
[![Node.js](https://img.shields.io/badge/Node.js-20-brightgreen)](https://nodejs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What is MediCore?

Sepsis kills 6 million people annually and is the leading cause of inpatient death in hospitals. The problem is not detection, it is that clinical staff detect it too late, or fail to complete the treatment bundle in time.

MediCore is an end to end clinical decision support platform that deploys AI at every critical decision point in sepsis care — from the first warning sign to safe treatment. It is designed for small to mid-size hospitals that cannot afford enterprise systems like Epic or Cerner.

**What makes it different from the original Sepsis Watch:**

| Feature | Sepsis Watch (2018) | MediCore (2026) |
|---|---|---|
| Detection model | MGP-RNN, black box | Time2Vec Transformer, attention explainability |
| Explainability | None (deliberately) | Attention weights over time + SHAP |
| Drug safety | Not included | Antibiotic interaction checking |
| Federated learning | Not included | Flower simulation across 3 hospitals |
| Alert delivery | Nurse checks iPad periodically | Socket.io real-time push |
| SOFA score | Manual (15 min) | Auto-computed from vitals |
| Roles served | Nurse only | Nurse + Doctor + Hospital Admin + Platform (Super) Admin |
| Tenancy | Single hospital | Multi-tenant — hospitals request access, platform admin approves |

---

## Clinical Validation

Inspired by and compared against:
- **Sepsis Watch** — Duke University Health System (2018). 27% reduction in sepsis deaths. Now monitoring 1,000+ patients daily.
- **TREWS** — Bayesian Health. FDA cleared May 2026.
- **ClinSepsis-XAI** (2023) — Published AUROC baseline: 0.779. MediCore achieves **0.7777** on PhysioNet 2019.

> ⚕️ **Clinical disclaimer:** MediCore is a research prototype and academic capstone project. It is not approved for clinical deployment. Every model output includes a clinical disclaimer. AI supports clinical decisions — it does not replace them.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MediCore Platform                         │
├──────────────┬──────────────────────────────────────────────┤
│  Landing +   │  React app → multi-step login (hospital/name  │
│  Auth        │  dropdown for staff, email+password for admins)│
├──────────────┼──────────────────────────────────────────────┤
│  Nurse       │  React Portal → Socket.io real-time alerts   │
│  Station     │  Risk queue · Vitals logging · Treatment list │
├──────────────┼──────────────────────────────────────────────┤
│  Doctor      │  React Portal → Unified AI dashboard          │
│  Portal      │  Attention heatmap · SOFA trend · Drug alerts │
├──────────────┼──────────────────────────────────────────────┤
│  Hospital /  │  Approve/reject hospitals · invite & manage   │
│  Platform    │  staff · multi-tenant hospital management     │
│  Admin       │                                                │
├──────────────┴──────────────────────────────────────────────┤
│              Node.js Backend (Express + node-postgres)       │
│   REST APIs · Socket.io server (/nurse /doctor /admin) ·     │
│   Hourly scoring cron job · Gmail SMTP for invites/approvals │
├─────────────────────────────────────────────────────────────┤
│               FastAPI AI Gateway (port 8000)                 │
│     asyncio.gather parallel dispatch · 10s timeout          │
│     Rule-based alert text · Unified JSON response           │
├──────────────────────┬──────────────────────────────────────┤
│  Time2Vec            │  Drug Interaction                     │
│  Transformer         │  Safety Engine                        │
│  port 8001           │  port 8004                            │
│  Sepsis + SOFA       │  CatBoost + RDKit                     │
│  Attention weights   │  Morgan fingerprints                  │
├──────────────────────┴──────────────────────────────────────┤
│                       PostgreSQL                              │
└─────────────────────────────────────────────────────────────┘
```

**Real time monitoring flow:**
```
Nurse logs vitals → Node.js → AI Gateway → Time2Vec Transformer
→ risk_score > 0.65 → Socket.io fires sepsis:alert → Nurse station
→ Treatment checklist activates → Doctor notified
```

---

## AI Models

### Model 1 : Time2Vec Transformer (Sepsis Early Warning)
A modern deep learning architecture designed for irregular clinical time series.

**Architecture:**
- **Time2Vec layer** — learns both linear (trend) and periodic patterns in vital sign timing
- **Causal Transformer** — 4 layers, 4 attention heads, d_model=128. Causal masking ensures the model only sees past data, never future
- **Dual output heads** — sepsis risk (0-1) + SOFA score, trained jointly with multi-task loss

**What it outputs:**
```json
{
  "risk_score": 0.82,
  "risk_level": "high",
  "alert": true,
  "sofa_score": 7.1,
  "sofa_rounded": 7,
  "trend": "worsening",
  "attention_weights": [0.02, 0.03, "...24 values..."],
  "attention_peak_hour": 22,
  "top_attended_hours": [
    {"hour_index": 22, "attention": 0.31, "vitals": {"hr": 118, "o2sat": 91}}
  ],
  "alert_text": "Critical sepsis risk detected. Primary driver: tachycardia (HR 118). SOFA score 7. Immediate clinical assessment required."
}
```

**Results (PhysioNet 2019 — the default, currently-served model):**
- Validation AUROC: **0.7777**
- Test AUROC: **0.7603**
- Dataset: PhysioNet 2019 Sepsis Challenge (40,000 ICU patients, 1.55M rows)
- Patient-level split: 0 overlap between train/test sets verified
- Parameters: 553,314

**MIMIC-IV retrain (opt-in, `USE_MIMIC_MODEL=true`):**
Retrained on the full credentialed MIMIC-IV v3.1 dataset (364,627 patients, 94,458 adult ICU stays — not the 100-patient public demo) with 15 features (7 vitals + 8 labs) instead of PhysioNet's 7.
- Test AUROC: **0.7955** on 13,073 held-out patients — beats the PhysioNet baseline
- Served off by default for now: the saved checkpoint is from epoch 1 (early-stopped once validation AUROC drifted down over the following 10 epochs), so it's real but under-trained. Set `USE_MIMIC_MODEL=true` to try it; falls back to the PhysioNet model automatically if the MIMIC artifacts aren't present.

**Federated Learning:**
Implemented using [Flower](https://flower.dev) across 3 simulated hospital partitions (40% / 35% / 25% of patients, large academic → community mix). Each hospital trains locally; only model weights are shared, never patient data — addressing the core privacy limitation of the original Sepsis Watch, which required centralizing all patient data at Duke.
Currently **disabled by default** (`USE_FEDERATED_MODEL=true` to opt in) — an earlier evaluation measured a real regression versus the centralized model that hasn't been root-caused yet, so the platform ships the better-understood model until that's resolved.

---

### Model 2 : Drug Interaction Safety Engine

Antibiotic safety checking for sepsis treatment protocols.

**Architecture:** CatBoost multi-class classifier on pharmacological pairwise features derived from RDKit Morgan fingerprints (molecular structure) and the DDIS interaction dataset. NetworkX knowledge graph for drug relationship visualization.

**Severity classes:** None → Minor → Moderate → Major → Contraindicated

**Clinical focus:** Sepsis antibiotic combinations with known toxicity risks (e.g. Fentanyl + Sevoflurane → moderate, monitor for adverse effects).

**Honesty over false negatives:** the reference dataset covers 615 drugs — a pair where either drug falls outside that vocabulary (e.g. Vancomycin, Piperacillin-Tazobactam — both absent from the current training data) is reported as `"unknown"` with a manual-review recommendation, rather than silently scoring it as safe. An earlier version of this pipeline ran the model on those pairs anyway, which reliably (and misleadingly) classified them as "no interaction."

---

### AI Gateway

FastAPI orchestrator that coordinates both models.

- Fires both models **simultaneously** using `asyncio.gather` — confirmed parallel at ~2.6s total vs ~5s sequential
- 10-second independent timeout per model — one slow model never blocks the other
- Always returns a valid response — model failures return `status: "error"`, never a 500
- Generates plain-English alert text from model output (Qwen LLM integration in progress)

---

## Repository Structure

```
medicore/
├── ai-models/
│   ├── model_sepsis/                  # Time2Vec Transformer
│   │   ├── data_loader.py             # PhysioNet preprocessing pipeline
│   │   ├── mimic_data_loader.py       # MIMIC-IV preprocessing pipeline
│   │   ├── model.py                   # Time2Vec + Transformer + dual heads
│   │   ├── train.py                   # PhysioNet training loop
│   │   ├── train_mimic.py             # MIMIC-IV training loop
│   │   ├── inference.py               # Real-time prediction + attention
│   │   ├── endpoint.py / app.py       # FastAPI on port 8001 (app.py = HF Spaces entry point)
│   │   ├── federated/                 # Flower federated learning (implemented, off by default)
│   │   │   ├── fl_partition.py        # 3 hospital partitions
│   │   │   ├── fl_client.py           # Flower NumPy client
│   │   │   ├── fl_server.py           # FedAvg strategy
│   │   │   ├── fl_train.py            # Simulation entry point
│   │   │   └── fl_test.py             # Federated evaluation
│   │   └── artifacts/
│   │       ├── model.pt               # PhysioNet-trained weights (served by default)
│   │       ├── mimic_model.pt         # MIMIC-IV-trained weights (opt-in)
│   │       ├── federated_model.pt     # Federated model weights (opt-in)
│   │       ├── normalisation.json     # PhysioNet preprocessing statistics
│   │       └── mimic_normalisation.json
│   │
│   └── model_4_drug_interaction/      # CatBoost drug safety
│       ├── feature_extraction.py      # RDKit Morgan fingerprints
│       ├── train.py
│       ├── inference.py
│       ├── graph.py                   # NetworkX DDI knowledge graph
│       └── endpoint.py / app.py       # FastAPI on port 8004
│
├── ai-gateway/                        # FastAPI orchestrator (port 8000)
│   ├── main.py / app.py               # app.py = HF Spaces entry point
│   ├── orchestrator.py                # asyncio.gather parallel dispatch
│   ├── schemas.py                     # Pydantic request/response models
│   ├── middleware.py                  # JWT verification (python-jose)
│   ├── alert_generator.py             # Rule-based clinical alert text (Qwen LLM planned)
│   └── test_gateway.py
│
├── backend/                           # Node.js + Express
│   ├── db/
│   │   ├── schema.sql                 # PostgreSQL schema (plain SQL, no ORM)
│   │   └── migrate.js                 # Applies schema.sql
│   ├── src/
│   │   ├── routes/                    # REST API (auth, hospitals, hospitalAdmin, patients,
│   │   │                              #   encounters, vitals, medications, predictions, notifications)
│   │   ├── sockets/                   # Socket.io namespaces (/nurse /doctor /admin)
│   │   ├── jobs/scoringJob.js         # Hourly sepsis scoring cron job
│   │   ├── services/email.service.js  # Gmail SMTP — hospital approval + staff invite emails
│   │   └── lib/                       # db pool, seed script
│   └── package.json
│
├── frontend/
│   └── src/portals/
│       ├── app/                       # Primary unified portal (all roles, all routes below)
│       │   └── src/
│       │       ├── pages/             # Landing, Login (multi-step), Request Access,
│       │       │                      #   Super Admin, Hospital Admin
│       │       ├── nurse/             # Nurse Station (dashboard, patients)
│       │       └── doctor/            # Doctor Portal (AI insights, drug alerts)
│       └── nurse/, doctor/            # Earlier standalone prototypes, superseded by app/
│
└── docs/deployment.md                 # Hugging Face Spaces / Vercel / Render deployment guide
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PyTorch 2.1+ (MPS supported for Apple Silicon)
- PostgreSQL (local install or a hosted instance — anything `DATABASE_URL` can point at)

### Run the full stack locally

```bash
# 1. Database
createdb medicore_backend
cd backend
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET, etc.
npm install
npm run db:migrate
npm run db:seed         # creates a demo hospital + one user per role — see console output for credentials
npm run dev              # http://localhost:5000 (or PORT from .env)

# 2. AI Gateway + models — see "Run the AI models locally" below, then:
cd ai-gateway && cp .env.example .env && pip install -r requirements.txt && uvicorn main:app --port 8000

# 3. Frontend (the unified portal — landing, login, nurse, doctor, admin)
cd frontend/src/portals/app
npm install --legacy-peer-deps   # see Troubleshooting — a real peer-dep conflict, not optional
npm run dev                       # http://localhost:3000
```

### Troubleshooting

- **Backend won't bind to port 5000 (`EADDRINUSE`)** — on macOS, Control Center's AirPlay Receiver squats on port 5000 by default. Either turn it off (System Settings → General → AirDrop & Handoff) or just change `PORT` in `backend/.env` and set `VITE_API_URL`/`VITE_SOCKET_URL` in `frontend/src/portals/app/.env` to match.
- **`npm install` in the frontend fails with an ERESOLVE peer-dependency error** — `package.json` currently pins a `vite` version ahead of what `@vitejs/plugin-react` declares support for. Use `npm install --legacy-peer-deps` rather than editing the lockfile.
- **Gmail App Password option isn't visible** even with 2-Step Verification on — Google withholds it from brand-new accounts for roughly 24 hours as an anti-abuse measure. Use an older Gmail account, wait it out, or point `SMTP_HOST`/`SMTP_PORT` at any other SMTP relay (e.g. Brevo's free tier) instead.
- **A brand-new patient's first vitals entry doesn't produce a risk score** — this is by design, not a bug: the sepsis model needs at least 2 readings to see a trend. The backend silently skips scoring below that (`backend/src/routes/vitals.routes.js`); log a second reading and the score appears.

### Run the AI models locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/medicore.git
cd medicore

# 2. Install Python dependencies
cd ai-models/model_sepsis
pip install -r requirements.txt

# 3. Train the sepsis model (requires PhysioNet 2019 dataset)
# Download from: physionet.org/content/challenge-2019/
python train.py

# 4. Start the sepsis endpoint
uvicorn endpoint:app --port 8001

# 5. In a new terminal — drug interaction endpoint
cd ../model_4_drug_interaction
pip install -r requirements.txt
uvicorn endpoint:app --port 8004

# 6. In a new terminal — AI Gateway
cd ../../ai-gateway
pip install -r requirements.txt
uvicorn main:app --port 8000

# 7. Test the gateway
curl http://localhost:8000/health
```

### Test a live sepsis assessment

```bash
curl -X POST http://localhost:8000/gateway/sepsis-assessment/public \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "demo-001",
    "encounter_id": "enc-001",
    "vitals_readings": [
      {"hr": 85, "o2sat": 97, "temp": 37.2, "sbp": 118, "resp": 16, "iculos": 1},
      {"hr": 92, "o2sat": 96, "temp": 37.5, "sbp": 112, "resp": 17, "iculos": 2},
      {"hr": 98, "o2sat": 95, "temp": 37.9, "sbp": 104, "resp": 19, "iculos": 3},
      {"hr": 106, "o2sat": 93, "temp": 38.3, "sbp": 96, "resp": 22, "iculos": 4},
      {"hr": 112, "o2sat": 92, "temp": 38.6, "sbp": 90, "resp": 24, "iculos": 5},
      {"hr": 118, "o2sat": 91, "temp": 38.9, "sbp": 86, "resp": 26, "iculos": 6}
    ],
    "medications": ["Vancomycin", "Piperacillin-Tazobactam"]
  }'
```

---

## Datasets

| Dataset | Used for | Access |
|---|---|---|
| PhysioNet 2019 Sepsis Challenge | Sepsis model training (default served model) | [Open access](https://physionet.org/content/challenge-2019/) |
| MIMIC-IV v3.1 | Sepsis model retrain — full credentialed dataset (364,627 patients, 94,458 ICU stays), not the 100-patient public demo | [PhysioNet credentialing](https://physionet.org/credential-application/) |
| DDIS | Drug interaction training | Open access |

---

## Deployment

Config for deploying each AI service to Hugging Face Spaces (Docker SDK) — `app.py` entry points, `packages.txt`, and pinned `requirements.txt` are already in `ai-gateway/`, `ai-models/model_sepsis/`, and `ai-models/model_4_drug_interaction/`. Full walkthrough, including the frontend (Vercel) and backend (Render), is in [docs/deployment.md](docs/deployment.md).

---

## Team

| Name | Role | Responsibilities |
|---|---|---|
| **Krishna Gangwal** | AI / ML Engineer | PyTorch models, FastAPI, federated learning, SHAP |
| **Khushi Gupta** | Frontend Engineer | React portals, Socket.io client, UI/UX |
| **Hitansh** | Backend Engineer | Node.js, PostgreSQL, REST APIs, Socket.io server |

**Institution:** Thakur College of Engineering and Technology (TCET), University of Mumbai
**Programme:** B.E. Computer Engineering — Final Year Capstone, 2025–26
**Guided by:** [Guide Name], Department of Computer Engineering

---

## References

1. Sendak et al. — *"The Human Body is a Black Box": Supporting Clinical Decision-Making with Deep Learning.* FAccT 2020. [DOI](https://doi.org/10.1145/3351095.3372827)
2. Futoma et al. — *Learning to Detect Sepsis with a Multitask Gaussian Process RNN Classifier.* ICML 2017. [arXiv](https://arxiv.org/abs/1706.04152)
3. Evaluating Sepsis Watch generalizability — multisite external validation. npj Digital Medicine, June 2025.
4. Kazemi et al. — *Time2Vec: Learning a Vector Representation of Time.* 2019. [arXiv](https://arxiv.org/abs/1907.05321)
5. McMahan et al. — *Communication-Efficient Learning of Deep Networks from Decentralized Data (FedAvg).* AISTATS 2017.
6. PhysioNet Computing in Cardiology Challenge 2019 — Early Prediction of Sepsis from Clinical Data.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

> This project is for academic and research purposes only. Not for clinical use.
