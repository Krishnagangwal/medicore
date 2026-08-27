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
| Roles served | Nurse only | Nurse + Doctor |

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
│  Nurse       │  React Portal → Socket.io real-time alerts   │
│  Station     │  Risk queue · Vitals logging · Treatment list │
├──────────────┼──────────────────────────────────────────────┤
│  Doctor      │  React Portal → Unified AI dashboard          │
│  Portal      │  Attention heatmap · SOFA trend · Drug alerts │
├──────────────┴──────────────────────────────────────────────┤
│              Node.js Backend (Express + Prisma)              │
│   REST APIs · Socket.io server · Hourly scoring cron job    │
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
│         PostgreSQL (Supabase) · Cloudinary                   │
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

**Results:**
- Validation AUROC: **0.7777**
- Test AUROC: **0.7603**
- Dataset: PhysioNet 2019 Sepsis Challenge (40,000 ICU patients, 1.55M rows)
- Patient-level split: 0 overlap between train/test sets verified
- Parameters: 553,314

**Federated Learning:**
Trained using [Flower](https://flower.dev) across 3 simulated hospital partitions:
- Hospital 0: 40% of patients (large academic)
- Hospital 1: 35% (mid-size)
- Hospital 2: 25% (community)

Each hospital trains locally. Only model weights are shared — no patient data ever leaves the simulated hospital. This addresses the core privacy limitation of the original Sepsis Watch which required centralizing all patient data at Duke.

---

### Model 2 : Drug Interaction Safety Engine

Antibiotic safety checking for sepsis treatment protocols.

**Architecture:** CatBoost multi-class classifier on pharmacological pairwise features derived from RDKit Morgan fingerprints (molecular structure) and the DDIS interaction dataset. NetworkX knowledge graph for drug relationship visualization.

**Severity classes:** None → Minor → Moderate → Major → Contraindicated

**Clinical focus:** Sepsis antibiotic combinations with known toxicity risks (e.g. Vancomycin + Piperacillin-Tazobactam → nephrotoxicity).

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
│   ├── model_sepsis/              # Time2Vec Transformer
│   │   ├── data_loader.py         # PhysioNet preprocessing pipeline
│   │   ├── model.py               # Time2Vec + Transformer + dual heads
│   │   ├── train.py               # Multi-task training loop
│   │   ├── inference.py           # Real-time prediction + attention
│   │   ├── endpoint.py            # FastAPI on port 8001
│   │   ├── federated/             # Flower federated learning
│   │   │   ├── fl_partition.py    # 3 hospital partitions
│   │   │   ├── fl_client.py       # Flower NumPy client
│   │   │   ├── fl_server.py       # FedAvg strategy
│   │   │   ├── fl_train.py        # Simulation entry point
│   │   │   └── fl_test.py         # Federated evaluation
│   │   └── artifacts/
│   │       ├── model.pt           # Centralized model weights
│   │       ├── federated_model.pt # Federated model weights
│   │       └── normalisation.json # Preprocessing statistics
│   │
│   └── model_4_drug_interaction/  # CatBoost drug safety
│       ├── feature_extraction.py  # RDKit Morgan fingerprints
│       ├── train.py
│       ├── inference.py
│       ├── graph.py               # NetworkX DDI knowledge graph
│       └── endpoint.py            # FastAPI on port 8004
│
├── ai-gateway/                    # FastAPI orchestrator (port 8000)
│   ├── main.py
│   ├── orchestrator.py            # asyncio.gather parallel dispatch
│   ├── schemas.py                 # Pydantic request/response models
│   ├── middleware.py              # JWT verification (python-jose)
│   ├── alert_generator.py        # Rule-based clinical alert text
│   └── test_gateway.py
│
├── backend/                       # Node.js + Express (in progress)
│   ├── prisma/schema.prisma       # PostgreSQL schema
│   ├── src/
│   │   ├── routes/                # REST API endpoints
│   │   ├── socket/                # Socket.io namespaces + events
│   │   ├── jobs/                  # Hourly sepsis scoring cron job
│   │   └── services/              # AI Gateway client
│   └── package.json
│
└── frontend/                      # React portals (in progress)
    └── src/portals/
        ├── nurse/                 # Nurse Station
        └── doctor/                # Doctor Portal
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PyTorch 2.1+ (MPS supported for Apple Silicon)

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
| PhysioNet 2019 Sepsis Challenge | Sepsis model training | [Open access](https://physionet.org/content/challenge-2019/) |
| MIMIC-IV | Model retrain (pending credentials) | [PhysioNet credentialing](https://physionet.org/credential-application/) |
| DDIS | Drug interaction training | Open access |

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
