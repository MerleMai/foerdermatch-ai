from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence


# ---------- Utilities ----------

def utcnow_sql() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ---------- Lightweight migrations ----------

def _table_info(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return {r["name"] for r in rows}


def ensure_query_embeddings_schema(conn: sqlite3.Connection) -> None:
    """
    Ensures query_embeddings exists and has the expected columns.
    Works even if an older DB already has query_embeddings without created_at/updated_at.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS query_embeddings (
          model_name      TEXT NOT NULL,
          query_hash      TEXT NOT NULL,
          query_text      TEXT NOT NULL,
          embedding_json  TEXT NOT NULL,
          created_at      TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
          PRIMARY KEY (model_name, query_hash)
        );
        """
    )

    cols = _table_info(conn, "query_embeddings")

    if "created_at" not in cols:
        conn.execute("ALTER TABLE query_embeddings ADD COLUMN created_at TEXT;")
        conn.execute("UPDATE query_embeddings SET created_at = COALESCE(created_at, datetime('now'));")

    if "updated_at" not in cols:
        conn.execute("ALTER TABLE query_embeddings ADD COLUMN updated_at TEXT;")
        conn.execute("UPDATE query_embeddings SET updated_at = COALESCE(updated_at, datetime('now'));")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_query_embeddings_updated_at
          ON query_embeddings(updated_at);
        """
    )


def run_migrations(conn: sqlite3.Connection) -> None:
    ensure_query_embeddings_schema(conn)


# ---------- Schema init ----------

def init_db(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")
    with connect(db_path) as conn:
        conn.executescript(schema_sql)
        run_migrations(conn)
        conn.commit()


# ---------- CRUD helpers ----------

def upsert_program(
    db_path: Path,
    *,
    program_id: str,
    name: str,
    name_official: Optional[str] = None,
    name_display: Optional[str] = None,
    provider: str,
    funding_type: str,
    focus_area: Optional[str] = None,
    geography: Optional[str] = None,
    variant: Optional[str] = None,
    source_url: Optional[str] = None,
    status: str = "active",
    notes: Optional[str] = None,
) -> None:
    now = utcnow_sql()
    sql = """
    INSERT INTO programs (
        id, name, name_official, name_display, provider, funding_type, focus_area, geography, variant,
        source_url, status, notes, created_at, updated_at
    ) VALUES (
        :id, :name, :name_official, :name_display, :provider, :funding_type, :focus_area, :geography, :variant,
        :source_url, :status, :notes, :created_at, :updated_at
    )
    ON CONFLICT(id) DO UPDATE SET
        name          = excluded.name,
        name_official = excluded.name_official,
        name_display  = excluded.name_display,
        provider      = excluded.provider,
        funding_type  = excluded.funding_type,
        focus_area    = excluded.focus_area,
        geography     = excluded.geography,
        variant       = excluded.variant,
        source_url    = excluded.source_url,
        status        = excluded.status,
        notes         = excluded.notes,
        updated_at    = excluded.updated_at;
    """

    params = {
        "id": program_id,
        "name": name,
        "name_official": name_official,
        "name_display": name_display,
        "provider": provider,
        "funding_type": funding_type,
        "focus_area": focus_area,
        "geography": geography,
        "variant": variant,
        "source_url": source_url,
        "status": status,
        "notes": notes,
        "created_at": now,
        "updated_at": now,
    }

    with connect(db_path) as conn:
        conn.execute(sql, params)
        conn.commit()


def upsert_program_project_form(
    db_path: Path,
    *,
    program_id: str,
    project_form: str,
) -> None:
    sql = """
    INSERT INTO program_project_forms (program_id, project_form)
    VALUES (?, ?)
    ON CONFLICT(program_id, project_form) DO NOTHING;
    """
    with connect(db_path) as conn:
        conn.execute(sql, (program_id, project_form))
        conn.commit()


def insert_document(
    db_path: Path,
    *,
    program_id: str,
    doc_type: str,
    file_path: Path,
    project_root: Path,
    source_url: Optional[str] = None,
    version_date: Optional[str] = None,
    last_checked_at: Optional[str] = None,
    compute_hash: bool = True,
) -> int:
    if not file_path.is_file():
        raise FileNotFoundError(f"Document file not found (or not a file): {file_path}")

    file_abs = file_path.resolve()
    root_abs = project_root.resolve()

    try:
        rel_path = str(file_abs.relative_to(root_abs))
    except ValueError as e:
        raise ValueError(
            f"Document path must be inside project_root.\n"
            f"project_root={root_abs}\n"
            f"file_path={file_abs}"
        ) from e

    filename = file_path.name
    sha = sha256_file(file_path) if compute_hash else None
    now = utcnow_sql()

    sql = """
    INSERT INTO documents (
        program_id, doc_type, filename, filepath, source_url, version_date,
        sha256, last_checked_at, last_ingested_at, created_at, updated_at
    ) VALUES (
        :program_id, :doc_type, :filename, :filepath, :source_url, :version_date,
        :sha256, :last_checked_at, NULL, :created_at, :updated_at
    )
    ON CONFLICT(program_id, doc_type) DO UPDATE SET
        filename        = excluded.filename,
        filepath        = excluded.filepath,
        source_url      = excluded.source_url,
        version_date    = excluded.version_date,
        sha256          = excluded.sha256,
        last_checked_at = COALESCE(excluded.last_checked_at, documents.last_checked_at),
        updated_at      = excluded.updated_at;
    """

    params = {
        "program_id": program_id,
        "doc_type": doc_type,
        "filename": filename,
        "filepath": rel_path,
        "source_url": source_url,
        "version_date": version_date,
        "sha256": sha,
        "last_checked_at": last_checked_at,
        "created_at": now,
        "updated_at": now,
    }

    with connect(db_path) as conn:
        conn.execute(sql, params)
        conn.commit()

        row = conn.execute(
            "SELECT id FROM documents WHERE program_id = ? AND doc_type = ?;",
            (program_id, doc_type),
        ).fetchone()

        if row is None:
            raise RuntimeError("insert_document: failed to fetch document id after insert/upsert")

        return int(row["id"])


def insert_chunks(
    db_path: Path,
    *,
    program_id: str,
    document_id: int,
    chunks: Sequence[dict[str, Any]],
    replace_existing: bool = True,
    mark_document_ingested: bool = True,
) -> int:
    if replace_existing:
        with connect(db_path) as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?;", (document_id,))
            conn.commit()

    rows_to_insert: list[tuple[Any, ...]] = []
    for c in chunks:
        try:
            chunk_index = int(c["chunk_index"])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid chunk item (missing/invalid chunk_index): {c}") from e

        text = (c.get("text") or "").strip()
        if not text:
            continue

        rows_to_insert.append(
            (
                program_id,
                document_id,
                chunk_index,
                c.get("page_ref"),
                text,
                c.get("chroma_id"),
                c.get("token_estimate"),
            )
        )

    sql = """
    INSERT INTO chunks (
        program_id, document_id, chunk_index, page_ref, text, chroma_id, token_estimate
    ) VALUES (?, ?, ?, ?, ?, ?, ?);
    """

    with connect(db_path) as conn:
        if rows_to_insert:
            conn.executemany(sql, rows_to_insert)

        if mark_document_ingested:
            now = utcnow_sql()
            conn.execute(
                "UPDATE documents SET last_ingested_at = ?, updated_at = ? WHERE id = ?;",
                (now, now, document_id),
            )

        conn.commit()

    return len(rows_to_insert)


def upsert_program_rule(
    db_path: Path,
    *,
    program_id: str,
    rule_id: str,
    rule_type: str,
    path: str,
    op: str,
    value: Any,
    weight: int,
    hard_fail: bool = False,
    unknown_factor: float = 0.35,
    reason_ok: Optional[str] = None,
    reason_fail: Optional[str] = None,
    missing_field: Optional[str] = None,
) -> None:
    now = utcnow_sql()
    sql = """
    INSERT INTO program_rules (
      program_id, rule_id, rule_type, path, op, value_json, weight, hard_fail,
      unknown_factor, reason_ok, reason_fail, missing_field, created_at, updated_at
    ) VALUES (
      :program_id, :rule_id, :rule_type, :path, :op, :value_json, :weight, :hard_fail,
      :unknown_factor, :reason_ok, :reason_fail, :missing_field, :created_at, :updated_at
    )
    ON CONFLICT(program_id, rule_id) DO UPDATE SET
      rule_type      = excluded.rule_type,
      path           = excluded.path,
      op             = excluded.op,
      value_json     = excluded.value_json,
      weight         = excluded.weight,
      hard_fail      = excluded.hard_fail,
      unknown_factor = excluded.unknown_factor,
      reason_ok      = excluded.reason_ok,
      reason_fail    = excluded.reason_fail,
      missing_field  = excluded.missing_field,
      updated_at     = excluded.updated_at;
    """
    params = {
        "program_id": program_id,
        "rule_id": rule_id,
        "rule_type": rule_type,
        "path": path,
        "op": op,
        "value_json": json.dumps(value, ensure_ascii=False),
        "weight": int(weight),
        "hard_fail": 1 if hard_fail else 0,
        "unknown_factor": float(unknown_factor),
        "reason_ok": reason_ok,
        "reason_fail": reason_fail,
        "missing_field": missing_field,
        "created_at": now,
        "updated_at": now,
    }
    with connect(db_path) as conn:
        conn.execute(sql, params)
        conn.commit()


# ---------- Read helpers ----------

def fetch_all_program_ids(db_path: Path) -> list[str]:
    """
    Returns all program IDs from the programs table.
    IMPORTANT: The programs PK column is `id` (not `program_id`).
    """
    with connect(db_path) as conn:
        rows = conn.execute("SELECT id FROM programs ORDER BY id;").fetchall()
    return [r["id"] for r in rows]


def fetch_program_rules(db_path: Path, *, program_id: str) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
              program_id, rule_id, rule_type, path, op, value_json, weight, hard_fail,
              unknown_factor, reason_ok, reason_fail, missing_field
            FROM program_rules
            WHERE program_id = ?
            ORDER BY id ASC
            """,
            (program_id,),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["value"] = json.loads(d.pop("value_json"))
        d["hard_fail"] = bool(d["hard_fail"])
        out.append(d)
    return out