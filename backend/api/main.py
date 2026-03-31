# backend/api/main.py
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from backend.config import require_env
require_env("OPENAI_API_KEY")

from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from typing import Any, Optional, Literal
import mimetypes

from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from backend.db.repo import fetch_all_program_ids, connect
from backend.services.rag_service import build_grounded_detail_from_chunks, validate_grounded_output
from backend.services.scoring_service import ScoreConfig, score_program

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "programs.db"
CHROMA_DIR = ROOT / "data" / "chroma"

app = FastAPI(
    title="FörderMatch AI API",
    version="0.3.0",
    description=(
        "Demo-API für FörderMatch AI.\n\n"
        "- /rank: Programme ranken (Rules + Semantic Retrieval)\n"
        "- /detail: Detailansicht für ein Programm inkl. grounded RAG (Quellengebunden)\n"
        "- /evaluate: raw scoring/debug\n"
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://foerdermatch-ai.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Criticality = Literal["low", "medium", "high"]
ProgramStatus = Literal["eligible", "maybe", "blocked"]


class EvaluateRequest(BaseModel):
    program_id: str
    profile: dict[str, Any] = Field(default_factory=dict)
    query_text: str
    retrieval_k: int = Field(default=5, ge=1, le=10)


class DetailRequest(BaseModel):
    program_id: str
    profile: dict[str, Any] = Field(default_factory=dict)
    query_text: str
    retrieval_k: int = Field(default=5, ge=1, le=10)


class RankRequest(BaseModel):
    query_text: str
    profile: dict[str, Any] = Field(default_factory=dict)
    program_ids: Optional[list[str]] = None
    retrieval_k: int = Field(default=5, ge=1, le=10)
    limit: int = Field(default=5, ge=1, le=20)
    include_detail_top_n: int = Field(default=1, ge=0, le=5)


class SourceRef(BaseModel):
    doc_type: str
    filename: str
    page_ref: str
    document_id: int
    chunk_index: int
    distance: float
    source_url: Optional[str] = None
    filepath: Optional[str] = None
    url: Optional[str] = None


class ChecklistItem(BaseModel):
    item: str
    criticality: Criticality
    source_refs: list[SourceRef] = Field(default_factory=list)


class RiskItem(BaseModel):
    risk: str
    criticality: Criticality
    source_refs: list[SourceRef] = Field(default_factory=list)


class DetailPayload(BaseModel):
    summary: str
    program_requirements: list[ChecklistItem] = Field(default_factory=list)
    typical_risks: list[RiskItem] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    disclaimer: Optional[str] = None


class HardFailExplain(BaseModel):
    hard_fail_summary: str
    hard_fail_rule_ids: list[str] = Field(default_factory=list)
    hard_fail_rule_details: list[dict[str, Any]] = Field(default_factory=list)


class ProgramResult(BaseModel):
    program_id: str
    program_name: Optional[str] = None
    program_name_official: Optional[str] = None
    total_score: int
    effective_total_score: int
    rule_score: int
    semantic_score: int
    hard_fail: bool
    hard_fail_reasons: list[str] = Field(default_factory=list)
    blocked_label: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
    rules: list[dict[str, Any]] = Field(default_factory=list)
    status: ProgramStatus
    badge: str
    next_actions: list[str] = Field(default_factory=list)
    hard_fail_explain: Optional[HardFailExplain] = None
    rule_engine_note: Optional[str] = None
    retrieval_note: Optional[str] = None
    scoring_spec: Optional[dict[str, Any]] = None
    detail: Optional[DetailPayload] = None


class RankResponse(BaseModel):
    query_text: str
    retrieval_k: int
    limit: int
    include_detail_top_n: int
    results: list[ProgramResult]


def _clamp_int(x: int, lo: int, hi: int) -> int:
    try:
        v = int(x)
    except Exception:
        v = lo
    return max(lo, min(hi, v))


def _ensure_backend_ready() -> None:
    if not DB.exists():
        raise HTTPException(status_code=503, detail=f"DB missing: {DB}. Run ingest/init first.")
    if not CHROMA_DIR.exists():
        raise HTTPException(status_code=503, detail=f"Chroma dir missing: {CHROMA_DIR}. Run embeddings/ingest first.")


def _ensure_program_exists(program_id: str) -> None:
    program_id = (program_id or "").strip()
    if not program_id:
        raise HTTPException(status_code=422, detail="program_id is required.")
    _ensure_backend_ready()
    all_ids = set(fetch_all_program_ids(DB))
    if program_id not in all_ids:
        raise HTTPException(status_code=404, detail=f"Unknown program_id: {program_id}")


def _fetch_program_names(program_id: str) -> dict[str, Optional[str]]:
    with connect(DB) as conn:
        row = conn.execute(
            """
            SELECT name, name_official, name_display
            FROM programs
            WHERE id = ?
            """,
            (program_id,),
        ).fetchone()

    if not row:
        return {
            "program_name": program_id,
            "program_name_official": program_id,
        }

    return {
        "program_name": row["name_display"] or row["name"] or program_id,
        "program_name_official": row["name_official"] or row["name"] or program_id,
    }


def _status_and_badge(*, hard_fail: bool, missing_fields: list[str]) -> tuple[ProgramStatus, str]:
    if hard_fail:
        return "blocked", "Blocked"
    if missing_fields:
        return "maybe", "Missing info"
    return "eligible", "Eligible"


def _next_actions_from_missing(missing_fields: list[str]) -> list[str]:
    if not missing_fields:
        return []
    actions: list[str] = []
    for f in missing_fields:
        if "de_minimis" in f:
            actions.append("De-minimis-Status angeben und bisherige Beihilfen dokumentieren.")
        elif "project.start_status" in f or "start_status" in f:
            actions.append("Projektstatus angeben, da der Vorhabensbeginn ein typischer Ausschlussgrund ist.")
        else:
            actions.append(f"Fehlende Angabe ergänzen: {f}")
    out: list[str] = []
    seen: set[str] = set()
    for action in actions:
        if action not in seen:
            seen.add(action)
            out.append(action)
    return out


def _default_next_actions_for_program(program_id: str) -> list[str]:
    pid = (program_id or "").upper()

    if pid.startswith("KFW-ERP-DIGI-511") or pid.startswith("KFW-ERP-DIGI-512"):
        return [
            "Digitalisierungsvorhaben, Kosten und Projektumfang konkret beschreiben.",
            "Investitions- und Betriebsmittelkosten strukturiert vorbereiten.",
            "Finanzierungspartner bzw. Hausbank frühzeitig ansprechen.",
            "Antrag vor Vorhabensbeginn abstimmen und einreichen.",
        ]

    if pid == "ZIM":
        return [
            "FuE-Gehalt und technisches Risiko des Vorhabens klar herausarbeiten.",
            "Arbeitsplan, Projektziele und Innovationshöhe dokumentieren.",
            "Geeignete Projektform prüfen.",
            "Skizze oder Antrag beim zuständigen Projektträger vorbereiten.",
        ]

    if pid == "KMU-INNOVATIV":
        return [
            "Vorhaben klar als risikoreiches FuE-Projekt abgrenzen.",
            "Passung zur Förderbekanntmachung fachlich prüfen.",
            "Projektskizze mit Zielen, Innovation und Verwertung vorbereiten.",
            "Einreichungsstichtage und Verfahrensschritte beachten.",
        ]

    if pid.startswith("EEW-BAFA-"):
        return [
            "Fördermodul und technische Maßnahme eindeutig festlegen.",
            "Energieeinsparung oder THG-Minderung belastbar nachweisen.",
            "Technische Unterlagen und Investitionskosten vorbereiten.",
            "Antrag vor Maßnahmenbeginn einreichen.",
        ]

    if pid == "GO-INNO":
        return [
            "Innovationsberatungsbedarf und Beratungsziel klar beschreiben.",
            "Passendes Fördermodul auswählen.",
            "Autorisierte Beratungsunternehmen prüfen.",
            "Förderantrag vor Beginn der Beratung vorbereiten.",
        ]

    if pid == "GRW-MV-GEWERBE":
        return [
            "Standort im Fördergebiet und Investitionsvorhaben sauber nachweisen.",
            "Primäreffekt und Investitionsschwelle dokumentieren.",
            "Förderfähigkeit mit zuständiger Stelle abstimmen.",
            "Antragsunterlagen vollständig vorbereiten.",
        ]

    return [
        "Fördervoraussetzungen anhand der Programmdetails prüfen.",
        "Projektunterlagen und Kostenplanung strukturieren.",
        "Antragsweg und Fristen gesondert absichern.",
    ]


def _hard_fail_explain(rules: list[dict[str, Any]], hard_fail_reasons: list[str]) -> Optional[HardFailExplain]:
    if not hard_fail_reasons:
        return None
    hf_rules = [
        r for r in rules
        if bool(r.get("hard_fail")) and str(r.get("status") or "").lower() == "failed"
    ]
    hf_rule_ids = [str(r.get("rule_id") or "").strip() for r in hf_rules if str(r.get("rule_id") or "").strip()]
    return HardFailExplain(
        hard_fail_summary=hard_fail_reasons[0],
        hard_fail_rule_ids=hf_rule_ids,
        hard_fail_rule_details=hf_rules,
    )


def _blocked_label(hard_fail: bool, reasons: list[str]) -> Optional[str]:
    if not hard_fail:
        return None
    if reasons:
        return reasons[0]
    return "Hard-fail condition triggered."


def _fetch_document_link_map(document_ids: list[int], request: Request) -> dict[int, dict[str, Optional[str]]]:
    ids = sorted({int(x) for x in document_ids if int(x) > 0})
    if not ids:
        return {}

    placeholders = ",".join("?" for _ in ids)
    sql = f"""
        SELECT id, filename, filepath, source_url
        FROM documents
        WHERE id IN ({placeholders})
    """

    with connect(DB) as conn:
        rows = conn.execute(sql, ids).fetchall()

    out: dict[int, dict[str, Optional[str]]] = {}
    for r in rows:
        document_id = int(r["id"])
        filepath = str(r["filepath"] or "").strip() or None
        source_url = str(r["source_url"] or "").strip() or None
        local_url = str(request.url_for("open_document_file", document_id=document_id))
        out[document_id] = {
            "filepath": filepath,
            "source_url": source_url,
            "url": local_url,
        }
    return out


def _to_source_ref_list(
    raw_sources: list[dict[str, Any]],
    *,
    request: Request,
    document_link_map: Optional[dict[int, dict[str, Optional[str]]]] = None,
) -> list[SourceRef]:
    out: list[SourceRef] = []

    if document_link_map is None:
        ids: list[int] = []
        for s in raw_sources or []:
            if isinstance(s, dict):
                try:
                    ids.append(int(s.get("document_id") or 0))
                except Exception:
                    pass
        document_link_map = _fetch_document_link_map(ids, request=request)

    for s in raw_sources or []:
        if not isinstance(s, dict):
            continue

        try:
            document_id = int(s.get("document_id") or 0)
        except Exception:
            document_id = 0

        link_meta = document_link_map.get(document_id, {})

        try:
            chunk_index = int(s.get("chunk_index") or 0)
        except Exception:
            chunk_index = 0

        try:
            distance = float(s.get("distance") or 0.0)
        except Exception:
            distance = 0.0

        out.append(
            SourceRef(
                doc_type=str(s.get("doc_type") or ""),
                filename=str(s.get("filename") or ""),
                page_ref=str(s.get("page_ref") or ""),
                document_id=document_id,
                chunk_index=chunk_index,
                distance=distance,
                source_url=link_meta.get("source_url"),
                filepath=link_meta.get("filepath"),
                url=link_meta.get("url"),
            )
        )

    return out


def _to_detail_payload_from_rag(item: Any, *, request: Request) -> DetailPayload:
    def _dump(x: Any) -> dict[str, Any]:
        if x is None:
            return {}
        if isinstance(x, dict):
            return x
        if hasattr(x, "model_dump"):
            return x.model_dump()
        if hasattr(x, "__dict__"):
            return dict(x.__dict__)
        return {}

    raw_top_sources = [_dump(s) for s in (item.sources or [])]
    raw_program_requirements = [_dump(c) for c in (item.program_requirements or [])]
    raw_risks = [_dump(r) for r in (item.risks or [])]

    document_ids: list[int] = []

    def _collect_ids(raw_source_list: list[dict[str, Any]]) -> None:
        for s in raw_source_list:
            try:
                did = int(s.get("document_id") or 0)
            except Exception:
                did = 0
            if did > 0:
                document_ids.append(did)

    _collect_ids(raw_top_sources)

    for c in raw_program_requirements:
        _collect_ids(list(c.get("source_refs") or []))

    for r in raw_risks:
        _collect_ids(list(r.get("source_refs") or []))

    link_map = _fetch_document_link_map(document_ids, request=request)

    sources = _to_source_ref_list(raw_top_sources, request=request, document_link_map=link_map)

    program_requirements: list[ChecklistItem] = []
    for c in raw_program_requirements:
        program_requirements.append(
            ChecklistItem(
                item=str(c.get("item") or ""),
                criticality=str(c.get("criticality") or "low"),
                source_refs=_to_source_ref_list(
                    c.get("source_refs") or [],
                    request=request,
                    document_link_map=link_map,
                ),
            )
        )

    risks: list[RiskItem] = []
    for r in raw_risks:
        risks.append(
            RiskItem(
                risk=str(r.get("risk") or ""),
                criticality=str(r.get("criticality") or "low"),
                source_refs=_to_source_ref_list(
                    r.get("source_refs") or [],
                    request=request,
                    document_link_map=link_map,
                ),
            )
        )

    return DetailPayload(
        summary=str(item.summary or ""),
        program_requirements=program_requirements,
        typical_risks=risks,
        sources=sources,
        disclaimer=(
            "Diese Auswertung dient der strukturierten Vorqualifizierung. "
            "Sie basiert auf hinterlegten Regeln und quellengebundenen Dokumenten, "
            "ersetzt aber keine abschließende Prüfung durch die zuständige Förderstelle."
        ),
    )


def _program_result_from_scored(scored: dict[str, Any], *, detail: Optional[DetailPayload]) -> ProgramResult:
    program_id = str(scored.get("program_id") or "")
    name_meta = _fetch_program_names(program_id)
    hard_fail = bool(scored.get("hard_fail"))
    missing_fields = list(scored.get("missing_fields") or [])
    rules = list(scored.get("rules") or [])
    hard_fail_reasons = list(scored.get("hard_fail_reasons") or [])

    status, badge = _status_and_badge(hard_fail=hard_fail, missing_fields=missing_fields)

    next_actions: list[str] = []
    if hard_fail:
        if hard_fail_reasons:
            next_actions.append(f"Blocker beheben: {hard_fail_reasons[0]}")
        next_actions.append("Prüfen, ob der Vorhabensbeginn korrekt ist und keine irreversiblen Verpflichtungen eingegangen wurden.")
    next_actions.extend(_next_actions_from_missing(missing_fields))

    deduped: list[str] = []
    seen: set[str] = set()
    for action in next_actions:
        if action not in seen:
            seen.add(action)
            deduped.append(action)

    if not deduped:
        deduped = _default_next_actions_for_program(str(scored.get("program_id") or ""))

    return ProgramResult(
        program_id=program_id,
        program_name=name_meta["program_name"],
        program_name_official=name_meta["program_name_official"],
        total_score=int(scored.get("total_score") or 0),
        effective_total_score=int(
            scored.get("effective_total_score")
            if scored.get("effective_total_score") is not None
            else (scored.get("total_score") or 0)
        ),
        rule_score=int(scored.get("rule_score") or 0),
        semantic_score=int(scored.get("semantic_score") or 0),
        hard_fail=hard_fail,
        hard_fail_reasons=hard_fail_reasons,
        blocked_label=_blocked_label(hard_fail, hard_fail_reasons),
        missing_fields=missing_fields,
        rules=rules,
        status=status,
        badge=badge,
        next_actions=deduped,
        hard_fail_explain=_hard_fail_explain(rules, hard_fail_reasons),
        rule_engine_note=scored.get("rule_engine_note"),
        retrieval_note=scored.get("retrieval_note"),
        scoring_spec=scored.get("scoring_spec"),
        detail=detail,
    )


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "FörderMatch AI API",
        "version": app.version,
        "endpoints": {
            "health": "GET /health",
            "evaluate": "POST /evaluate",
            "detail": "POST /detail",
            "rank": "POST /rank",
            "document_file": "GET /documents/{document_id}/file",
            "docs": "GET /docs",
        },
    }


@app.get("/health")
def health() -> dict[str, Any]:
    db_exists = DB.exists()
    chroma_exists = CHROMA_DIR.exists()

    status = "ok" if (db_exists and chroma_exists) else "error"

    return {
        "status": status,
        "db_exists": db_exists,
        "chroma_exists": chroma_exists,
        "db_path": str(DB),
        "chroma_dir": str(CHROMA_DIR),
    }


@app.get("/documents/{document_id}/file", name="open_document_file")
def open_document_file(document_id: int):
    _ensure_backend_ready()

    with connect(DB) as conn:
        row = conn.execute(
            "SELECT id, filename, filepath FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown document_id: {document_id}")

    rel_path = str(row["filepath"] or "").strip()
    if not rel_path:
        raise HTTPException(status_code=404, detail=f"No filepath stored for document_id: {document_id}")

    file_path = (ROOT / rel_path).resolve()

    try:
        file_path.relative_to(ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid document path outside project root: {rel_path}")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Document file not found: {rel_path}")

    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=file_path,
        filename=str(row["filename"] or file_path.name),
        media_type=media_type or "application/octet-stream",
    )


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


@app.post("/evaluate")
def evaluate(req: EvaluateRequest) -> dict[str, Any]:
    _ensure_program_exists(req.program_id)
    rk = _clamp_int(req.retrieval_k, 1, 10)
    return score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id=req.program_id,
        profile=req.profile,
        query_text=req.query_text,
        cfg=ScoreConfig(retrieval_k=int(rk)),
    )


@app.post("/detail", response_model=ProgramResult)
def detail(req: DetailRequest, request: Request) -> ProgramResult:
    _ensure_program_exists(req.program_id)
    rk = _clamp_int(req.retrieval_k, 1, 10)

    scored = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id=req.program_id,
        profile=req.profile,
        query_text=req.query_text,
        cfg=ScoreConfig(retrieval_k=int(rk)),
    )

    retrieved = scored.get("retrieval", {}).get("top_k", []) or []
    rag_item = build_grounded_detail_from_chunks(program_id=req.program_id, retrieved=retrieved)
    rag_item2 = validate_grounded_output(rag_item, retrieved_sources=rag_item.sources)
    detail_payload = _to_detail_payload_from_rag(rag_item2, request=request)
    return _program_result_from_scored(scored, detail=detail_payload)


@app.post("/rank", response_model=RankResponse)
def rank(req: RankRequest, request: Request) -> RankResponse:
    _ensure_backend_ready()

    rk = _clamp_int(req.retrieval_k, 1, 10)
    limit = _clamp_int(req.limit, 1, 20)
    include_n = _clamp_int(req.include_detail_top_n, 0, 5)

    all_ids = fetch_all_program_ids(DB)
    all_ids_set = set(all_ids)

    if req.program_ids:
        unknown = [p for p in req.program_ids if p not in all_ids_set]
        if unknown:
            raise HTTPException(status_code=404, detail=f"Unknown program_id(s): {unknown}")
        program_ids = req.program_ids
    else:
        program_ids = all_ids

    cfg = ScoreConfig(retrieval_k=int(rk))
    scored_items: list[dict[str, Any]] = []
    for pid in program_ids:
        scored_items.append(
            score_program(
                db_path=DB,
                chroma_dir=CHROMA_DIR,
                program_id=pid,
                profile=req.profile,
                query_text=req.query_text,
                cfg=cfg,
            )
        )

    def _sort_key(x: dict[str, Any]) -> tuple[int, int, int, str]:
        hf = 1 if bool(x.get("hard_fail")) else 0
        eff = int(
            x.get("effective_total_score")
            if x.get("effective_total_score") is not None
            else (x.get("total_score") or 0)
        )
        total = int(x.get("total_score") or 0)
        pid = str(x.get("program_id") or "")
        return (hf, -eff, -total, pid)

    scored_items.sort(key=_sort_key)

    results: list[ProgramResult] = []
    for i, scored in enumerate(scored_items[:limit]):
        detail_payload: Optional[DetailPayload] = None
        if include_n > 0 and i < include_n:
            retrieved = scored.get("retrieval", {}).get("top_k", []) or []
            rag_item = build_grounded_detail_from_chunks(program_id=str(scored.get("program_id") or ""), retrieved=retrieved)
            rag_item2 = validate_grounded_output(rag_item, retrieved_sources=rag_item.sources)
            detail_payload = _to_detail_payload_from_rag(rag_item2, request=request)
        results.append(_program_result_from_scored(scored, detail=detail_payload))

    return RankResponse(
        query_text=req.query_text,
        retrieval_k=int(rk),
        limit=int(limit),
        include_detail_top_n=int(include_n),
        results=results,
    )