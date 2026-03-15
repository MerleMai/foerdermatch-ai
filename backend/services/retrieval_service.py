from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from backend.db.query_cache_repo import get_cached_query_embedding, upsert_query_embedding
from backend.services.embedding_service import embed_query

EMBEDDING_MODEL = "text-embedding-3-small"


def _normalize_hit(doc: Any, md: Any, dist: Any) -> dict[str, Any]:
    return {
        "distance": float(dist),
        "metadata": md or {},
        "text": doc or "",
    }


def _collection_has_program_id(col) -> bool:
    try:
        sample = col.get(limit=1, include=["metadatas"])
        metas = (sample.get("metadatas") or [])
        if not metas:
            return False
        md0 = metas[0] or {}
        return "program_id" in md0
    except Exception:
        return False


def _pick_best_collection(client: chromadb.PersistentClient):
    cols = client.list_collections()
    if not cols:
        return client.get_or_create_collection("chunks")

    for c in cols:
        col = client.get_or_create_collection(c.name)
        if _collection_has_program_id(col):
            return col

    for c in cols:
        col = client.get_or_create_collection(c.name)
        try:
            if col.count() > 0:
                return col
        except Exception:
            continue

    return client.get_or_create_collection(cols[0].name)


def _get_query_embedding(*, db_path: Path, query_text: str) -> list[float]:
    cached = get_cached_query_embedding(
        db_path,
        model_name=EMBEDDING_MODEL,
        query_text=query_text,
    )
    if cached:
        return cached

    emb = embed_query(query_text, embedding_model=EMBEDDING_MODEL)
    upsert_query_embedding(
        db_path,
        model_name=EMBEDDING_MODEL,
        query_text=query_text,
        embedding=emb,
    )
    return emb


def _doc_type_weight(doc_type: str) -> float:
    dt = (doc_type or "").lower().strip()

    high = {
        "richtlinie_zim",
        "richtlinie_kmu_innovativ",
        "richtlinie_update_kmu_innovativ",
        "eew_foerderrichtlinie",
        "merkblatt_511",
        "merkblatt_512",
        "eew_modul1_merkblatt",
        "eew_modul2_merkblatt",
        "eew_modul3_merkblatt",
        "eew_modul4_merkblatt",
        "go_inno_richtlinie",
        "grw_koordinierungsrahmen_2026",
        "grw_merkblatt_mv",
    }

    medium = {
        "erp_bedingungen",
        "allgemeine_bedingungen_erp",
        "allgemeines_merkblatt_beihilfen",
        "de_minimis_infoblatt",
        "informationsbroschuere_kmu_innovativ",
        "leitfaden_kmu_innovativ",
        "go_inno_merkblatt",
        "go_inno_orientierungshilfe",
        "grw_foerdergebiete_2022_2027",
        "grw_merkblatt_tiefenpruefung_mv",
    }

    low = {
        "eew_glossar",
        "eew_softwareliste",
        "eew_infoblatt_co2_faktoren",
        "grw_ergaenzende_angaben_mv",
        "grw_antragsformular_mv",
    }

    if dt in high:
        return 1.0
    if dt in medium:
        return 0.9
    if dt in low:
        return 0.75
    return 0.85


def _rerank_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for h in hits:
        dist = float(h.get("distance") or 1.0)
        md = h.get("metadata") or {}
        doc_type = str(md.get("doc_type") or "")
        weight = _doc_type_weight(doc_type)

        # smaller distance is better
        score = weight / max(dist, 0.0001)
        h["_score"] = score

    hits.sort(key=lambda x: x["_score"], reverse=True)
    return hits


def _limit_per_document(hits: list[dict[str, Any]], max_per_doc: int = 2) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    per_doc: dict[int, int] = {}

    for h in hits:
        md = h.get("metadata") or {}
        doc_id = int(md.get("document_id") or 0)

        cnt = per_doc.get(doc_id, 0)
        if cnt >= max_per_doc:
            continue

        out.append(h)
        per_doc[doc_id] = cnt + 1

    return out


def retrieve_top_k(
    *,
    db_path: Path,
    chroma_dir: Path,
    program_id: str,
    query_text: str,
    k: int = 5,
) -> list[dict[str, Any]]:
    chroma_dir = Path(chroma_dir)
    if not chroma_dir.exists():
        raise FileNotFoundError(f"Chroma dir not found: {chroma_dir}")

    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = _pick_best_collection(client)

    query_emb = _get_query_embedding(db_path=db_path, query_text=query_text)

    pool_size = max(int(k) * 8, 40)

    res = col.query(
        query_embeddings=[query_emb],
        n_results=int(pool_size),
        where={"program_id": str(program_id)},
        include=["documents", "metadatas", "distances"],
    )

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    hits = [_normalize_hit(d, m, dist) for d, m, dist in zip(docs, metas, dists)]
    if not hits:
        return []

    hits = _rerank_hits(hits)
    hits = _limit_per_document(hits, max_per_doc=2)

    return hits[: int(k)]