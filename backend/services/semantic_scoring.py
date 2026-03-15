from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SemanticConfig:
    alpha: float = 2.0         # exp(-alpha*d)
    k: int = 5
    score_max: int = 40
    w_best: float = 0.65
    w_mean: float = 0.35


def distance_to_similarity(d: float, *, alpha: float) -> float:
    # similarity in (0,1], monotone decreasing with distance
    if d < 0:
        d = 0.0
    return math.exp(-alpha * d)


def aggregate_similarities(sims: Sequence[float], *, w_best: float, w_mean: float) -> float:
    if not sims:
        return 0.0
    best = max(sims)
    mean = sum(sims) / len(sims)
    return (w_best * best) + (w_mean * mean)


def semantic_score_from_distances(distances: Sequence[float], cfg: SemanticConfig = SemanticConfig()) -> int:
    sims = [distance_to_similarity(float(d), alpha=cfg.alpha) for d in distances if d is not None]
    agg = aggregate_similarities(sims, w_best=cfg.w_best, w_mean=cfg.w_mean)
    score = round(cfg.score_max * agg)
    if score < 0:
        score = 0
    if score > cfg.score_max:
        score = cfg.score_max
    return int(score)