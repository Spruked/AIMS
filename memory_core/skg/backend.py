"""Derived-SKG storage contract and zero-dependency reference backend.

Backends never establish authority. They receive only events already committed
to the Vault and may be discarded and rebuilt at any time.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Protocol

from .types import Edge, EdgeState


class SKGBackend(Protocol):
    def clear_derived_state(self) -> None: ...
    def upsert_edge(self, edge: Edge) -> None: ...
    def edge(self, edge_id: str) -> Optional[Edge]: ...
    def all_edges(self) -> List[Edge]: ...
    def merge_aliases(self, aliases: Dict[str, str]) -> None: ...
    def resolve(self, atom_id: str) -> str: ...
    def state_digest(self) -> str: ...


class PythonSKGBackend:
    """Reference implementation: deterministic in-memory derived state.

    A restart rebuilds this backend from Vault SKG events. It remains the
    compatibility baseline against which optional accelerated backends are
    tested.
    """

    def __init__(self):
        self._edges: Dict[str, Edge] = {}
        self._aliases: Dict[str, str] = {}

    def clear_derived_state(self) -> None:
        self._edges.clear()
        self._aliases.clear()

    def upsert_edge(self, edge: Edge) -> None:
        self._edges[edge.edge_id] = edge.copy()

    def edge(self, edge_id: str) -> Optional[Edge]:
        edge = self._edges.get(edge_id)
        return edge.copy() if edge else None

    def all_edges(self) -> List[Edge]:
        return [self._edges[key].copy() for key in sorted(self._edges)]

    def merge_aliases(self, aliases: Dict[str, str]) -> None:
        self._aliases.update(aliases)

    def resolve(self, atom_id: str) -> str:
        seen = set()
        while atom_id in self._aliases and atom_id not in seen:
            seen.add(atom_id)
            atom_id = self._aliases[atom_id]
        return atom_id

    def aliases(self) -> Dict[str, str]:
        return dict(self._aliases)

    def state_digest(self) -> str:
        payload = {
            "aliases": dict(sorted(self._aliases.items())),
            "edges": [edge.to_dict() for edge in self.all_edges()],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GraphQLiteSKGBackend(PythonSKGBackend):
    """Optional embedded GraphQLite mirror for accelerated graph queries.

    The Python backend remains the deterministic state reference. GraphQLite
    receives the same already-authoritative state and can be removed/rebuilt
    without affecting the Vault. The adapter is deliberately opt-in so a
    normal A.I.M.S. installation has no native graph dependency.
    """

    def __init__(self, database_path: str = ":memory:"):
        super().__init__()
        try:
            from graphqlite import Graph
        except ImportError as error:
            raise RuntimeError(
                "GraphQLite is not installed. Install the optional dependency "
                "with `pip install .[graphqlite]`."
            ) from error
        self._graph = Graph(database_path)

    def clear_derived_state(self) -> None:
        super().clear_derived_state()
        self._graph.query("MATCH (n) DETACH DELETE n")

    def upsert_edge(self, edge: Edge) -> None:
        super().upsert_edge(edge)
        properties = edge.to_dict()
        self._graph.upsert_node(edge.source_id, {"atom_id": edge.source_id}, label="VaultAtom")
        self._graph.upsert_node(edge.target_id, {"atom_id": edge.target_id}, label="VaultAtom")
        self._graph.upsert_edge(
            edge.source_id,
            edge.target_id,
            properties,
            rel_type=edge.relation.value.upper(),
        )

    def query(self, cypher: str):
        """Run an accelerated derived-state query. Never use its result as authority."""
        return self._graph.query(cypher)

    def close(self) -> None:
        """Release the optional native database handle, required on Windows."""
        if self._graph is not None:
            self._graph.close()
            self._graph = None

    def __enter__(self) -> "GraphQLiteSKGBackend":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def graphqlite_backend_factory(directory: Path) -> Callable[[str], SKGBackend]:
    """Create isolated GraphQLite derived stores for the three logical SKGs."""
    root = Path(directory)

    def create(domain: str) -> SKGBackend:
        root.mkdir(parents=True, exist_ok=True)
        return GraphQLiteSKGBackend(str(root / f"{domain}.graphqlite"))

    return create
