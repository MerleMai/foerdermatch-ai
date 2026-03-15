from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Optional

from backend.services.retrieval_service import retrieve_top_k
from backend.services.semantic_scoring import SemanticConfig, semantic_score_from_distances

ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = ROOT / "data" / "chroma"
DB = ROOT / "data" / "programs.db"


def make_context_snippet(text: str, query: str, window: int = 250) -> str:
    t = text.replace("\n", " ")
    t_low = t.lower()
    tokens = [tok.strip().lower() for tok in query.split() if len(tok.strip()) >= 3]

    if not tokens:
        return (t[:350] + "…") if len(t) > 350 else t

    positions = [(t_low.find(tok), tok) for tok in tokens if t_low.find(tok) != -1]
    if not positions:
        return (t[:350] + "…") if len(t) > 350 else t

    idx, tok = min(positions, key=lambda x: x[0])
    start = max(0, idx - window)
    end = min(len(t), idx + len(tok) + window)

    snippet = t[start:end]
    if start > 0:
        snippet = "… " + snippet
    if end < len(t):
        snippet = snippet + " …"
    return snippet


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _parse_csv_arg(val: Optional[str]) -> list[str]:
    if not val:
        return []
    parts = [p.strip() for p in val.split(",")]
    return [p for p in parts if p]


def _gate_check(
    *,
    program_id: str,
    query: str,
    docs: list[str],
    metas: list[dict[str, Any]],
    dists: list[float],
    expect_doc_type: Optional[str],
    max_dist: Optional[float],
    expect_page_contains: Optional[str],
    must_contain_all: list[str],
    must_contain_any: list[str],
) -> tuple[bool, str]:
    exp_doc = _norm(expect_doc_type)
    exp_page = _norm(expect_page_contains)
    must_all = [_norm(x) for x in must_contain_all if _norm(x)]
    any_list = [_norm(x) for x in must_contain_any if _norm(x)]

    best_diag = None

    for txt, md, dist in zip(docs, metas, dists):
        doc_type = _norm(str(md.get("doc_type") or ""))
        page_ref = _norm(str(md.get("page_ref") or ""))

        ok_doc = True if not exp_doc else (doc_type == exp_doc)
        ok_dist = True if (max_dist is None) else (dist <= float(max_dist))
        ok_page = True if not exp_page else (exp_page in page_ref)

        t_low = _norm(txt)

        ok_all = True
        missing_all: list[str] = []
        for kw in must_all:
            if kw not in t_low:
                ok_all = False
                missing_all.append(kw)

        ok_any = True
        missing_any: list[str] = []
        if any_list:
            ok_any = False
            for kw in any_list:
                if kw in t_low:
                    ok_any = True
                    break
            if not ok_any:
                missing_any = any_list

        if ok_doc and ok_dist and ok_page and ok_all and ok_any:
            diag = f"doc={md.get('doc_type')} dist={dist:.4f} page={md.get('page_ref')} q={query!r}"
            return True, diag

        if best_diag is None:
            best_diag = (
                f"(closest hit) doc={md.get('doc_type')} dist={dist:.4f} page={md.get('page_ref')}; "
                f"doc_ok={ok_doc} dist_ok={ok_dist} page_ok={ok_page} all_ok={ok_all} any_ok={ok_any}"
            )
            if missing_all:
                best_diag += f" missing_all={missing_all}"
            if missing_any:
                best_diag += f" missing_any={missing_any}"

    return False, best_diag or "no results"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--q", required=True)
    parser.add_argument("--k", type=int, default=3)

    parser.add_argument("--gate", action="store_true", help="Enable quality gate checks (exit 1 on fail).")
    parser.add_argument("--expect-doc-type", type=str, default=None)
    parser.add_argument("--max-dist", type=float, default=None)
    parser.add_argument("--expect-page-contains", type=str, default=None)
    parser.add_argument("--must-contain", type=str, default=None)
    parser.add_argument("--must-contain-any", type=str, default=None)

    parser.add_argument("--alpha", type=float, default=2.0)
    parser.add_argument("--w-best", type=float, default=0.65)
    parser.add_argument("--w-mean", type=float, default=0.35)
    args = parser.parse_args()

    hits = retrieve_top_k(
        db_path=DB,
        chroma_dir=CHROMA_DIR,
        program_id=args.program_id,
        query_text=args.q,
        k=args.k,
    )

    docs = [h.get("text") or "" for h in hits]
    metas = [h.get("metadata") or {} for h in hits]
    dists = [float(h.get("distance") or 1.0) for h in hits]

    if not docs:
        if args.gate:
            print(f"[FAIL] {args.program_id} gate: no results q={args.q!r}")
            raise SystemExit(1)
        print("No results.")
        return

    sem_cfg = SemanticConfig(alpha=args.alpha, w_best=args.w_best, w_mean=args.w_mean, k=args.k)
    sem = semantic_score_from_distances(dists, sem_cfg)

    if args.gate:
        must_all = _parse_csv_arg(args.must_contain)
        must_any = _parse_csv_arg(args.must_contain_any)

        ok, diag = _gate_check(
            program_id=args.program_id,
            query=args.q,
            docs=docs,
            metas=metas,
            dists=dists,
            expect_doc_type=args.expect_doc_type,
            max_dist=args.max_dist,
            expect_page_contains=args.expect_page_contains,
            must_contain_all=must_all,
            must_contain_any=must_any,
        )

        if ok:
            parts = [f"[PASS] {args.program_id} gate ok: {diag}"]
            if args.expect_doc_type:
                parts.append(f"expect_doc={args.expect_doc_type}")
            if args.max_dist is not None:
                parts.append(f"max_dist={args.max_dist}")
            if args.expect_page_contains:
                parts.append(f"expect_page~={args.expect_page_contains!r}")
            if must_all:
                parts.append(f"must_all={must_all}")
            if must_any:
                parts.append(f"must_any={must_any}")
            parts.append(f"semantic_score(0..40)={sem}")
            print("  ".join(parts))
            return

        parts = [
            f"[FAIL] {args.program_id} gate failed: q={args.q!r}",
            f"expect_doc={args.expect_doc_type!r}",
            f"max_dist={args.max_dist}",
            f"expect_page~={args.expect_page_contains!r}",
            f"must_all={must_all}",
            f"must_any={must_any}",
            f"diag={diag}",
        ]
        print("  ".join(parts))
        raise SystemExit(1)

    print(f"\nQuery: {args.q}\nProgram: {args.program_id}\n")
    print(
        f"semantic_score(0..40) = {sem}  using sim(d)=exp(-alpha*d), alpha={args.alpha}, "
        f"agg={args.w_best}*max+{args.w_mean}*mean\n"
    )

    for i, (txt, md, dist) in enumerate(zip(docs, metas, dists), start=1):
        snippet = make_context_snippet(txt, args.q)
        print(
            f"[{i}] distance={dist:.4f}  "
            f"doc={md.get('doc_type')}  "
            f"file={md.get('filename')}  "
            f"page={md.get('page_ref')}"
        )
        print(f"    {snippet}\n")


if __name__ == "__main__":
    main()