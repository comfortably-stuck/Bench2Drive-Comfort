#!/usr/bin/env python3
"""Standstill report for one Bench2Drive evaluation run.

Reports the fraction of each route spent stationary, using the same fixed
1-second segmentation as the comfort metric's traditional and fixed
implementations.

Usage:
    python evaluate_standstill.py <run_dir> [-m metric_dir] [-o out.csv]
"""

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comfort_metrics import results, standstill


def evaluate_run(run_dir, metric_dir):
    rows = []
    for record, episode in results.iter_routes(run_dir, metric_dir):
        route_id = results.short_route_id(record.get("route_id", ""))
        standstill_pct = None
        if episode is not None:
            fraction = standstill.standstill_fraction(episode["location"])
            standstill_pct = fraction * 100.0 if fraction is not None else None
        rows.append({
            "route_id": route_id,
            "status": record.get("status"),
            "completion_pct": float(record["scores"]["score_route"]),
            "standstill_pct": standstill_pct,
        })

    values = [r["standstill_pct"] for r in rows if r["standstill_pct"] is not None]
    summary = {
        "n_routes": len(rows),
        "standstill_pct": float(np.mean(values)) if values else None,
    }
    return rows, summary


def _fmt(value, nd=2):
    return f"{value:.{nd}f}" if value is not None else "n/a"


def print_table(rows):
    header = ["Route ID", "Status", "Standstill %", "Completion %"]
    table = [header]
    for r in rows:
        table.append([r["route_id"], str(r["status"]),
                      _fmt(r["standstill_pct"]), _fmt(r["completion_pct"])])
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    for i, row in enumerate(table):
        print(" | ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)))
        if i == 0:
            print("-+-".join("-" * w for w in widths))


def write_csv(rows, path):
    fields = ["route_id", "status", "completion_pct", "standstill_pct"]
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
                        help="Output CSV path (default: <run_dir>/standstill_per_route.csv).")
    args = parser.parse_args()

    run_dir = os.path.abspath(args.run_dir)
    metric_dir = os.path.abspath(args.metric_dir) if args.metric_dir else run_dir
    out_path = args.output or os.path.join(run_dir, "standstill_per_route.csv")

    rows, summary = evaluate_run(run_dir, metric_dir)
    if not rows:
        print(f"No records found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    print_table(rows)
    write_csv(rows, out_path)

    print()
    print(f"routes            : {summary['n_routes']}")
    print(f"Time spent stationary : {_fmt(summary['standstill_pct'])}%")
    print(f"\nCSV written to {out_path}")


if __name__ == "__main__":
    main()
