from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.db.repo import connect, init_db
from backend.services.scoring_service import score_program, ScoreConfig

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "programs.db"
SCHEMA = ROOT / "backend" / "db" / "schema.sql"
CHROMA_DIR = ROOT / "data" / "chroma"


def list_active_programs() -> list[str]:
    with connect(DB) as conn:
        rows = conn.execute("SELECT id FROM programs WHERE status='active' ORDER BY id;").fetchall()
    return [r["id"] for r in rows]


def rank(programs: list[str], profile: dict[str, Any], query_text: str) -> list[str]:
    results = []
    for pid in programs:
        res = score_program(
            db_path=DB,
            chroma_dir=CHROMA_DIR,
            program_id=pid,
            profile=profile,
            query_text=query_text,
            cfg=ScoreConfig(retrieval_k=5, hard_fail_policy="push_to_bottom"),
        )
        results.append(res)

    def _sort_key(x: dict[str, Any]) -> tuple[int, int, int, str]:
        hard_fail = 1 if bool(x.get("hard_fail")) else 0
        effective_total = int(x.get("effective_total_score", 0))
        total = int(x.get("total_score", 0))
        pid = str(x.get("program_id", ""))
        return (hard_fail, -effective_total, -total, pid)

    results.sort(key=_sort_key)
    return [r["program_id"] for r in results]


def _resolve_expected_path(arg_value: str | None) -> Path:
    candidates = []
    if arg_value:
        candidates.append(Path(arg_value))
    candidates.extend(
        [
            ROOT / "data" / "expected_rankings.json",
            ROOT / "data" / "expected_ranking.json",
        ]
    )

    for p in candidates:
        if p.exists():
            return p

    raise FileNotFoundError(
        "No expected ranking file found. Checked:\n"
        + "\n".join(f"  - {p}" for p in candidates)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-dir", default=str(ROOT / "data" / "profiles"))
    parser.add_argument("--expected", default=None)
    parser.add_argument(
        "--query",
        default=None,
        help="Fallback query if a case in expected_rankings.json does not define its own query.",
    )
    args = parser.parse_args()

    init_db(DB, SCHEMA)
    all_programs = list_active_programs()

    expected_path = _resolve_expected_path(args.expected)
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    cases = expected.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"Invalid expected ranking file: missing/non-list 'cases' in {expected_path}")

    ok = True

    for case in cases:
        if not isinstance(case, dict):
            ok = False
            print("\n[FAIL] Invalid case (not an object):", case)
            continue

        name = case.get("profile")
        exp = case.get("expected_rank")
        query_text = case.get("query") or args.query
        case_program_ids = case.get("program_ids")

        if not isinstance(name, str) or not name.strip():
            ok = False
            print("\n[FAIL] Case missing valid 'profile':", case)
            continue

        if not isinstance(exp, list) or not all(isinstance(x, str) for x in exp):
            ok = False
            print(f"\n[FAIL] Case for profile '{name}' has invalid 'expected_rank': {exp}")
            continue

        if not isinstance(query_text, str) or not query_text.strip():
            ok = False
            print(f"\n[FAIL] Case for profile '{name}' has no query. Add 'query' in the case or pass --query.")
            continue

        if case_program_ids is None:
            programs = all_programs
        else:
            if not isinstance(case_program_ids, list) or not all(isinstance(x, str) for x in case_program_ids):
                ok = False
                print(f"\n[FAIL] Case for profile '{name}' has invalid 'program_ids': {case_program_ids}")
                continue
            programs = case_program_ids

        prof_path = Path(args.profiles_dir) / f"{name}.json"
        if not prof_path.exists():
            ok = False
            print(f"\n[FAIL] Profile file missing: {prof_path}")
            continue

        profile = json.loads(prof_path.read_text(encoding="utf-8"))
        got = rank(programs, profile, query_text)

        got_prefix = got[: len(exp)]
        if got_prefix != exp:
            ok = False
            print("\n[FAIL] Ranking mismatch")
            print("  profile   :", name)
            print("  query     :", query_text)
            print("  programs  :", programs)
            print("  expected  :", exp)
            print("  got       :", got_prefix)
        else:
            print(f"[PASS] {name}: ranking ok -> {got_prefix}")

    if not ok:
        raise SystemExit(2)

    print(f"\n[OK] Ranking validation passed. expected_file={expected_path}")


if __name__ == "__main__":
    main()