"""Generate 50,000 synthetic triage training samples.

Pipeline:
  1. Derive vital-sign distributions (PhysioNet 2019 used as reference; fallback
     to hardcoded population norms if the raw CSVs are not present).
  2. Sample N synthetic patients.
  3. Compute NEWS2 score to assign triage label.
  4. Add extra features: diastolic_bp, pain_scale, age, chief_complaint_code,
     shock_index (HR / SBP).
  5. Save to data/triage_synthetic.csv

Output columns:
    heart_rate, systolic_bp, diastolic_bp, temperature, respiratory_rate,
    spo2, pain_scale, age, chief_complaint_code, shock_index, triage_label
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

PHYSIONET_DIR = Path.home() / "Downloads" / "22687585"
OUT_DIR = Path(__file__).parent / "data"
OUT_FILE = OUT_DIR / "triage_synthetic.csv"

CATEGORY_ORDER = ["NON_URGENT", "SEMI_URGENT", "URGENT", "CRITICAL"]

CHIEF_COMPLAINTS: list[str] = [
    "Chest pain",           # 0 — high risk
    "Shortness of breath",  # 1 — high risk
    "Altered mental status",# 2 — very high risk
    "Trauma / Injury",      # 3 — variable
    "Abdominal pain",       # 4 — variable
    "Fever",                # 5 — variable
    "Nausea / Vomiting",    # 6 — lower risk
    "Headache",             # 7 — lower risk
    "Back pain",            # 8 — low risk
    "Other",                # 9 — low risk
]

# Weights for chief_complaint_code given each triage label index (0-3)
_CC_WEIGHTS_BY_TRIAGE: dict[int, list[float]] = {
    0: [0.05, 0.05, 0.02, 0.08, 0.10, 0.15, 0.15, 0.15, 0.15, 0.10],  # NON_URGENT
    1: [0.10, 0.10, 0.03, 0.12, 0.15, 0.15, 0.12, 0.10, 0.08, 0.05],  # SEMI_URGENT
    2: [0.20, 0.20, 0.05, 0.15, 0.15, 0.10, 0.05, 0.05, 0.03, 0.02],  # URGENT
    3: [0.15, 0.20, 0.20, 0.15, 0.10, 0.08, 0.04, 0.04, 0.02, 0.02],  # CRITICAL
}

# ---------------------------------------------------------------------------
# NEWS2 scoring
# ---------------------------------------------------------------------------

def news2_score(
    respiratory_rate: float,
    spo2: float,
    supplemental_o2: bool,
    temperature: float,
    systolic_bp: float,
    heart_rate: float,
    avpu: int = 0,
) -> int:
    """Return NEWS2 early-warning score (0–20+).

    avpu: 0=Alert, 3 = any non-Alert AVPU level.
    """
    score = 0

    # Respiratory rate
    if respiratory_rate <= 8:
        score += 3
    elif respiratory_rate <= 11:
        score += 1
    elif respiratory_rate <= 20:
        score += 0
    elif respiratory_rate <= 24:
        score += 2
    else:
        score += 3

    # SpO2
    if spo2 <= 91:
        score += 3
    elif spo2 <= 93:
        score += 2
    elif spo2 <= 95:
        score += 1

    # Supplemental O2
    if supplemental_o2:
        score += 2

    # Temperature
    if temperature <= 35.0:
        score += 3
    elif temperature <= 36.0:
        score += 1
    elif temperature <= 38.0:
        score += 0
    elif temperature <= 39.0:
        score += 1
    else:
        score += 2

    # Systolic BP
    if systolic_bp <= 90:
        score += 3
    elif systolic_bp <= 100:
        score += 2
    elif systolic_bp <= 110:
        score += 1
    elif systolic_bp <= 219:
        score += 0
    else:
        score += 3

    # Heart rate
    if heart_rate <= 40:
        score += 3
    elif heart_rate <= 50:
        score += 1
    elif heart_rate <= 90:
        score += 0
    elif heart_rate <= 110:
        score += 1
    elif heart_rate <= 130:
        score += 2
    else:
        score += 3

    # Consciousness
    score += avpu

    return score


def _news2_to_triage(score: int) -> int:
    """Map NEWS2 score to label index (0–3)."""
    if score >= 7:
        return 3  # CRITICAL
    if score >= 5:
        return 2  # URGENT
    if score >= 1:
        return 1  # SEMI_URGENT
    return 0      # NON_URGENT


# ---------------------------------------------------------------------------
# Vital-sign distributions (mean, std, lo_clamp, hi_clamp)
# ---------------------------------------------------------------------------

_DISTRIBUTIONS: dict[str, tuple[float, float, float, float]] = {
    "heart_rate":        (80.0,  18.0,  20.0,  220.0),
    "systolic_bp":       (120.0, 20.0,  60.0,  260.0),
    "respiratory_rate":  (18.0,  5.0,   4.0,   60.0),
    "spo2":              (97.0,  3.0,   70.0,  100.0),
    "temperature":       (37.1,  0.8,   33.0,  42.0),
    "age":               (55.0,  20.0,  18.0,  99.0),
    "pain_scale":        (4.5,   3.0,   0.0,   10.0),
}


def _try_fit_physionet_distributions() -> None:
    """If PhysioNet CSVs are present, update _DISTRIBUTIONS with real stats."""
    psv_files = list(PHYSIONET_DIR.rglob("*.psv"))
    if not psv_files:
        return
    try:
        import pandas as pd  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415

        dfs = [pd.read_csv(f, sep="|") for f in psv_files[:200]]
        df = pd.concat(dfs, ignore_index=True)
        mapping = {
            "HR":   "heart_rate",
            "SBP":  "systolic_bp",
            "Resp": "respiratory_rate",
            "O2Sat": "spo2",
            "Temp": "temperature",
        }
        for src, dst in mapping.items():
            if src in df.columns:
                col = df[src].dropna()
                lo, hi = _DISTRIBUTIONS[dst][2], _DISTRIBUTIONS[dst][3]
                mu = float(np.clip(col.mean(), lo, hi))
                sigma = float(col.std())
                _DISTRIBUTIONS[dst] = (mu, sigma, lo, hi)
        print(f"Fitted distributions from {len(psv_files)} PhysioNet PSV files.")
    except Exception as exc:  # noqa: BLE001
        print(f"PhysioNet fit skipped: {exc}")


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _sample_one(rng: random.Random) -> tuple[dict, int]:
    """Sample a single patient record, return (features, triage_label_index)."""
    hr    = _clamp(rng.gauss(*_DISTRIBUTIONS["heart_rate"][:2]),        *_DISTRIBUTIONS["heart_rate"][2:])
    sbp   = _clamp(rng.gauss(*_DISTRIBUTIONS["systolic_bp"][:2]),       *_DISTRIBUTIONS["systolic_bp"][2:])
    rr    = _clamp(rng.gauss(*_DISTRIBUTIONS["respiratory_rate"][:2]),  *_DISTRIBUTIONS["respiratory_rate"][2:])
    spo2  = _clamp(rng.gauss(*_DISTRIBUTIONS["spo2"][:2]),              *_DISTRIBUTIONS["spo2"][2:])
    temp  = _clamp(rng.gauss(*_DISTRIBUTIONS["temperature"][:2]),       *_DISTRIBUTIONS["temperature"][2:])
    age   = _clamp(rng.gauss(*_DISTRIBUTIONS["age"][:2]),               *_DISTRIBUTIONS["age"][2:])
    pain  = int(_clamp(round(rng.gauss(*_DISTRIBUTIONS["pain_scale"][:2])), 0.0, 10.0))

    # Diastolic BP correlated with systolic
    dbp = _clamp(sbp * 0.62 + rng.gauss(0, 6), 40.0, 150.0)

    # Derived shock index
    shock_index = round(hr / max(sbp, 1.0), 4)

    # NEWS2 labels derived ONLY from the observable vitals in the feature set.
    # avpu and supplemental_o2 are excluded so labels are a deterministic function
    # of the features the model will see — eliminating label noise.
    score = news2_score(
        respiratory_rate=rr,
        spo2=spo2,
        supplemental_o2=False,
        temperature=temp,
        systolic_bp=sbp,
        heart_rate=hr,
        avpu=0,
    )
    triage_idx = _news2_to_triage(score)

    # Chief complaint: weighted by triage category
    cc = rng.choices(range(len(CHIEF_COMPLAINTS)), weights=_CC_WEIGHTS_BY_TRIAGE[triage_idx])[0]

    record = {
        "heart_rate":           round(hr, 1),
        "systolic_bp":          round(sbp, 1),
        "diastolic_bp":         round(dbp, 1),
        "temperature":          round(temp, 2),
        "respiratory_rate":     round(rr, 1),
        "spo2":                 round(spo2, 1),
        "pain_scale":           pain,
        "age":                  round(age, 0),
        "chief_complaint_code": cc,
        "shock_index":          shock_index,
        "triage_label":         CATEGORY_ORDER[triage_idx],
    }
    return record, triage_idx


def generate(n_samples: int = 50_000, seed: int = 42) -> list[dict]:
    """Return n_samples labelled synthetic patient records."""
    _try_fit_physionet_distributions()
    rng = random.Random(seed)
    records = [_sample_one(rng)[0] for _ in range(n_samples)]
    return records


def save_csv(records: list[dict], path: Optional[Path] = None) -> Path:
    """Save records to CSV."""
    import pandas as pd  # noqa: PLC0415

    out = path or OUT_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df.to_csv(out, index=False)
    print(f"Saved {len(records)} rows → {out}")
    label_counts = df["triage_label"].value_counts()
    print("Label distribution:\n", label_counts.to_string())
    return out


if __name__ == "__main__":
    print(f"PhysioNet dir: {PHYSIONET_DIR} (exists={PHYSIONET_DIR.exists()})")
    records = generate(n_samples=50_000)
    save_csv(records)
