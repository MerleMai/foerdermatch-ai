from __future__ import annotations

from backend.config import require_env
require_env("OPENAI_API_KEY")

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.services.scoring_service import ScoreConfig, score_program
from backend.services.rag_service import build_grounded_detail_from_chunks, validate_grounded_output


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "programs.db"
CHROMA_DIR = ROOT / "data" / "chroma"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rank(program_ids: list[str], profile: dict[str, Any], query: str) -> list[dict[str, Any]]:
    out = []
    for pid in program_ids:
        res = score_program(
            db_path=DB,
            chroma_dir=CHROMA_DIR,
            program_id=pid,
            profile=profile,
            query_text=query,
            cfg=ScoreConfig(retrieval_k=5, hard_fail_policy="push_to_bottom"),
        )
        out.append(res)

    out.sort(
        key=lambda x: (
            int(x.get("effective_total_score", 0)),
            int(x.get("total_score", 0)),
        ),
        reverse=True,
    )
    return out


def main() -> int:
    checks: list[Check] = []

    checks.append(Check("DB exists", DB.exists(), str(DB)))
    checks.append(Check("CHROMA_DIR exists", CHROMA_DIR.exists(), str(CHROMA_DIR)))

    if not DB.exists() or not CHROMA_DIR.exists():
        for c in checks:
            print(f"[{'OK' if c.ok else 'FAIL'}] {c.name}: {c.detail}")
        return 1

    p_a = ROOT / "data" / "profiles" / "profile_a.json"
    p_b = ROOT / "data" / "profiles" / "profile_b.json"
    p_c = ROOT / "data" / "profiles" / "profile_c.json"
    p_a_started = ROOT / "data" / "profiles" / "profile_a_started.json"

    p_eew_m1 = ROOT / "data" / "profiles" / "profile_eew_m1_kmu_anlagenaustausch.json"
    p_eew_m3 = ROOT / "data" / "profiles" / "profile_eew_m3_energiemanagement.json"
    p_eew_m4p = ROOT / "data" / "profiles" / "profile_eew_m4_premium_prozessoptimierung.json"

    p_grw_mv = ROOT / "data" / "profiles" / "profile_grw_mv_invest_kmu.json"
    p_grw_mv_started = ROOT / "data" / "profiles" / "profile_grw_mv_started.json"

    p_go_inno = ROOT / "data" / "profiles" / "profile_go_inno_kmu.json"
    p_go_inno_started = ROOT / "data" / "profiles" / "profile_go_inno_started.json"

    for p in [
        p_a, p_b, p_c, p_a_started,
        p_eew_m1, p_eew_m3, p_eew_m4p,
        p_grw_mv, p_grw_mv_started,
        p_go_inno, p_go_inno_started,
    ]:
        checks.append(Check(f"profile exists: {p.name}", p.exists(), str(p)))

    if any((not c.ok) for c in checks if c.name.startswith("profile exists")):
        for c in checks:
            print(f"[{'OK' if c.ok else 'FAIL'}] {c.name}: {c.detail}")
        return 1

    prof_a = _load_json(p_a)
    prof_b = _load_json(p_b)
    prof_c = _load_json(p_c)
    prof_a_started = _load_json(p_a_started)

    prof_eew_m1 = _load_json(p_eew_m1)
    prof_eew_m3 = _load_json(p_eew_m3)
    prof_eew_m4p = _load_json(p_eew_m4p)

    prof_grw_mv = _load_json(p_grw_mv)
    prof_grw_mv_started = _load_json(p_grw_mv_started)

    prof_go_inno = _load_json(p_go_inno)
    prof_go_inno_started = _load_json(p_go_inno_started)

    core_program_ids = ["KFW-ERP-DIGI-511", "KFW-ERP-DIGI-512", "ZIM", "KMU-INNOVATIV"]
    eew_program_ids = [
        "EEW-BAFA-M1",
        "EEW-BAFA-M2",
        "EEW-BAFA-M3",
        "EEW-BAFA-M4-BASIS",
        "EEW-BAFA-M4-PREMIUM",
    ]
    grw_program_ids = ["GRW-MV-GEWERBE"]
    go_inno_program_ids = ["GO-INNO"]

    rank_a = _rank(core_program_ids, prof_a, "Digitalisierung Vorhabensbeginn De-minimis")
    ok = all((len(x.get("rules") or []) > 0) for x in rank_a)
    checks.append(Check("A: rules non-empty for all", ok, f"top={rank_a[0]['program_id']}"))

    ok = all((len((x.get("retrieval") or {}).get("top_k") or []) > 0) for x in rank_a)
    checks.append(Check("A: retrieval non-empty for all", ok, f"top={rank_a[0]['program_id']}"))

    rank_started = _rank(core_program_ids, prof_a_started, "Vorhabensbeginn Antrag")
    hf = [bool(x.get("hard_fail")) for x in rank_started]
    checks.append(Check("STARTED: hard_fail present", any(hf), f"hard_fail_flags={hf}"))

    ok = True
    for x in rank_started:
        if x.get("hard_fail") is True and int(x.get("effective_total_score", 0)) != -1:
            ok = False
            break
    checks.append(
        Check(
            "STARTED: push_to_bottom effective_total_score=-1",
            ok,
            f"top_effective={rank_started[0].get('effective_total_score')}",
        )
    )

    r1 = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="KFW-ERP-DIGI-511",
        profile=prof_a,
        query_text="Digitalisierung",
        cfg=ScoreConfig(retrieval_k=5),
    )
    r2 = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="KFW-ERP-DIGI-511",
        profile=prof_a,
        query_text="Digitalisierung",
        cfg=ScoreConfig(retrieval_k=5),
    )
    ok = (
        (r1.get("total_score") == r2.get("total_score"))
        and (r1.get("rule_score") == r2.get("rule_score"))
        and (r1.get("semantic_score") == r2.get("semantic_score"))
    )
    checks.append(Check("Determinism: 2x same score", ok, f"{r1.get('total_score')} vs {r2.get('total_score')}"))

    retrieved = (r1.get("retrieval") or {}).get("top_k") or []
    detail = build_grounded_detail_from_chunks(program_id="KFW-ERP-DIGI-511", retrieved=retrieved)
    detail2 = validate_grounded_output(detail, retrieved_sources=detail.sources)

    ok = (len(detail2.sources) > 0)
    checks.append(Check("RAG: sources non-empty", ok, f"sources={len(detail2.sources)}"))

    ok = all((len(ci.source_refs) > 0) for ci in (detail2.program_requirements or []))
    checks.append(Check("RAG: program_requirements items source-bound", ok, f"program_requirements={len(detail2.program_requirements)}"))

    ok = all((len(ri.source_refs) > 0) for ri in (detail2.risks or []))
    checks.append(Check("RAG: risk items source-bound", ok, f"risks={len(detail2.risks)}"))

    r_kmu = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="KMU-INNOVATIV",
        profile=prof_a,
        query_text="Forschung Entwicklung Wertschöpfung Robotik 15. April 15. Oktober",
        cfg=ScoreConfig(retrieval_k=5),
    )

    ok = len(r_kmu.get("rules") or []) > 0
    checks.append(Check("KMU-I: rules non-empty", ok, f"rule_count={len(r_kmu.get('rules') or [])}"))

    ok = len((r_kmu.get("retrieval") or {}).get("top_k") or []) > 0
    checks.append(
        Check(
            "KMU-I: retrieval non-empty",
            ok,
            f"retrieved={len((r_kmu.get('retrieval') or {}).get('top_k') or [])}",
        )
    )

    retrieved_kmu = (r_kmu.get("retrieval") or {}).get("top_k") or []
    detail_kmu = build_grounded_detail_from_chunks(program_id="KMU-INNOVATIV", retrieved=retrieved_kmu)
    detail_kmu_2 = validate_grounded_output(detail_kmu, retrieved_sources=detail_kmu.sources)

    ok = len(detail_kmu_2.sources) > 0
    checks.append(Check("KMU-I: sources non-empty", ok, f"sources={len(detail_kmu_2.sources)}"))

    ok = all((len(ci.source_refs) > 0) for ci in (detail_kmu_2.program_requirements or []))
    checks.append(
        Check(
            "KMU-I: program_requirements items source-bound",
            ok,
            f"program_requirements={len(detail_kmu_2.program_requirements)}",
        )
    )

    r_eew_m3 = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="EEW-BAFA-M3",
        profile=prof_a,
        query_text="Energiemanagement Software Sensorik MSR ISO 50001",
        cfg=ScoreConfig(retrieval_k=5),
    )
    checks.append(
        Check(
            "EEW-M3: rules non-empty",
            len(r_eew_m3.get("rules") or []) > 0,
            f"rule_count={len(r_eew_m3.get('rules') or [])}",
        )
    )
    checks.append(
        Check(
            "EEW-M3: retrieval non-empty",
            len((r_eew_m3.get("retrieval") or {}).get("top_k") or []) > 0,
            f"retrieved={len((r_eew_m3.get('retrieval') or {}).get('top_k') or [])}",
        )
    )

    retrieved_eew_m3 = (r_eew_m3.get("retrieval") or {}).get("top_k") or []
    detail_eew_m3 = build_grounded_detail_from_chunks(program_id="EEW-BAFA-M3", retrieved=retrieved_eew_m3)
    detail_eew_m3_2 = validate_grounded_output(detail_eew_m3, retrieved_sources=detail_eew_m3.sources)
    checks.append(
        Check(
            "EEW-M3: sources non-empty",
            len(detail_eew_m3_2.sources) > 0,
            f"sources={len(detail_eew_m3_2.sources)}",
        )
    )

    checks.append(
        Check(
            "EEW-M3: program_requirements items source-bound",
            all((len(ci.source_refs) > 0) for ci in (detail_eew_m3_2.program_requirements or [])),
            f"program_requirements={len(detail_eew_m3_2.program_requirements)}",
        )
    )

    r_eew_m4_basis = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="EEW-BAFA-M4-BASIS",
        profile=prof_a,
        query_text="KMU Anlagenaustausch 15 Prozent Endenergieeinsparung",
        cfg=ScoreConfig(retrieval_k=5),
    )
    checks.append(
        Check(
            "EEW-M4-BASIS: retrieval non-empty",
            len((r_eew_m4_basis.get("retrieval") or {}).get("top_k") or []) > 0,
            f"retrieved={len((r_eew_m4_basis.get('retrieval') or {}).get('top_k') or [])}",
        )
    )

    r_eew_m4_premium = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="EEW-BAFA-M4-PREMIUM",
        profile=prof_a,
        query_text="THG Einsparpotenzial Einsparkonzept Prozessoptimierung Dekarbonisierung",
        cfg=ScoreConfig(retrieval_k=5),
    )
    checks.append(
        Check(
            "EEW-M4-PREMIUM: retrieval non-empty",
            len((r_eew_m4_premium.get("retrieval") or {}).get("top_k") or []) > 0,
            f"retrieved={len((r_eew_m4_premium.get('retrieval') or {}).get('top_k') or [])}",
        )
    )

    rank_eew_started = _rank(eew_program_ids, prof_a_started, "Vorhabensbeginn Energieeffizienz Antrag")
    hf_eew = [bool(x.get("hard_fail")) for x in rank_eew_started]
    checks.append(Check("EEW STARTED: hard_fail present", any(hf_eew), f"hard_fail_flags={hf_eew}"))

    ok = True
    for x in rank_eew_started:
        if x.get("hard_fail") is True and int(x.get("effective_total_score", 0)) != -1:
            ok = False
            break
    checks.append(
        Check(
            "EEW STARTED: push_to_bottom effective_total_score=-1",
            ok,
            f"top_effective={rank_eew_started[0].get('effective_total_score') if rank_eew_started else 'n/a'}",
        )
    )

    rank_eew_m1 = _rank(
        ["EEW-BAFA-M1", "EEW-BAFA-M4-BASIS", "EEW-BAFA-M3", "EEW-BAFA-M2", "EEW-BAFA-M4-PREMIUM"],
        prof_eew_m1,
        "Energieeffizienz Austausch Bestandsanlage Querschnittstechnologie Abwärme Wärmedämmung",
    )
    top3_m1 = [x["program_id"] for x in rank_eew_m1[:3]]
    top2_m1 = [x["program_id"] for x in rank_eew_m1[:2]]

    checks.append(
        Check(
            "EEW-M1 ranking: EEW-BAFA-M1 appears in top 3",
            "EEW-BAFA-M1" in top3_m1,
            f"top3={top3_m1}",
        )
    )
    checks.append(
        Check(
            "EEW-M1 ranking: top 2 contains M1 or M4-BASIS",
            any(pid in {"EEW-BAFA-M1", "EEW-BAFA-M4-BASIS"} for pid in top2_m1),
            f"top2={top2_m1}",
        )
    )

    rank_eew_m3 = _rank(
        ["EEW-BAFA-M3", "EEW-BAFA-M1", "EEW-BAFA-M2", "EEW-BAFA-M4-BASIS", "EEW-BAFA-M4-PREMIUM"],
        prof_eew_m3,
        "Energiemanagementsoftware Sensorik MSR Datenerfassung ISO 50001",
    )
    checks.append(
        Check(
            "EEW-M3 ranking: top is EEW-BAFA-M3",
            rank_eew_m3[0]["program_id"] == "EEW-BAFA-M3",
            f"top={rank_eew_m3[0]['program_id']}",
        )
    )

    rank_eew_m4p = _rank(
        ["EEW-BAFA-M4-PREMIUM", "EEW-BAFA-M4-BASIS", "EEW-BAFA-M2", "EEW-BAFA-M3", "EEW-BAFA-M1"],
        prof_eew_m4p,
        "Prozessoptimierung THG Einsparpotenzial Einsparkonzept Dekarbonisierung Ressourceneffizienz",
    )
    checks.append(
        Check(
            "EEW-M4-PREMIUM ranking: top is EEW-BAFA-M4-PREMIUM",
            rank_eew_m4p[0]["program_id"] == "EEW-BAFA-M4-PREMIUM",
            f"top={rank_eew_m4p[0]['program_id']}",
        )
    )

    r_grw = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="GRW-MV-GEWERBE",
        profile=prof_grw_mv,
        query_text="Regionalförderung Investition Arbeitsplätze Produktionsstätte Primäreffekt",
        cfg=ScoreConfig(retrieval_k=5),
    )
    checks.append(
        Check(
            "GRW: rules non-empty",
            len(r_grw.get("rules") or []) > 0,
            f"rule_count={len(r_grw.get('rules') or [])}",
        )
    )
    checks.append(
        Check(
            "GRW: retrieval non-empty",
            len((r_grw.get("retrieval") or {}).get("top_k") or []) > 0,
            f"retrieved={len((r_grw.get('retrieval') or {}).get('top_k') or [])}",
        )
    )

    retrieved_grw = (r_grw.get("retrieval") or {}).get("top_k") or []
    detail_grw = build_grounded_detail_from_chunks(program_id="GRW-MV-GEWERBE", retrieved=retrieved_grw)
    detail_grw_2 = validate_grounded_output(detail_grw, retrieved_sources=detail_grw.sources)
    checks.append(
        Check(
            "GRW: sources non-empty",
            len(detail_grw_2.sources) > 0,
            f"sources={len(detail_grw_2.sources)}",
        )
    )

    checks.append(
        Check(
            "GRW: program_requirements items source-bound",
            all((len(ci.source_refs) > 0) for ci in (detail_grw_2.program_requirements or [])),
            f"program_requirements={len(detail_grw_2.program_requirements)}",
        )
    )

    rank_grw_started = _rank(grw_program_ids, prof_grw_mv_started, "Vorhabensbeginn Regionalförderung Antrag")
    hf_grw = [bool(x.get("hard_fail")) for x in rank_grw_started]
    checks.append(Check("GRW STARTED: hard_fail present", any(hf_grw), f"hard_fail_flags={hf_grw}"))

    ok = True
    for x in rank_grw_started:
        if x.get("hard_fail") is True and int(x.get("effective_total_score", 0)) != -1:
            ok = False
            break
    checks.append(
        Check(
            "GRW STARTED: push_to_bottom effective_total_score=-1",
            ok,
            f"top_effective={rank_grw_started[0].get('effective_total_score') if rank_grw_started else 'n/a'}",
        )
    )

    rank_grw = _rank(
        ["GRW-MV-GEWERBE", "EEW-BAFA-M4-BASIS", "EEW-BAFA-M1", "KFW-ERP-DIGI-511"],
        prof_grw_mv,
        "Regionalförderung Investition neue Arbeitsplätze Produktionsstätte Primäreffekt",
    )
    checks.append(
        Check(
            "GRW ranking: top is GRW-MV-GEWERBE",
            rank_grw[0]["program_id"] == "GRW-MV-GEWERBE",
            f"top={rank_grw[0]['program_id']}",
        )
    )

    r_go = score_program(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id="GO-INNO",
        profile=prof_go_inno,
        query_text="Innovationsberatung Produktinnovation Verfahrensinnovation autorisierte Beratungsunternehmen",
        cfg=ScoreConfig(retrieval_k=5),
    )
    checks.append(
        Check(
            "GO-INNO: rules non-empty",
            len(r_go.get("rules") or []) > 0,
            f"rule_count={len(r_go.get('rules') or [])}",
        )
    )
    checks.append(
        Check(
            "GO-INNO: retrieval non-empty",
            len((r_go.get("retrieval") or {}).get("top_k") or []) > 0,
            f"retrieved={len((r_go.get('retrieval') or {}).get('top_k') or [])}",
        )
    )

    retrieved_go = (r_go.get("retrieval") or {}).get("top_k") or []
    detail_go = build_grounded_detail_from_chunks(program_id="GO-INNO", retrieved=retrieved_go)
    detail_go_2 = validate_grounded_output(detail_go, retrieved_sources=detail_go.sources)
    checks.append(
        Check(
            "GO-INNO: sources non-empty",
            len(detail_go_2.sources) > 0,
            f"sources={len(detail_go_2.sources)}",
        )
    )

    checks.append(
        Check(
            "GO-INNO: program_requirements items source-bound",
            all((len(ci.source_refs) > 0) for ci in (detail_go_2.program_requirements or [])),
            f"program_requirements={len(detail_go_2.program_requirements)}",
        )
    )

    rank_go_started = _rank(go_inno_program_ids, prof_go_inno_started, "Vorhabensbeginn Beratung Innovationsgutschein")
    hf_go = [bool(x.get("hard_fail")) for x in rank_go_started]
    checks.append(Check("GO-INNO STARTED: hard_fail present", any(hf_go), f"hard_fail_flags={hf_go}"))

    ok = True
    for x in rank_go_started:
        if x.get("hard_fail") is True and int(x.get("effective_total_score", 0)) != -1:
            ok = False
            break
    checks.append(
        Check(
            "GO-INNO STARTED: push_to_bottom effective_total_score=-1",
            ok,
            f"top_effective={rank_go_started[0].get('effective_total_score') if rank_go_started else 'n/a'}",
        )
    )

    rank_go = _rank(
        ["GO-INNO", "KFW-ERP-DIGI-511", "EEW-BAFA-M3", "KMU-INNOVATIV"],
        prof_go_inno,
        "Innovationsberatung autorisierte Beratungsunternehmen Produktinnovation technische Verfahrensinnovation",
    )
    checks.append(
        Check(
            "GO-INNO ranking: top is GO-INNO",
            rank_go[0]["program_id"] == "GO-INNO",
            f"top={rank_go[0]['program_id']}",
        )
    )

    failed = 0
    for c in checks:
        print(f"[{'OK' if c.ok else 'FAIL'}] {c.name}: {c.detail}")
        if not c.ok:
            failed += 1

    if failed == 0:
        print("[OK] Regression suite passed.")
        return 0

    print(f"[FAIL] Regression suite failed: {failed} checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())