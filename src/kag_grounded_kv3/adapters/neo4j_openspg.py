"""Optional Neo4j search and OpenSPG output adapters.

This module deliberately has no default password. Optional dependencies are
imported only when an adapter is instantiated or called.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from ..models import PathHop, PathRecord, RetrievalResult, SearchHit, SourceValue


class JsonGraphStore:
    """Loads sanitized source values and paths exported from a KAG project."""

    def __init__(self, source_values_path: str | Path, paths_path: str | Path) -> None:
        source_rows = json.loads(Path(source_values_path).read_text(encoding="utf-8"))
        path_rows = json.loads(Path(paths_path).read_text(encoding="utf-8"))
        self._sources = {
            row["id"]: SourceValue(
                id=row["id"],
                content=row["content"],
                name=row.get("name", row["id"]),
                chapter=row.get("chapter", ""),
            )
            for row in source_rows
        }
        self._paths = {
            row["id"]: PathRecord(
                id=row["id"],
                anchor_entity=row["anchor_entity"],
                target_entity=row["target_entity"],
                source_value_ids=tuple(row["source_value_ids"]),
                hops=tuple(
                    PathHop(
                        predicate=hop.get("predicate", ""),
                        source_quote=hop.get("source_quote", ""),
                    )
                    for hop in row.get("hops", [])
                ),
            )
            for row in path_rows
        }

    def source_ids(self) -> Iterable[str]:
        return self._sources.keys()

    def get_source(self, source_id: str) -> SourceValue:
        return self._sources[source_id]

    def get_path(self, path_id: str) -> PathRecord | None:
        return self._paths.get(path_id)


class Neo4jVectorIndex:
    """Runs Neo4j vector queries using a caller-provided embedding function."""

    def __init__(
        self,
        *,
        uri: str,
        user: str,
        password: str,
        database: str,
        indexes: dict[str, str],
        vectorize: Callable[[str], Sequence[float]],
    ) -> None:
        if not password:
            raise ValueError("a Neo4j password must be provided explicitly")
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("install the 'neo4j' optional dependency") from exc
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._indexes = dict(indexes)
        self._vectorize = vectorize

    @classmethod
    def from_env(
        cls,
        *,
        indexes: dict[str, str],
        vectorize: Callable[[str], Sequence[float]],
    ) -> Neo4jVectorIndex:
        required = ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE"]
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise RuntimeError(f"missing environment variables: {', '.join(missing)}")
        return cls(
            uri=os.environ["NEO4J_URI"],
            user=os.environ["NEO4J_USER"],
            password=os.environ["NEO4J_PASSWORD"],
            database=os.environ["NEO4J_DATABASE"],
            indexes=indexes,
            vectorize=vectorize,
        )

    def search(self, view: str, query: str, limit: int) -> Sequence[SearchHit]:
        if view not in self._indexes:
            raise KeyError(f"no vector index configured for view: {view}")
        vector = list(self._vectorize(query))
        with self._driver.session(database=self._database) as session:
            rows = session.run(
                "CALL db.index.vector.queryNodes($index_name,$limit,$vector) "
                "YIELD node,score RETURN node,score",
                index_name=self._indexes[view],
                limit=int(limit),
                vector=vector,
            ).data()
        return [
            SearchHit(
                id=str(dict(row["node"]).get("id", "")),
                view=view,
                score=float(row.get("score", 0.0)),
                content=str(dict(row["node"]).get("content", "")),
                source_value_ids=tuple(_as_string_list(dict(row["node"]).get("source_value_ids"))),
                source_quotes=tuple(_as_string_list(dict(row["node"]).get("source_quotes"))),
                path_id=str(dict(row["node"]).get("path_id", "")),
            )
            for row in rows
        ]

    def close(self) -> None:
        self._driver.close()


def _as_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def to_openspg_output(result: RetrievalResult, *, method: str = "grounded_kv3"):
    """Converts standalone results to KAG's RetrieverOutput on demand."""

    try:
        from kag.interface import ChunkData, RetrieverOutput
    except ImportError as exc:
        raise RuntimeError("OpenSPG KAG must be installed to convert this result") from exc
    chunks = [
        ChunkData(
            content=chunk.content,
            title=chunk.name,
            chunk_id=chunk.id,
            score=chunk.score,
            properties={
                "view_type": "source_value",
                "candidate": "kv_conditional_path",
                "channels": list(chunk.channels),
            },
        )
        for chunk in result.chunks
    ]
    return RetrieverOutput(chunks=chunks, retriever_method=method)
