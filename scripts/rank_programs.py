from __future__ import annotations

from backend.config import require_env
require_env("OPENAI_API_KEY")

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.services.scoring_service import ScoreConfig, score_program

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "programs.db"
CHROMA_DIR = ROOT / "data" / "chroma"


def _load_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_program_ids() -> list[str]:
    return [
        "KFW-ERP-DIGI-511",
        "KFW-ERP-DIGI-512",
        "ZIM",
        "KMU-INNOVATIV",
        "EEW-BAFA-M1",
        "EEW-BAFA-M2",
        "EEW-BAFA-M3",
        "EEW-BAFA-M4-BASIS",
        "EEW-BAFA-M4-PREMIUM",
        "GRW-MV-GEWERBE",
        "GO-INNO",
    ]


def _list_program_ids_from_db(db_path: Path) -> list[str]:
    if not db_path.exists():
        return _default_program_ids()

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT id FROM programs WHERE status='active' ORDER BY id;")
        rows = cur.fetchall()
        ids = [r[0] for r in rows]
        return ids if ids else _default_program_ids()
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, type=Path)
    ap.add_argument("--query", required=True, type=str)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--only", type=str, default=None, help="Optional single program_id")
    ap.add_argument("--json", action="store_true", help="Output full ranking JSON")
    args = ap.parse_args()

    profile = _load_profile(args.profile)
    program_ids = _list_program_ids_from_db(DB)

    if args.only:
        program_ids = [args.only]

    results: list[dict[str, Any]] = []
    for pid in program_ids:
        res = score_program(
            db_path=DB,
            chroma_dir=CHROMA_DIR,
            program_id=pid,
            profile=profile,
            query_text=args.query,
            cfg=ScoreConfig(retrieval_k=int(args.k)),
        )
        results.append(res)

    def sort_key(r: dict[str, Any]):
        return (
            int(r.get("hard_fail") is True),
            -int(r.get("effective_total_score", 0)),
            -int(r.get("total_score", 0)),
        )

    results_sorted = sorted(results, key=sort_key)

    if args.json:
        print(json.dumps({"ranking": results_sorted}, ensure_ascii=False, indent=2))
        return 0

    print("\nRanking:")
    for i, r in enumerate(results_sorted, start=1):
        print(
            f" {i:>2}. {r['program_id']:<22} "
            f"total={r['total_score']:>3} (rule={r['rule_score']:>2} sem={r['semantic_score']:>2}) "
            f"hard_fail={r['hard_fail']} effective={r['effective_total_score']:>3}"
        )

    top = results_sorted[0] if results_sorted else None
    if top:
        print("\nTop details (top 1):")
        print(json.dumps(top, ensure_ascii=False, indent=2))

        if not top.get("retrieval", {}).get("top_k"):
            print("\n[DEBUG] retrieval empty. Notes:")
            print("  retrieval_note:", top.get("retrieval_note"))
            print("  CHROMA_DIR:", CHROMA_DIR, "exists:", CHROMA_DIR.exists())
        if not top.get("rules"):
            print("\n[DEBUG] rules empty. Notes:")
            print("  rule_engine_note:", top.get("rule_engine_note"))
            print("  DB:", DB, "exists:", DB.exists())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())