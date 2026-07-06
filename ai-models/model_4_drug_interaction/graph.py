"""Drug-drug interaction knowledge graph built from the DDIS dataset.

Backed by NetworkX. Used at inference time to do a fast graph lookup before
falling back to the ML model for unknown pairs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

DDIS_PATH = Path.home() / "Downloads" / "ddis.csv"


class DrugInteractionGraph:
    """Directed graph: edge (drug_a, drug_b) carries severity + description."""

    def __init__(self) -> None:
        try:
            import networkx as nx  # noqa: PLC0415
            self._g: Optional[object] = nx.DiGraph()
        except ImportError:
            self._g = None
        self._loaded = False

    def load(self, csv_path: Path = DDIS_PATH) -> None:
        """Populate graph from DDIS CSV (columns: drug_a, drug_b, severity, description)."""
        if self._g is None:
            return

        import pandas as pd  # noqa: PLC0415

        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            a = str(row.get("drug_a", "")).lower()
            b = str(row.get("drug_b", "")).lower()
            if a and b:
                self._g.add_edge(  # type: ignore[union-attr]
                    a,
                    b,
                    severity=row.get("severity", "UNKNOWN"),
                    description=row.get("description", ""),
                )
        self._loaded = True

    def get_interaction(self, drug_a: str, drug_b: str) -> Optional[dict]:
        """Return edge data for (drug_a, drug_b) or None if no interaction exists."""
        if not self._loaded or self._g is None:
            return None
        a, b = drug_a.lower(), drug_b.lower()
        if self._g.has_edge(a, b):  # type: ignore[union-attr]
            return dict(self._g[a][b])  # type: ignore[index]
        if self._g.has_edge(b, a):  # type: ignore[union-attr]
            return dict(self._g[b][a])  # type: ignore[index]
        return None

    def has_interaction(self, drug_a: str, drug_b: str) -> bool:
        return self.get_interaction(drug_a, drug_b) is not None
