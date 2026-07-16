"""Drug-drug interaction knowledge graph, backed by NetworkX.

Loads from the compact artifacts/graph_edges.json produced by train.py
(fast: ~63k rows) rather than re-scanning the 195MB ddis.csv on every
import. Falls back to building directly from ddis.csv if the artifact
doesn't exist yet (e.g. before the first training run).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import networkx as nx

import feature_extraction as fe

DDIS_PATH = Path.home() / "Downloads" / "ddis.csv"
GRAPH_EDGES_PATH = Path(__file__).parent / "artifacts" / "graph_edges.json"


class DrugInteractionGraph:
    """Directed graph: edge (drug_a, drug_b) carries severity + severity_code."""

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()
        self._loaded = False

    def load(self, edges_path: Path = GRAPH_EDGES_PATH, ddis_path: Path = DDIS_PATH) -> None:
        """Populate the graph, preferring the compact trained artifact."""
        if edges_path.exists():
            self._load_from_artifact(edges_path)
        elif ddis_path.exists():
            self._load_from_raw_ddis(ddis_path)
        self._loaded = True

    def _load_from_artifact(self, edges_path: Path) -> None:
        with open(edges_path) as f:
            edges = json.load(f)
        for e in edges:
            self._g.add_edge(
                e["d1"],
                e["d2"],
                severity=e["severity"],
                severity_code=e["severity_code"],
            )

    def _load_from_raw_ddis(self, ddis_path: Path) -> None:
        """Slow fallback: build directly from the raw dataset (no severity proxy applied)."""
        import pandas as pd  # noqa: PLC0415

        df = pd.read_csv(
            ddis_path,
            dtype={"d1": "category", "d2": "category", "type": "int16", "Neg samples": "category"},
        )
        type_counts = df.groupby(["d1", "d2"])["type"].nunique()
        for (a, b), count in type_counts.items():
            self._g.add_edge(a, b, severity="unknown", severity_code=None, type_count=int(count))

    def get_interaction(self, drug_a: str, drug_b: str) -> Optional[dict]:
        if not self._loaded:
            return None
        a = fe.resolve_drug_id(drug_a) or drug_a
        b = fe.resolve_drug_id(drug_b) or drug_b
        if self._g.has_edge(a, b):
            return dict(self._g[a][b])
        if self._g.has_edge(b, a):
            return dict(self._g[b][a])
        return None

    def has_interaction(self, drug_a: str, drug_b: str) -> bool:
        return self.get_interaction(drug_a, drug_b) is not None

    def to_json(self, drug_list: list[str]) -> dict:
        """Return the subgraph induced by drug_list as {"nodes": [...], "edges": [...]}.

        Unresolved/unknown drugs are still included as isolated nodes.
        Fewer than 2 drugs -> empty nodes and edges.
        """
        if len(drug_list) < 2:
            return {"nodes": [], "edges": []}

        resolved: list[tuple[str, str]] = []  # (original_label, node_id)
        for raw in drug_list:
            cid = fe.resolve_drug_id(raw)
            node_id = cid or raw
            label = fe.display_name(cid) if cid else raw
            resolved.append((label, node_id))

        nodes = [{"id": node_id, "label": label} for label, node_id in resolved]

        edges = []
        for i in range(len(resolved)):
            for j in range(i + 1, len(resolved)):
                _, id_a = resolved[i]
                _, id_b = resolved[j]
                data = None
                if self._loaded and self._g.has_edge(id_a, id_b):
                    data = self._g[id_a][id_b]
                    source, target = id_a, id_b
                elif self._loaded and self._g.has_edge(id_b, id_a):
                    data = self._g[id_b][id_a]
                    source, target = id_b, id_a
                if data is not None:
                    edges.append(
                        {
                            "source": source,
                            "target": target,
                            "severity": data.get("severity", "unknown"),
                            "severity_code": data.get("severity_code"),
                        }
                    )

        return {"nodes": nodes, "edges": edges}


_GRAPH: Optional[DrugInteractionGraph] = None


def get_graph() -> DrugInteractionGraph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = DrugInteractionGraph()
        _GRAPH.load()
    return _GRAPH


def to_json(drug_list: list[str]) -> dict:
    return get_graph().to_json(drug_list)
