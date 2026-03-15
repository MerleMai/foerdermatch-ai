from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuleEngineResult:
    program_id: str
    rule_score: int
    hard_fail: bool
    rules: list[dict[str, Any]]
    missing_fields: list[str]


def _is_unknown(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _get_path(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in (path or "").split("."):
        if not part:
            return None
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _scalar_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) == float(right)
    return left == right


def _eval_boolean_rule(actual: Any, *, op: str, expected: Any) -> str:
    actual_bool = _as_bool(actual)
    expected_bool = _as_bool(expected)
    if actual_bool is None or expected_bool is None:
        return "unknown"
    if op != "eq":
        return "unknown"
    return "fulfilled" if actual_bool == expected_bool else "failed"


def _eval_enum_rule(actual: Any, *, op: str, expected: Any) -> str:
    if isinstance(actual, (dict, list)):
        return "unknown"
    if op == "eq":
        return "fulfilled" if _scalar_equal(actual, expected) else "failed"
    if op == "in":
        if not isinstance(expected, list):
            return "unknown"
        return "fulfilled" if any(_scalar_equal(actual, item) for item in expected) else "failed"
    return "unknown"


def _eval_numeric_rule(actual: Any, *, op: str, expected: Any) -> str:
    actual_num = _as_number(actual)
    if actual_num is None:
        return "unknown"

    if op in {"lt", "lte", "gt", "gte"}:
        expected_num = _as_number(expected)
        if expected_num is None:
            return "unknown"
        if op == "lt":
            ok = actual_num < expected_num
        elif op == "lte":
            ok = actual_num <= expected_num
        elif op == "gt":
            ok = actual_num > expected_num
        else:
            ok = actual_num >= expected_num
        return "fulfilled" if ok else "failed"

    if op == "between":
        if not isinstance(expected, list) or len(expected) != 2:
            return "unknown"
        lo = _as_number(expected[0])
        hi = _as_number(expected[1])
        if lo is None or hi is None:
            return "unknown"
        return "fulfilled" if lo <= actual_num <= hi else "failed"

    return "unknown"


def _evaluate_rule(rule: dict[str, Any], profile: dict[str, Any]) -> tuple[str, str]:
    actual = _get_path(profile, str(rule.get("path") or ""))
    if _is_unknown(actual):
        return "unknown", "Missing/unknown field for rule evaluation."

    rule_type = str(rule.get("rule_type") or "")
    op = str(rule.get("op") or "")
    expected = rule.get("value")

    if rule_type == "boolean":
        status = _eval_boolean_rule(actual, op=op, expected=expected)
    elif rule_type == "enum":
        status = _eval_enum_rule(actual, op=op, expected=expected)
    elif rule_type == "numeric":
        status = _eval_numeric_rule(actual, op=op, expected=expected)
    else:
        status = "unknown"

    if status == "fulfilled":
        return status, str(rule.get("reason_ok") or "Rule fulfilled.")
    if status == "failed":
        return status, str(rule.get("reason_fail") or "Rule failed.")
    return status, "Missing/unknown field for rule evaluation."


def evaluate_rules_python(
    *,
    rules_payload: dict[str, Any] | list[dict[str, Any]],
    profile: dict[str, Any],
    program_id: str = "",
    rule_score_max: int = 60,
) -> RuleEngineResult:
    if isinstance(rules_payload, dict):
        rules = list(rules_payload.get("rules") or [])
        payload_program_id = str(rules_payload.get("program_id") or "")
    else:
        rules = list(rules_payload or [])
        payload_program_id = ""

    effective_program_id = program_id or payload_program_id

    rule_items: list[dict[str, Any]] = []
    missing_fields: list[str] = []
    seen_missing: set[str] = set()

    raw_points = 0.0
    max_points = 0.0
    hard_fail = False

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        weight = int(rule.get("weight") or 0)
        unknown_factor = float(rule.get("unknown_factor") or 0.35)
        status, reason = _evaluate_rule(rule, profile)

        max_points += float(weight)
        if status == "fulfilled":
            raw_points += float(weight)
        elif status == "unknown":
            raw_points += float(weight) * unknown_factor
            missing_field = str(rule.get("missing_field") or "").strip()
            if missing_field and missing_field not in seen_missing:
                seen_missing.add(missing_field)
                missing_fields.append(missing_field)

        is_hard_fail = bool(rule.get("hard_fail"))
        if status == "failed" and is_hard_fail:
            hard_fail = True

        rule_items.append(
            {
                "rule_id": str(rule.get("rule_id") or ""),
                "status": status,
                "weight": weight,
                "hard_fail": is_hard_fail,
                "reason": reason,
            }
        )

    if max_points > 0:
        scaled = round(float(rule_score_max) * (raw_points / max_points))
        rule_score = max(0, min(int(rule_score_max), int(scaled)))
    else:
        rule_score = 0

    return RuleEngineResult(
        program_id=effective_program_id,
        rule_score=rule_score,
        hard_fail=hard_fail,
        rules=rule_items,
        missing_fields=missing_fields,
    )
