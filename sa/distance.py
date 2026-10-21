"""Euclidean distance matrix and round-trip tour length."""

from __future__ import annotations

import math
from typing import List, Sequence

from .data import City


def build_distance_matrix(cities: Sequence[City]) -> List[List[float]]:
    """Return an n x n matrix of Euclidean distances between city coordinates.

    Index ``i`` corresponds to ``cities[i]`` (position in the list, not the
    city's label).
    """
    n = len(cities)
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        xi, yi = cities[i].h, cities[i].v
        for j in range(i + 1, n):
            dist = math.hypot(xi - cities[j].h, yi - cities[j].v)
            d[i][j] = dist
            d[j][i] = dist
    return d


def tour_length(order: Sequence[int], dist: Sequence[Sequence[float]]) -> float:
    """Total length of a closed tour that visits the cities in ``order`` and
    returns to the starting city (round trip)."""
    n = len(order)
    if n < 2:
        return 0.0
    total = 0.0
    for k in range(n):
        total += dist[order[k]][order[(k + 1) % n]]
    return total
