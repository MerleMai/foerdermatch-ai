from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

from backend.db.repo import init_db, insert_chunks
from backend.services.embedding_service import get_collection

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "programs.db"
SCHEMA = ROOT / "backend" / "db" / "schema.sql"
CHROMA_DIR = ROOT / "data" / "chroma"

_ws_re = re.compile(r"\s+")


def clean_text(t: str) -> str:
    t = t.replace("\x00", " ")
    t = t.replace("\u00ad", "")
    t = t.replace("­", "")
    for ch in ["•", "", "▪", "■", "◦", "‣", "·", "–"]:
        t = t.replace(ch, " ")
    t = _ws_re.sub(" ", t).strip()
    return t


def extract_pages(pdf_path: Path) -> list[dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    pages: list[dict[str, Any]] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "text": clean_text(text)})
    return pages


def chunk_pages(
    pages: list[dict[str, Any]],
    *,
    max_words: int = 900,
    overlap_words: int = 150,
) -> list[dict[str, Any]]:
    stream: list[tuple[str, int]] = []
    for p in pages:
        page_no = int(p["page"])
        words = (p["text"] or "").split()
        for w in words:
            stream.append((w, page_no))

    if not stream:
        return []

    chunks: list[dict[str, Any]] = []
    i = 0
    chunk_index = 0
    n = len(stream)

    while i < n:
        end = min(i + max_words, n)
        slice_words = stream[i:end]
        text = " ".join([w for w, _pg in slice_words]).strip()
        if text and len(text.split()) >= 80:
            pages_in_chunk = [pg for _w, pg in slice_words]
            p1, p2 = min(pages_in_chunk), max(pages_in_chunk)
            page_ref = f"S. {p1}" if p1 == p2 else f"S. {p1}-{p2}"
            chunks.append({"chunk_index": chunk_index, "page_ref": page_ref, "text": text})
            chunk_index += 1

        if end == n:
            break
        i = max(0, end - overlap_words)

    return chunks


def fetch_documents_for_program(program_id: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    rows = conn.execute(
        "SELECT id, program_id, doc_type, filename, filepath FROM documents WHERE program_id = ? ORDER BY id;",
        (program_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def should_index(doc_type: str) -> bool:
    """
    Whitelist indexing: keep DB docs, but only embed/index core docs into Chroma.
    """
    doc_type = (doc_type or "").strip().lower()

    core = {
        "merkblatt_511",
        "merkblatt_512",
        "erp_bedingungen",
        "allgemeine_bedingungen_erp",
        "allgemeines_merkblatt_beihilfen",
        "ausschlussliste_kfw",
        "investitionskredite_bestimmungen",
        "kmu_definition",
        "richtlinie_zim",
        "de_minimis_infoblatt",
        "richtlinie_kmu_innovativ",
        "richtlinie_update_kmu_innovativ",
        "informationsbroschuere_kmu_innovativ",
        "leitfaden_kmu_innovativ",
        "eew_merkblatt",
        "eew_foerderrichtlinie",
        "eew_glossar",
        "eew_infoblatt_co2_faktoren",
        "eew_modul1_merkblatt",
        "eew_modul2_merkblatt",
        "eew_modul3_merkblatt",
        "eew_softwareliste",
        "eew_modul4_merkblatt",
        "grw_koordinierungsrahmen_2026",
        "grw_foerdergebiete_2022_2027",
        "grw_merkblatt_mv",
        "grw_merkblatt_tiefenpruefung_mv",
        "grw_ergaenzende_angaben_mv",
        "grw_antragsformular_mv",
        "go_inno_richtlinie",
        "go_inno_merkblatt",
        "go_inno_orientierungshilfe",
    }
    return doc_type in core


def batched(seq: list[Any], batch_size: int) -> Iterable[list[Any]]:
    for i in range(0, len(seq), batch_size):
        yield seq[i:i + batch_size]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--max-words", type=int, default=280)
    parser.add_argument("--overlap-words", type=int, default=80)
    parser.add_argument("--embed-batch-size", type=int, default=50)
    args = parser.parse_args()

    program_id = args.program_id
    embed_batch_size = max(1, int(args.embed_batch_size))

    init_db(DB, SCHEMA)
    collection = get_collection(persist_dir=CHROMA_DIR)

    docs = fetch_documents_for_program(program_id)
    if not docs:
        raise SystemExit(f"No documents found for program_id={program_id}. Did you run demo_seed.py?")

    total_docs = 0
    total_chunks = 0

    for d in docs:
        doc_id = int(d["id"])
        doc_type = str(d["doc_type"])
        filepath = ROOT / str(d["filepath"])

        if not filepath.is_file():
            print(f"[WARN] Missing file on disk: {filepath} (doc_type={doc_type})")
            continue

        if not should_index(doc_type):
            print(f"[SKIP] Not indexing doc_type={doc_type} (kept in DB, excluded from Chroma)")
            continue

        print(f"[INGEST] program={program_id} doc_type={doc_type} file={filepath.name}")
        pages = extract_pages(filepath)
        chunks = chunk_pages(pages, max_words=args.max_words, overlap_words=args.overlap_words)

        for c in chunks:
            c["chroma_id"] = f"{program_id}:{doc_id}:{c['chunk_index']}"

        ids = [c["chroma_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "program_id": program_id,
                "document_id": doc_id,
                "doc_type": doc_type,
                "filename": filepath.name,
                "page_ref": c.get("page_ref"),
                "chunk_index": int(c["chunk_index"]),
            }
            for c in chunks
        ]

        if ids:
            for ids_batch, docs_batch, metas_batch in zip(
                batched(ids, embed_batch_size),
                batched(documents, embed_batch_size),
                batched(metadatas, embed_batch_size),
            ):
                collection.upsert(
                    ids=ids_batch,
                    documents=docs_batch,
                    metadatas=metas_batch,
                )

        inserted = insert_chunks(
            DB,
            program_id=program_id,
            document_id=doc_id,
            chunks=chunks,
            replace_existing=True,
            mark_document_ingested=True,
        )

        total_docs += 1
        total_chunks += inserted
        print(f"  -> {inserted} chunks")
        if inserted == 0:
            print("  -> WARNING: no usable text chunks extracted")

    print(f"\nDone. Indexed {total_docs} documents, stored {total_chunks} chunks (program_id={program_id}).")


if __name__ == "__main__":
    main()