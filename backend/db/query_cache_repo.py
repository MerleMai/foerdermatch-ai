from __future__ import annotations

import hashlib
import json
from typing import Optional

from backend.db.repo import connect, utcnow_sql


def query_hash(query: str) -> str:
    return hashlib.sha256(query.strip().encode("utf-8")).hexdigest()


def get_cached_query_embedding(
    db_path,
    *,
    model_name: str,
    query_text: str,
) -> Optional[list[float]]:
    """
    Returns cached embedding for (model_name, query_hash(query_text)) if present.
    """
    qh = query_hash(query_text)

    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT embedding_json
            FROM query_embeddings
            WHERE model_name = ? AND query_hash = ?
            """,
            (model_name, qh),
        ).fetchone()

    if not row:
        return None

    return json.loads(row["embedding_json"])


def upsert_query_embedding(
    db_path,
    *,
    model_name: str,
    query_text: str,
    embedding: list[float],
) -> None:
    """
    Inserts or updates the cached embedding for (model_name, query_hash(query_text)).
    """
    qh = query_hash(query_text)
    now = utcnow_sql()

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO query_embeddings (
              model_name, query_hash, query_text, embedding_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_name, query_hash) DO UPDATE SET
              query_text     = excluded.query_text,
              embedding_json = excluded.embedding_json,
              updated_at     = excluded.updated_at
            """,
            (
                model_name,
                qh,
                query_text,
                json.dumps(embedding),
                now,
                now,
            ),
        )
        conn.commit()