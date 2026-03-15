from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

_SENT_SPLIT = re.compile(r"(?<=[\.\!\?])\s+")
_WS = re.compile(r"\s+")

# Triggers for compliance-like statements (German)
TRIGGERS = [
    "antrag",
    "vor beginn",
    "beginn der arbeiten",
    "ausgeschlossen",
    "muss",
    "dürfen nicht",
    "darf nicht",
    "voraussetzung",
    "beihilfeantrag",
    "de-minimis",
    "unternehmen in schwierigkeiten",
]

NEG_TRIGGERS = [
    "beispiel",
    "z.b.",
    "beispielsweise",
]

def _norm(t: str) -> str:
    t = t.replace("\n", " ")
    t = _WS.sub(" ", t).strip()
    return t

def _score_sentence(s: str) -> int:
    low = s.lower()
    score = 0
    for tr in TRIGGERS:
        if tr in low:
            score += 3
    for tr in NEG_TRIGGERS:
        if tr in low:
            score -= 1
    # prefer medium length sentences
    n = len(s)
    if 60 <= n <= 260:
        score += 2
    return score

def extract_checklist_items(
    retrieved: list[dict[str, Any]],
    *,
    max_items: int = 5,
) -> list[dict[str, Any]]:
    """
    retrieved items expected shape:
      { "text": str, "metadata": {...}, "distance": float }
    Returns list:
      { "item": str, "criticality": "high|medium|low", "source_refs":[...] }
    """
    candidates: list[tuple[int, str, dict[str, Any]]] = []

    for r in retrieved:
        text = _norm(str(r.get("text") or ""))
        if not text:
            continue

        md = dict(r.get("metadata") or {})
        dist = float(r.get("distance") or 0.0)
        src = {
            "doc_type": md.get("doc_type"),
            "filename": md.get("filename"),
            "page_ref": md.get("page_ref"),
            "document_id": md.get("document_id"),
            "chunk_index": md.get("chunk_index"),
            "distance": dist,
        }

        # Split into sentences
        sentences = _SENT_SPLIT.split(text)
        for s in sentences:
            s = _norm(s)
            if len(s) < 40:
                continue
            sc = _score_sentence(s)
            if sc <= 0:
                continue
            candidates.append((sc, s, src))

    # Sort by score desc, then by lower distance (better)
    candidates.sort(key=lambda x: (-x[0], x[2]["distance"]))

    out: list[dict[str, Any]] = []
    used = set()

    for sc, sent, src in candidates:
        # dedupe by prefix
        key = sent[:120].lower()
        if key in used:
            continue
        used.add(key)

        crit = "medium"
        low = sent.lower()
        if "ausgeschlossen" in low or "dürfen nicht" in low or "darf nicht" in low:
            crit = "high"
        if "vor beginn" in low or "beginn der arbeiten" in low:
            crit = "high"

        # Make it a checklist-style sentence
        item = sent
        if not item.endswith((".", "!", "?")):
            item += "."

        out.append(
            {
                "item": item,
                "criticality": crit,
                "source_refs": [src],
            }
        )
        if len(out) >= max_items:
            break

    return out