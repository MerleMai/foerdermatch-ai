# scripts/smoke_api.py
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


BASE_URL = "http://127.0.0.1:8000"
HTTP_TIMEOUT_SECONDS = 45


def _http_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = BASE_URL + path
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTPError {e.code} {e.reason}: {raw}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URLError: {e}") from e
    except TimeoutError as e:
        raise RuntimeError(f"TimeoutError: timed out after {HTTP_TIMEOUT_SECONDS}s for {method} {path}") from e


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    profile_a = root / "data" / "profiles" / "profile_a.json"
    profile_a_started = root / "data" / "profiles" / "profile_a_started.json"
    profile_grw = root / "data" / "profiles" / "profile_grw_mv_invest_kmu.json"
    profile_go_inno = root / "data" / "profiles" / "profile_go_inno_kmu.json"

    print("[SMOKE] health")
    health = _http_json("GET", "/health")
    _assert(health.get("status") == "ok", f"/health unexpected: {health}")
    print("  OK")

    print("[SMOKE] rank (profile_a)")
    prof = json.loads(profile_a.read_text(encoding="utf-8"))
    rank = _http_json(
        "POST",
        "/rank",
        {
            "query_text": "Digitalisierung Vorhabensbeginn De-minimis",
            "profile": prof,
            "program_ids": [
                "KFW-ERP-DIGI-511",
                "KFW-ERP-DIGI-512",
                "ZIM",
                "KMU-INNOVATIV",
            ],
            "limit": 5,
            "include_detail_top_n": 1,
            "retrieval_k": 5,
        },
    )
    _assert("results" in rank and isinstance(rank["results"], list) and rank["results"], "/rank results empty")
    top = rank["results"][0]
    _assert(top.get("program_id"), "top missing program_id")
    _assert(top.get("status") in ("eligible", "maybe", "blocked"), f"invalid status: {top.get('status')}")
    _assert(top.get("detail") is not None, "expected detail for top result (include_detail_top_n=1)")
    _assert(len(top["detail"].get("sources") or []) >= 1, "expected detail.sources non-empty")
    print(f"  OK top={top.get('program_id')} status={top.get('status')}")

    print("[SMOKE] detail (profile_a)")
    det = _http_json(
        "POST",
        "/detail",
        {
            "program_id": top["program_id"],
            "query_text": "Digitalisierung",
            "profile": prof,
            "retrieval_k": 5,
        },
    )
    _assert(det.get("program_id") == top["program_id"], "detail program_id mismatch")
    _assert("detail" in det and det["detail"] is not None, "detail payload missing")
    _assert(len(det["detail"].get("sources") or []) >= 1, "detail.sources should be non-empty")
    print("  OK")

    print("[SMOKE] rank (profile_a_started) -> should be blocked")
    prof2 = json.loads(profile_a_started.read_text(encoding="utf-8"))
    rank2 = _http_json(
        "POST",
        "/rank",
        {
            "query_text": "Vorhabensbeginn Antrag",
            "profile": prof2,
            "program_ids": [
                "KFW-ERP-DIGI-511",
                "KFW-ERP-DIGI-512",
                "ZIM",
                "KMU-INNOVATIV",
                "EEW-BAFA-M1",
                "EEW-BAFA-M2",
                "EEW-BAFA-M3",
                "EEW-BAFA-M4-BASIS",
                "EEW-BAFA-M4-PREMIUM",
            ],
            "limit": 5,
            "include_detail_top_n": 0,
            "retrieval_k": 5,
        },
    )
    _assert(rank2.get("results"), "rank2 results empty")
    any_blocked = any(r.get("status") == "blocked" for r in rank2["results"])
    _assert(any_blocked, "expected at least one blocked result for started profile")
    print("  OK (blocked present)")

    print("[SMOKE] targeted rank for KMU-INNOVATIV")
    rank3 = _http_json(
        "POST",
        "/rank",
        {
            "query_text": "Forschung Entwicklung Wertschöpfung Produktion Dienstleistung Robotik",
            "profile": prof,
            "program_ids": [
                "KMU-INNOVATIV",
                "ZIM",
                "KFW-ERP-DIGI-511",
                "KFW-ERP-DIGI-512",
            ],
            "limit": 4,
            "include_detail_top_n": 1,
            "retrieval_k": 5,
        },
    )
    _assert(rank3.get("results"), "rank3 results empty")
    ids = [r.get("program_id") for r in rank3["results"]]
    _assert("KMU-INNOVATIV" in ids, "expected KMU-INNOVATIV in rank results")
    print("  OK (KMU-INNOVATIV present)")

    print("[SMOKE] detail for KMU-INNOVATIV")
    det2 = _http_json(
        "POST",
        "/detail",
        {
            "program_id": "KMU-INNOVATIV",
            "query_text": "15. April 15. Oktober 1000 Beschäftigte 100 Millionen Euro",
            "profile": prof,
            "retrieval_k": 5,
        },
    )
    _assert(det2.get("program_id") == "KMU-INNOVATIV", "detail program_id mismatch for KMU-INNOVATIV")
    _assert("detail" in det2 and det2["detail"] is not None, "detail payload missing for KMU-INNOVATIV")
    _assert(len(det2["detail"].get("sources") or []) >= 1, "expected KMU-INNOVATIV detail.sources non-empty")
    print("  OK")

    print("[SMOKE] targeted rank for EEW family")
    rank4 = _http_json(
        "POST",
        "/rank",
        {
            "query_text": "Energieeffizienz Prozesswärme Energiemanagement Sensorik THG Einsparung",
            "profile": prof,
            "program_ids": [
                "EEW-BAFA-M1",
                "EEW-BAFA-M2",
                "EEW-BAFA-M3",
                "EEW-BAFA-M4-BASIS",
                "EEW-BAFA-M4-PREMIUM",
            ],
            "limit": 5,
            "include_detail_top_n": 0,
            "retrieval_k": 5,
        },
    )
    _assert(rank4.get("results"), "rank4 results empty")
    ids4 = [r.get("program_id") for r in rank4["results"]]
    _assert(any(pid and pid.startswith("EEW-BAFA-") for pid in ids4), "expected at least one EEW result in rank4")
    print("  OK (EEW present)")

    print("[SMOKE] detail for EEW-BAFA-M3")
    det3 = _http_json(
        "POST",
        "/detail",
        {
            "program_id": "EEW-BAFA-M3",
            "query_text": "gelistete Energiemanagementsoftware Sensorik MSR 3 Jahre Speicherung",
            "profile": prof,
            "retrieval_k": 5,
        },
    )
    _assert(det3.get("program_id") == "EEW-BAFA-M3", "detail program_id mismatch for EEW-BAFA-M3")
    _assert("detail" in det3 and det3["detail"] is not None, "detail payload missing for EEW-BAFA-M3")
    _assert(len(det3["detail"].get("sources") or []) >= 1, "expected EEW-BAFA-M3 detail.sources non-empty")
    print("  OK")

    print("[SMOKE] detail for EEW-BAFA-M4-PREMIUM")
    det4 = _http_json(
        "POST",
        "/detail",
        {
            "program_id": "EEW-BAFA-M4-PREMIUM",
            "query_text": "THG Einsparpotenzial Einsparkonzept Premiumförderung",
            "profile": prof,
            "retrieval_k": 5,
        },
    )
    _assert(det4.get("program_id") == "EEW-BAFA-M4-PREMIUM", "detail program_id mismatch for EEW-BAFA-M4-PREMIUM")
    _assert("detail" in det4 and det4["detail"] is not None, "detail payload missing for EEW-BAFA-M4-PREMIUM")
    _assert(len(det4["detail"].get("sources") or []) >= 1, "expected EEW-BAFA-M4-PREMIUM detail.sources non-empty")
    print("  OK")

    print("[SMOKE] targeted rank for GRW")
    prof_grw = json.loads(profile_grw.read_text(encoding="utf-8"))
    rank5 = _http_json(
        "POST",
        "/rank",
        {
            "query_text": "Regionalförderung Investition Arbeitsplätze Produktionsstätte Primäreffekt",
            "profile": prof_grw,
            "program_ids": ["GRW-MV-GEWERBE"],
            "limit": 1,
            "include_detail_top_n": 1,
            "retrieval_k": 5,
        },
    )
    _assert(rank5.get("results"), "rank5 results empty")
    ids5 = [r.get("program_id") for r in rank5["results"]]
    _assert("GRW-MV-GEWERBE" in ids5, "expected GRW-MV-GEWERBE in rank results")
    print("  OK (GRW present)")

    print("[SMOKE] detail for GRW-MV-GEWERBE")
    det5 = _http_json(
        "POST",
        "/detail",
        {
            "program_id": "GRW-MV-GEWERBE",
            "query_text": "Primäreffekt überregional Vorhabensbeginn Fördergebiet Arbeitsplätze",
            "profile": prof_grw,
            "retrieval_k": 5,
        },
    )
    _assert(det5.get("program_id") == "GRW-MV-GEWERBE", "detail program_id mismatch for GRW-MV-GEWERBE")
    _assert("detail" in det5 and det5["detail"] is not None, "detail payload missing for GRW-MV-GEWERBE")
    _assert(len(det5["detail"].get("sources") or []) >= 1, "expected GRW-MV-GEWERBE detail.sources non-empty")
    print("  OK")

    print("[SMOKE] targeted rank for GO-INNO")
    prof_go = json.loads(profile_go_inno.read_text(encoding="utf-8"))
    rank6 = _http_json(
        "POST",
        "/rank",
        {
            "query_text": "Innovationsberatung Produktinnovation Verfahrensinnovation autorisierte Beratungsunternehmen",
            "profile": prof_go,
            "program_ids": ["GO-INNO"],
            "limit": 1,
            "include_detail_top_n": 1,
            "retrieval_k": 5,
        },
    )
    _assert(rank6.get("results"), "rank6 results empty")
    ids6 = [r.get("program_id") for r in rank6["results"]]
    _assert("GO-INNO" in ids6, "expected GO-INNO in rank results")
    print("  OK (GO-INNO present)")

    print("[SMOKE] detail for GO-INNO")
    det6 = _http_json(
        "POST",
        "/detail",
        {
            "program_id": "GO-INNO",
            "query_text": "100 Beschäftigte 20 Millionen Euro Beratungsunternehmen Produktinnovation Verfahrensinnovation",
            "profile": prof_go,
            "retrieval_k": 5,
        },
    )
    _assert(det6.get("program_id") == "GO-INNO", "detail program_id mismatch for GO-INNO")
    _assert("detail" in det6 and det6["detail"] is not None, "detail payload missing for GO-INNO")
    _assert(len(det6["detail"].get("sources") or []) >= 1, "expected GO-INNO detail.sources non-empty")
    print("  OK")

    print("[SMOKE] DONE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"[SMOKE] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        raise