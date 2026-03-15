from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from backend.db.repo import fetch_program_rules
from backend.services.rule_engine import RuleEngineResult, evaluate_rules_python
from backend.services.semantic_scoring import SemanticConfig, semantic_score_from_distances
from backend.services.retrieval_service import retrieve_top_k


ALLOWED_HARD_FAIL_POLICIES = {"push_to_bottom", "zero_score", "keep"}


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _clamp_int(x: Any, lo: int, hi: int) -> int:
    try:
        v = int(x)
    except Exception:
        v = lo
    return max(lo, min(hi, v))


def _build_default_semantic_config() -> SemanticConfig:
    return SemanticConfig(alpha=2.0, score_max=40)


def _collect_hard_fail_reasons(rule_items: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for r in rule_items:
        if bool(r.get("hard_fail")) and str(r.get("status") or "").lower() == "failed":
            reason = str(r.get("reason") or r.get("rule_id") or "hard_fail").strip()
            if reason and reason not in reasons:
                reasons.append(reason)
    return reasons


def _to_mapping(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, RuleEngineResult):
        return {
            "program_id": obj.program_id,
            "rule_score": obj.rule_score,
            "hard_fail": obj.hard_fail,
            "rules": obj.rules,
            "missing_fields": obj.missing_fields,
        }
    out: dict[str, Any] = {}
    for k in ["program_id", "rule_score", "hard_fail", "rules", "missing_fields"]:
        if hasattr(obj, k):
            out[k] = getattr(obj, k)
    return out


@dataclass(frozen=True)
class ScoreConfig:
    retrieval_k: int = 5
    semantic: Optional[SemanticConfig] = None
    rule_score_max: int = 60

    # push_to_bottom | zero_score | keep
    hard_fail_policy: str = "push_to_bottom"
    hard_fail_cap: Optional[int] = None


def _evaluate_rules(
    *,
    db_path: Path,
    program_id: str,
    profile: dict[str, Any],
    rule_score_max: int,
) -> dict[str, Any]:
    rules_rows = fetch_program_rules(db_path, program_id=program_id)
    rules_payload = {
        "program_id": program_id,
        "rules": list(rules_rows or []),
    }
    return _to_mapping(
        evaluate_rules_python(
            rules_payload=rules_payload,
            profile=profile,
            program_id=program_id,
            rule_score_max=rule_score_max,
        )
    )


def score_program(
    *,
    db_path: Path,
    chroma_dir: Path,
    program_id: str,
    profile: dict[str, Any],
    query_text: str,
    cfg: ScoreConfig,
) -> dict[str, Any]:
    retrieval_k = _clamp_int(cfg.retrieval_k, 1, 10)

    sem_cfg = cfg.semantic or _build_default_semantic_config()
    sem_max = int(getattr(sem_cfg, "score_max", 40))

    hard_fail_policy = cfg.hard_fail_policy if cfg.hard_fail_policy in ALLOWED_HARD_FAIL_POLICIES else "push_to_bottom"

    retrieval_note: Optional[str] = None
    retrieved: list[dict[str, Any]] = []
    try:
        retrieved = retrieve_top_k(
            db_path=db_path,
            chroma_dir=chroma_dir,
            program_id=program_id,
            query_text=query_text,
            k=int(retrieval_k),
        )
    except Exception as e:
        retrieved = []
        retrieval_note = f"Retrieval unavailable: {type(e).__name__}: {e}"

    distances = [
        float(x.get("distance"))
        for x in retrieved
        if isinstance(x, dict) and isinstance(x.get("distance"), (int, float))
    ]
    semantic_score = int(semantic_score_from_distances(distances=distances, cfg=sem_cfg))
    semantic_score = max(0, min(sem_max, semantic_score))

    rule_engine_note = "Python rule engine active."
    rule_items: list[dict[str, Any]] = []
    rule_score = 0
    hard_fail = False
    missing_fields: list[str] = []

    try:
        rule_res = _evaluate_rules(
            db_path=db_path,
            program_id=program_id,
            profile=profile,
            rule_score_max=int(cfg.rule_score_max),
        )
        rule_score = _safe_int(rule_res.get("rule_score"), 0)
        hard_fail = bool(rule_res.get("hard_fail"))
        missing_fields = list(rule_res.get("missing_fields") or [])
        rule_items = list(rule_res.get("rules") or [])
    except Exception as e:
        rule_engine_note = f"Python rule engine unavailable: {type(e).__name__}: {e}"
        rule_score = 0
        hard_fail = False
        missing_fields = []
        rule_items = []

    rule_score = max(0, min(int(cfg.rule_score_max), int(rule_score)))

    total_score = rule_score + semantic_score
    total_score = max(0, min(int(cfg.rule_score_max) + int(sem_max), total_score))

    effective_total_score = total_score
    if hard_fail:
        if hard_fail_policy == "zero_score":
            effective_total_score = 0
        elif hard_fail_policy == "push_to_bottom":
            effective_total_score = -1
        elif hard_fail_policy == "keep":
            effective_total_score = total_score

        if cfg.hard_fail_cap is not None and hard_fail_policy != "push_to_bottom":
            effective_total_score = min(int(effective_total_score), int(cfg.hard_fail_cap))

    hard_fail_reasons = _collect_hard_fail_reasons(rule_items)

    scoring_spec = {
        "rule_score_max": int(cfg.rule_score_max),
        "semantic_score_max": int(sem_max),
        "hard_fail_policy": hard_fail_policy,
        "hard_fail_cap": cfg.hard_fail_cap,
        "rule_engine": "python",
        "semantic": {
            "sim": "exp(-alpha * distance)",
            "alpha": float(getattr(sem_cfg, "alpha", 2.0)),
            "k": int(retrieval_k),
        },
    }

    return {
        "program_id": program_id,
        "rule_score": rule_score,
        "semantic_score": semantic_score,
        "total_score": total_score,
        "effective_total_score": int(effective_total_score),
        "hard_fail": hard_fail,
        "hard_fail_reasons": hard_fail_reasons,
        "missing_fields": missing_fields,
        "rules": rule_items,
        "retrieval": {"query": query_text, "top_k": retrieved},
        "rule_engine_note": rule_engine_note,
        "retrieval_note": retrieval_note,
        "scoring_spec": scoring_spec,
    }
