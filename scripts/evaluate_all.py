#!/usr/bin/env python3
"""Compute every metric reported in the paper for one or more evaluation runs.

For each run directory this combines driving score, success rate, efficiency,
the three comfort-metric variants, and the standstill benchmark into a single
row, matching the paper's main results table.

Usage:
    python evaluate_all.py <run_dir> [<run_dir> ...] [--route-xml routes.xml]
                           [-o out.csv]
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comfort_metrics import results
from comfort_metrics.route_geometry import load_route_waypoints

from evaluate_comfort import evaluate_run as evaluate_comfort_run, DEFAULT_ROUTE_XML
from evaluate_standstill import evaluate_run as evaluate_standstill_run


def evaluate(run_dir, route_xml):
    run_dir = os.path.abspath(run_dir)
    metric_dir = run_dir

    driving_score, success_rate, n_records = results.driving_score_and_success_rate(run_dir)
    efficiency = results.efficiency(run_dir)
    _, comfort_summary = evaluate_comfort_run(run_dir, metric_dir, route_xml)
    _, standstill_summary = evaluate_standstill_run(run_dir, metric_dir)

    return {
        "run": os.path.basename(run_dir),
        "n_routes": n_records,
        "traditional_comfort_pct": comfort_summary["traditional_comfort_pct"],
        "fixed_comfort_pct": comfort_summary["fixed_comfort_pct"],
        "distance_comfort_pct": comfort_summary["distance_comfort_pct"],
        "standstill_pct": standstill_summary["standstill_pct"],
        "efficiency": efficiency,
        "success_rate_pct": success_rate * 100.0 if success_rate is not None else None,
        "driving_score": driving_score,
    }


def _fmt(value, nd=2):
    return f"{value:.{nd}f}" if value is not None else "n/a"


def print_table(rows):
    header = ["Run", "Traditional %", "Fixed %", "Distance-based %",
              "Standstill %", "Efficiency", "Success Rate %", "Driving Score"]
    table = [header]
    for r in rows:
        table.append([
            r["run"], _fmt(r["traditional_comfort_pct"]), _fmt(r["fixed_comfort_pct"]),
            _fmt(r["distance_comfort_pct"]), _fmt(r["standstill_pct"]),
            _fmt(r["efficiency"]), _fmt(r["success_rate_pct"]), _fmt(r["driving_score"]),
        ])
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    for i, row in enumerate(table):
        print(" | ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)))
        if i == 0:
            print("-+-".join("-" * w for w in widths))


def write_csv(rows, path):
    fields = ["run", "n_routes", "traditional_comfort_pct", "fixed_comfort_pct",
              "distance_comfort_pct", "standstill_pct", "efficiency",
              "success_rate_pct", "driving_score"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dirs", nargs="+", help="One or more eval run directories.")
    parser.add_argument("--route-xml", default=DEFAULT_ROUTE_XML,
                        help="Leaderboard route XML providing route geometry.")
    parser.add_argument("-o", "--output", default=None, help="Output CSV path.")
    args = parser.parse_args()

    route_xml = os.path.abspath(args.route_xml)
    rows = [evaluate(run_dir, route_xml) for run_dir in args.run_dirs]

    print_table(rows)
    if args.output:
        write_csv(rows, args.output)
        print(f"\nCSV written to {args.output}")


if __name__ == "__main__":
    main()
