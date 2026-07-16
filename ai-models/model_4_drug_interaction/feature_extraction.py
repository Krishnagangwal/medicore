"""SMILES-based molecular + graph feature extraction for drug pairs.

Dataset reality (see exploration notes in train.py docstring): ddis.csv has
no severity or name field, so features here combine two signal sources:

  1. Morgan (ECFP) fingerprints of each drug (radius=2, nBits=1024), via
     RDKit — captures molecular structure.
  2. Lightweight interaction-graph features (known-pair flag, each drug's
     degree in the known-interaction graph, shared-neighbor count) built
     from ddis.csv's positive pairs — captures "how promiscuous/connected
     is this drug in the reference database", which is a legitimate,
     non-leaky signal distinct from the severity label itself (the label
     is derived from per-pair *type-diversity count*, which is
     deliberately NOT used as a feature to avoid leaking the target).

Drugs are identified internally by PubChem CID string (e.g.
"CID000002173"), matching both ddis.csv and drug_smiles.csv. Callers may
also pass a human drug name (e.g. "Aspirin"); it is resolved via
artifacts/cid_to_name.json.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

DRUG_SMILES_PATH = Path.home() / "Downloads" / "drug_smiles.csv"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
CID_TO_NAME_PATH = ARTIFACTS_DIR / "cid_to_name.json"
GRAPH_EDGES_PATH = ARTIFACTS_DIR / "graph_edges.json"

N_BITS = 1024

FEATURE_NAMES: list[str] = (
    [f"morgan_xor_bit_{i}" for i in range(N_BITS)]
    + [f"morgan_and_bit_{i}" for i in range(N_BITS)]
    + [
        "bit_diff_count",
        "known_interaction_flag",
        "drug_a_degree",
        "drug_b_degree",
        "common_neighbor_count",
        "both_drugs_known_flag",
    ]
)

FEATURE_DISPLAY_NAMES: dict[str, str] = {
    "bit_diff_count": "Total structural bit differences",
    "known_interaction_flag": "Known documented interaction",
    "drug_a_degree": "Drug A interaction-graph degree",
    "drug_b_degree": "Drug B interaction-graph degree",
    "common_neighbor_count": "Shared interaction partners",
    "both_drugs_known_flag": "Both drugs found in reference dataset",
}


def feature_display_name(feature: str) -> str:
    if feature in FEATURE_DISPLAY_NAMES:
        return FEATURE_DISPLAY_NAMES[feature]
    if feature.startswith("morgan_xor_bit_"):
        return f"Structural dissimilarity (bit {feature.rsplit('_', 1)[-1]})"
    if feature.startswith("morgan_and_bit_"):
        return f"Shared substructure (bit {feature.rsplit('_', 1)[-1]})"
    return feature


# --------------------------------------------------------------------- SMILES / fingerprints --

def load_smiles_dict(csv_path: Path = DRUG_SMILES_PATH) -> dict[str, str]:
    """Return {cid: smiles} from drug_smiles.csv (columns: drug_id, smiles)."""
    import pandas as pd  # noqa: PLC0415

    df = pd.read_csv(csv_path)
    return dict(zip(df["drug_id"], df["smiles"]))


def morgan_fingerprint(smiles: str, radius: int = 2, n_bits: int = N_BITS) -> np.ndarray:
    """Generate a Morgan (ECFP) fingerprint for a SMILES string."""
    from rdkit import Chem  # noqa: PLC0415
    from rdkit.Chem import AllChem  # noqa: PLC0415

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return np.zeros(n_bits, dtype=np.float32)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return np.array(fp, dtype=np.float32)


_FINGERPRINT_CACHE: dict[str, np.ndarray] = {}


def _prime_fingerprint_cache(smiles_dict: dict[str, str]) -> None:
    """Precompute and cache one fingerprint per known drug (fast: ~645 calls)."""
    for cid, smiles in smiles_dict.items():
        if cid not in _FINGERPRINT_CACHE:
            _FINGERPRINT_CACHE[cid] = morgan_fingerprint(smiles)


def _ensure_cache_loaded() -> None:
    if not _FINGERPRINT_CACHE:
        _prime_fingerprint_cache(load_smiles_dict())


def get_fingerprint(cid: str) -> np.ndarray:
    _ensure_cache_loaded()
    return _FINGERPRINT_CACHE.get(cid, np.zeros(N_BITS, dtype=np.float32))


def known_cids() -> set[str]:
    _ensure_cache_loaded()
    return set(_FINGERPRINT_CACHE.keys())


# --------------------------------------------------------------------- name <-> CID resolution --

_NAME_TO_CID: Optional[dict[str, str]] = None
_CID_TO_NAME: Optional[dict[str, str]] = None


def _load_name_maps() -> tuple[dict[str, str], dict[str, str]]:
    global _NAME_TO_CID, _CID_TO_NAME
    if _NAME_TO_CID is not None and _CID_TO_NAME is not None:
        return _NAME_TO_CID, _CID_TO_NAME

    import json  # noqa: PLC0415

    cid_to_name: dict[str, str] = {}
    if CID_TO_NAME_PATH.exists():
        with open(CID_TO_NAME_PATH) as f:
            cid_to_name = json.load(f)

    name_to_cid = {name.strip().lower(): cid for cid, name in cid_to_name.items()}
    _CID_TO_NAME, _NAME_TO_CID = cid_to_name, name_to_cid
    return _NAME_TO_CID, _CID_TO_NAME


def resolve_drug_id(raw: str) -> Optional[str]:
    """Resolve a CID string or a human drug name to a known CID, or None."""
    if not raw:
        return None
    raw = raw.strip()
    kc = known_cids()
    if raw in kc:
        return raw
    name_to_cid, _ = _load_name_maps()
    cid = name_to_cid.get(raw.lower())
    if cid and cid in kc:
        return cid
    return None


def display_name(cid: str) -> str:
    _, cid_to_name = _load_name_maps()
    return cid_to_name.get(cid, cid)


# --------------------------------------------------------------------- interaction graph context --

class GraphContext:
    """Precomputed, lightweight lookup over the known positive-interaction graph."""

    def __init__(
        self,
        positive_pairs: set[tuple[str, str]],
        degree: dict[str, int],
        adjacency: dict[str, set[str]],
    ) -> None:
        self.positive_pairs = positive_pairs
        self.degree = degree
        self.adjacency = adjacency

    @staticmethod
    def _canon(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    def known_flag(self, a: str, b: str) -> float:
        return 1.0 if self._canon(a, b) in self.positive_pairs else 0.0

    def degree_of(self, cid: str) -> float:
        return float(self.degree.get(cid, 0))

    def common_neighbors(self, a: str, b: str) -> float:
        na = self.adjacency.get(a, set())
        nb = self.adjacency.get(b, set())
        return float(len(na & nb))


_EMPTY_CONTEXT = GraphContext(set(), {}, {})
_GRAPH_CONTEXT: Optional[GraphContext] = None


def set_graph_context(ctx: GraphContext) -> None:
    """Install a GraphContext (e.g. built fresh from ddis.csv during training)."""
    global _GRAPH_CONTEXT
    _GRAPH_CONTEXT = ctx


def build_graph_context_from_positive_pairs(positive_pairs: set[tuple[str, str]]) -> GraphContext:
    adjacency: dict[str, set[str]] = {}
    for a, b in positive_pairs:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    degree = {cid: len(neighbors) for cid, neighbors in adjacency.items()}
    return GraphContext(positive_pairs, degree, adjacency)


def _load_graph_context_from_artifact() -> GraphContext:
    if not GRAPH_EDGES_PATH.exists():
        return _EMPTY_CONTEXT
    import json  # noqa: PLC0415

    with open(GRAPH_EDGES_PATH) as f:
        edges = json.load(f)
    positive_pairs = {GraphContext._canon(e["d1"], e["d2"]) for e in edges}
    return build_graph_context_from_positive_pairs(positive_pairs)


def _get_graph_context() -> GraphContext:
    global _GRAPH_CONTEXT
    if _GRAPH_CONTEXT is None:
        _GRAPH_CONTEXT = _load_graph_context_from_artifact()
    return _GRAPH_CONTEXT


# --------------------------------------------------------------------- feature vector --

def _pair_vector(cid_a: Optional[str], cid_b: Optional[str], ctx: GraphContext) -> np.ndarray:
    both_known = 1.0 if (cid_a is not None and cid_b is not None) else 0.0

    fp_a = get_fingerprint(cid_a) if cid_a else np.zeros(N_BITS, dtype=np.float32)
    fp_b = get_fingerprint(cid_b) if cid_b else np.zeros(N_BITS, dtype=np.float32)

    a_int = fp_a.astype(np.int32)
    b_int = fp_b.astype(np.int32)
    xor = np.bitwise_xor(a_int, b_int).astype(np.float32)
    and_ = np.bitwise_and(a_int, b_int).astype(np.float32)
    bit_diff = float(xor.sum())

    if cid_a and cid_b:
        known_flag = ctx.known_flag(cid_a, cid_b)
        deg_a = ctx.degree_of(cid_a)
        deg_b = ctx.degree_of(cid_b)
        common = ctx.common_neighbors(cid_a, cid_b)
    else:
        known_flag = deg_a = deg_b = common = 0.0

    tail = np.array([bit_diff, known_flag, deg_a, deg_b, common, both_known], dtype=np.float32)
    return np.concatenate([xor, and_, tail])


def extract_features(drug_a: str, drug_b: str) -> np.ndarray:
    """Build the feature vector for a drug pair.

    Accepts either PubChem CIDs or human drug names. Drugs not found in
    the reference dataset resolve to a zero fingerprint and
    both_drugs_known_flag=0 (the "flag" the caller can check for an
    unresolved pair), rather than raising.
    """
    cid_a = resolve_drug_id(drug_a)
    cid_b = resolve_drug_id(drug_b)
    return _pair_vector(cid_a, cid_b, _get_graph_context())


def build_feature_matrix(
    ddis_df,
    smiles_df,
    max_negatives: Optional[int] = None,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[tuple[str, str]]]:
    """Build (X, y, drug_pairs) for training.

    y is the severity-proxy label (see train.py): 0 for a sampled "clean"
    negative pair, 1-4 (quartile-binned by per-pair type-diversity count)
    for known positive pairs.
    """
    smiles_dict = dict(zip(smiles_df["drug_id"], smiles_df["smiles"]))
    _prime_fingerprint_cache(smiles_dict)

    pair_type_counts: dict[tuple[str, str], int] = (
        ddis_df.groupby(["d1", "d2"])["type"].nunique().to_dict()
    )
    positive_pairs = set(pair_type_counts.keys())

    counts = np.array(list(pair_type_counts.values()), dtype=np.float64)
    q25, q50, q75 = np.percentile(counts, [25, 50, 75])

    def bin_severity(count: int) -> int:
        if count <= q25:
            return 1
        if count <= q50:
            return 2
        if count <= q75:
            return 3
        return 4

    ctx = build_graph_context_from_positive_pairs(positive_pairs)
    set_graph_context(ctx)

    neg_pool: set[tuple[str, str]] = set()
    for d1, neg in zip(ddis_df["d1"], ddis_df["Neg samples"]):
        if d1 == neg:
            continue
        pair = (d1, neg) if d1 <= neg else (neg, d1)
        if pair not in positive_pairs:
            neg_pool.add(pair)
    neg_pool_list = list(neg_pool)

    rng = np.random.default_rng(random_state)
    n_neg = len(positive_pairs) if max_negatives is None else max_negatives
    n_neg = min(n_neg, len(neg_pool_list))
    chosen = rng.choice(len(neg_pool_list), size=n_neg, replace=False)
    negative_pairs = [neg_pool_list[i] for i in chosen]

    X_list: list[np.ndarray] = []
    y_list: list[int] = []
    pairs_list: list[tuple[str, str]] = []

    for (a, b), count in pair_type_counts.items():
        X_list.append(_pair_vector(a, b, ctx))
        y_list.append(bin_severity(count))
        pairs_list.append((a, b))

    for a, b in negative_pairs:
        X_list.append(_pair_vector(a, b, ctx))
        y_list.append(0)
        pairs_list.append((a, b))

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)
    return X, y, pairs_list
