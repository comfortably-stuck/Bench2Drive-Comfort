#!/usr/bin/env python3
"""Comfort report for one Bench2Drive evaluation run.

Reports all three comfort-metric variants discussed in the paper for every
route in a run, plus their run-level aggregates:

  * Traditional comfort  -- Bench2Drive's original metric, unmodified.
  * Fixed implementation -- nuPlan-faithful signals, smoothed once per
                             episode, judged over fixed 1 s segments.
  * Distance-based (ours)-- the same signals, judged over 100 equal-distance
                             segments along the route.

The traditional and fixed variants average each route's own comfort fraction
across routes. The distance-based variant instead pools every segment from
every route and averages once, so it weights by distance driven rather than
by route count (see the paper for why).

Usage:
    python evaluate_comfort.py <run_dir> [-m metric_dir] [-o out.csv]
                               [--route-xml routes.xml]
"""

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comfort_metrics import comfort, results
from comfort_metrics.bench2drive import get_bench2drive_root
from comfort_metrics.route_geometry import load_route_waypoints

DEFAULT_ROUTE_XML = os.path.join(
    get_bench2drive_root(), "leaderboard", "data", "bench2drive220.xml")


def evaluate_run(run_dir, metric_dir, route_xml):
    waypoints_by_route = load_route_waypoints(route_xml)

    rows = []
    all_distance_flags = []
    for record, episode in results.iter_routes(run_dir, metric_dir):
        route_id = results.short_route_id(record.get("route_id", ""))
        completion_pct = float(record["scores"]["score_route"])
        route_length_m = float(record.get("meta", {}).get("route_length", 0.0))

        row = {
            "route_id": route_id,
            "status": record.get("status"),
            "completion_pct": completion_pct,
            "route_length_m": route_length_m,
            "traditional_comfort_pct": None,
            "fixed_comfort_pct": None,
            "distance_comfort_pct": None,
            "n_distance_segments": None,
        }

        if episode is not None:
            row["traditional_comfort_pct"] = comfort.traditional_comfort(episode) * 100.0

            fixed_flags = comfort.fixed_comfort_flags(episode)
            if fixed_flags:
                row["fixed_comfort_pct"] = 100.0 * sum(fixed_flags) / len(fixed_flags)

            waypoints = waypoints_by_route.get(route_id)
            if waypoints is not None:
                distance_flags = comfort.distance_comfort_flags(episode, waypoints)
                if distance_flags:
                    row["distance_comfort_pct"] = 100.0 * sum(distance_flags) / len(distance_flags)
                    row["n_distance_segments"] = len(distance_flags)
                    all_distance_flags.extend(distance_flags)

        rows.append(row)

    summary = {
        "n_routes": len(rows),
        "traditional_comfort_pct": _mean_pct(rows, "traditional_comfort_pct"),
        "fixed_comfort_pct": _mean_pct(rows, "fixed_comfort_pct"),
        "distance_comfort_pct": (
            100.0 * sum(all_distance_flags) / len(all_distance_flags)
            if all_distance_flags else None),
    }
    return rows, summary


def _mean_pct(rows, key):
    values = [r[key] for r in rows if r[key] is not None]
    return float(np.mean(values)) if values else None


def _fmt(value, nd=2):
    return f"{value:.{nd}f}" if value is not None else "n/a"


def print_table(rows):
    header = ["Route ID", "Status", "Traditional %", "Fixed %", "Distance-based %", "Completion %"]
    table = [header]
    for r in rows:
        table.append([
            r["route_id"], str(r["status"]),
            _fmt(r["traditional_comfort_pct"]), _fmt(r["fixed_comfort_pct"]),
            _fmt(r["distance_comfort_pct"]), _fmt(r["completion_pct"]),
        ])
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    for i, row in enumerate(table):
        print(" | ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)))
        if i == 0:
            print("-+-".join("-" * w for w in widths))


def write_csv(rows, path):
    fields = ["route_id", "status", "completion_pct", "route_length_m",
              "traditional_comfort_pct", "fixed_comfort_pct",
              "distance_comfort_pct", "n_distance_segments"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", help="Eval run directory (Bench2Drive results JSON + per-route folders).")
    parser.add_argument("-m", "--metric-dir", default=None,
                        help="Folder holding the per-route metric_info.json dirs (default: run_dir).")
    parser.add_argument("-o", "--output", default=None,
                        help="Output CSV path (default: <run_dir>/comfort_per_route.csv).")
    parser.add_argument("--route-xml", default=DEFAULT_ROUTE_XML,
                        help="Leaderboard route XML providing route geometry.")
    args = parser.parse_args()

    run_dir = os.path.abspath(args.run_dir)
    metric_dir = os.path.abspath(args.metric_dir) if args.metric_dir else run_dir
    out_path = args.output or os.path.join(run_dir, "comfort_per_route.csv")

    rows, summary = evaluate_run(run_dir, metric_dir, os.path.abspath(args.route_xml))
    if not rows:
        print(f"No records found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    print_table(rows)
    write_csv(rows, out_path)

    print()
    print(f"routes                : {summary['n_routes']}")
    print(f"Traditional comfort   : {_fmt(summary['traditional_comfort_pct'])}%")
    print(f"Fixed implementation  : {_fmt(summary['fixed_comfort_pct'])}%")
    print(f"Distance-based (ours) : {_fmt(summary['distance_comfort_pct'])}%")
    print(f"\nCSV written to {out_path}")


if __name__ == "__main__":
    main()
