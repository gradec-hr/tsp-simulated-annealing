"""Simulated Annealing core for the Traveling Salesman Problem.

The start city is pinned at position 0 of the tour and the tour is closed
(returns to the start), so the solver only ever reorders the remaining cities.
Neighbours are generated with the classic 2-opt move (reverse a random segment),
whose change in tour length can be evaluated in O(1).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass
class SAParams:
    """Key parameters that control the annealing schedule."""

    t_init: Optional[float] = None   # initial temperature; auto-estimated if None
    t_min: float = 1e-3              # stop once temperature drops below this
    alpha: float = 0.995             # geometric cooling factor per level (0 < a < 1)
    iters_per_temp: int = 200        # candidate moves evaluated at each temperature
    seed: Optional[int] = None       # RNG seed for reproducible runs


@dataclass
class SAResult:
    order: List[int]                 # best tour as city *indices*, starting at start_index
    length: float                    # length of that tour (round trip)
    initial_length: float            # length of the initial (random) tour
    iterations: int                  # total candidate moves evaluated
    accepted: int                    # moves accepted
    t_init: float                    # initial temperature actually used
    history: List[float] = field(default_factory=list)  # best length per temperature level


def _estimate_initial_temperature(
    order: Sequence[int], dist: Sequence[Sequence[float]], rng: random.Random
) -> float:
    """Estimate T_init from the average absolute cost change of random 2-opt moves,
    so that clearly-worse moves start out being accepted roughly half the time."""
    n = len(order)
    if n < 4:
        return 1.0
    deltas = []
    for _ in range(min(200, n * 5)):
        i = rng.randint(1, n - 1)
        j = rng.randint(1, n - 1)
        if i == j:
            continue
        if i > j:
            i, j = j, i
        deltas.append(abs(_reverse_delta(order, dist, i, j)))
    avg = sum(deltas) / len(deltas) if deltas else 1.0
    # Accept an average-sized worsening with probability ~0.5 at the start.
    return max(avg / math.log(2.0), 1e-6)


def _reverse_delta(
    order: Sequence[int], dist: Sequence[Sequence[float]], i: int, j: int
) -> float:
    """Change in closed-tour length from reversing order[i..j] (inclusive),
    with 1 <= i <= j <= n-1 (position 0, the start city, is never touched)."""
    n = len(order)
    a, b = order[i - 1], order[i]
    c, d = order[j], order[(j + 1) % n]
    if a == c:  # whole non-start segment reversed; endpoints identical -> no change
        return 0.0
    return (dist[a][c] + dist[b][d]) - (dist[a][b] + dist[c][d])


def simulated_annealing(
    dist: Sequence[Sequence[float]],
    params: SAParams,
    start_index: int = 0,
) -> SAResult:
    """Run simulated annealing on the given distance matrix.

    ``start_index`` is the index (into the distance matrix) of the city that must
    begin and end the tour.
    """
    n = len(dist)
    rng = random.Random(params.seed)

    # Initial tour: start city first, the rest shuffled.
    rest = [i for i in range(n) if i != start_index]
    rng.shuffle(rest)
    order = [start_index] + rest

    from .distance import tour_length  # local import to avoid a cycle at import time

    current_len = tour_length(order, dist)
    initial_len = current_len
    best_order = list(order)
    best_len = current_len

    t_init = params.t_init if params.t_init is not None else _estimate_initial_temperature(order, dist, rng)
    t = t_init
    if t <= 0:
        t = 1.0

    iterations = 0
    accepted = 0
    history: List[float] = []

    while t > params.t_min:
        for _ in range(params.iters_per_temp):
            iterations += 1
            # Pick a segment [i, j] within positions 1..n-1 (never move the start).
            i = rng.randint(1, n - 1)
            j = rng.randint(1, n - 1)
            if i == j:
                continue
            if i > j:
                i, j = j, i

            delta = _reverse_delta(order, dist, i, j)
            if delta <= 0 or rng.random() < math.exp(-delta / t):
                order[i : j + 1] = reversed(order[i : j + 1])
                current_len += delta
                accepted += 1
                if current_len < best_len:
                    best_len = current_len
                    best_order = list(order)

        history.append(best_len)
        t *= params.alpha

    return SAResult(
        order=best_order,
        length=best_len,
        initial_length=initial_len,
        iterations=iterations,
        accepted=accepted,
        t_init=t_init,
        history=history,
    )
