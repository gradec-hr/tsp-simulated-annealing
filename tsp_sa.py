#!/usr/bin/env python3
"""Solve the 'A Walk Through the United States' TSP with Simulated Annealing.

Finds a short round trip that begins and ends in a chosen start city
(Olympia, Washington by default) and visits every other city exactly once.

Example:
    python tsp_sa.py --seed 1
    python tsp_sa.py --alpha 0.999 --iters-per-temp 400 --seed 1 --plot usa.png
    python tsp_sa.py --xlsx "a_walk_through_united_states.xlsx" --no-plot
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

from sa.data import City, load_cities, load_cities_xlsx
from sa.distance import build_distance_matrix, tour_length
from sa.annealing import SAParams, simulated_annealing

DEFAULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cities.csv")
DEFAULT_START = "Olympia (Washington)"


def find_start_index(cities: List[City], start: str) -> int:
    """Resolve the start city given a (case-insensitive, partial) name match."""
    s = start.strip().lower()
    exact = [i for i, c in enumerate(cities) if c.name.lower() == s]
    if exact:
        return exact[0]
    partial = [i for i, c in enumerate(cities) if s in c.name.lower()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise SystemExit(
            f"Start city '{start}' not found. Available examples: "
            + ", ".join(c.name for c in cities[:5]) + ", ..."
        )
    raise SystemExit(
        f"Start city '{start}' is ambiguous; matches: "
        + ", ".join(cities[i].name for i in partial)
    )


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Simulated Annealing solver for the US capitals TSP.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = p.add_argument_group("input")
    src.add_argument("--input", default=DEFAULT_CSV,
                     help="CSV file with columns label,city,state,h,v.")
    src.add_argument("--xlsx", default=None,
                     help="Read cities from the original .xlsx workbook instead of the CSV.")
    src.add_argument("--start", default=DEFAULT_START,
                     help="City that begins and ends the trip (partial match allowed).")

    sa = p.add_argument_group("simulated annealing parameters")
    sa.add_argument("--t-init", type=float, default=None,
                    help="Initial temperature (auto-estimated from the data if omitted).")
    sa.add_argument("--t-min", type=float, default=1e-3,
                    help="Stop once the temperature falls below this value.")
    sa.add_argument("--alpha", type=float, default=0.995,
                    help="Geometric cooling factor per temperature level (0 < alpha < 1).")
    sa.add_argument("--iters-per-temp", type=int, default=200,
                    help="Candidate moves evaluated at each temperature level.")
    sa.add_argument("--seed", type=int, default=None,
                    help="Random seed for reproducible runs.")

    out = p.add_argument_group("output")
    out.add_argument("--plot", default="route.png",
                     help="Path for the route-map PNG.")
    out.add_argument("--no-plot", action="store_true",
                     help="Do not produce a route-map image.")
    return p.parse_args(argv)


def save_plot(cities: List[City], order: List[int], length: float, path: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless / no display needed
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot (install it or use --no-plot).",
              file=sys.stderr)
        return

    closed = order + [order[0]]
    xs = [cities[i].h for i in closed]
    ys = [cities[i].v for i in closed]

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.plot(xs, ys, "-", color="#1f77b4", linewidth=1.2, zorder=1)
    ax.scatter([c.h for c in cities], [c.v for c in cities],
               color="#1f77b4", s=18, zorder=2)

    start = cities[order[0]]
    ax.scatter([start.h], [start.v], color="#d62728", s=90, zorder=3,
               label=f"start/end: {start.name}")

    for c in cities:
        ax.annotate(c.name.split(" (")[0], (c.h, c.v),
                    fontsize=6, xytext=(2, 2), textcoords="offset points")

    ax.set_title(f"Simulated Annealing TSP route - total distance {length:.1f}")
    ax.set_xlabel("H")
    ax.set_ylabel("V")
    ax.legend(loc="best", fontsize=8)
    ax.margins(0.05)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"Route map written to {path}")


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.xlsx:
        cities = load_cities_xlsx(args.xlsx)
        source = args.xlsx
    else:
        cities = load_cities(args.input)
        source = args.input

    start_index = find_start_index(cities, args.start)
    dist = build_distance_matrix(cities)

    params = SAParams(
        t_init=args.t_init,
        t_min=args.t_min,
        alpha=args.alpha,
        iters_per_temp=args.iters_per_temp,
        seed=args.seed,
    )
    result = simulated_annealing(dist, params, start_index=start_index)

    # Guard: the returned tour must be a valid permutation of all cities.
    assert sorted(result.order) == list(range(len(cities))), "invalid tour produced"
    recomputed = tour_length(result.order, dist)
    assert abs(recomputed - result.length) < 1e-6, "length bookkeeping mismatch"

    print("=" * 64)
    print("Simulated Annealing TSP  -  A Walk Through the United States")
    print("=" * 64)
    print(f"Cities loaded      : {len(cities)}  (from {source})")
    print(f"Start / end city   : {cities[start_index].name}")
    print(f"Parameters         : t_init={result.t_init:.4g}, t_min={args.t_min:g}, "
          f"alpha={args.alpha:g}, iters_per_temp={args.iters_per_temp}, seed={args.seed}")
    print(f"Candidate moves     : {result.iterations}  (accepted {result.accepted})")
    print("-" * 64)
    print(f"Initial random tour: {result.initial_length:.2f}")
    print(f"Best tour found    : {result.length:.2f}  "
          f"({100 * (1 - result.length / result.initial_length):.1f}% shorter)")
    print("-" * 64)
    print("Route:")
    for step, idx in enumerate(result.order, start=1):
        print(f"  {step:>2}. {cities[idx].name}")
    print(f"  {len(result.order) + 1:>2}. {cities[result.order[0]].name}   (return)")
    print("=" * 64)

    if not args.no_plot:
        save_plot(cities, result.order, result.length, args.plot)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
