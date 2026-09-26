"""Loading Bench2Drive leaderboard evaluation output.

An eval run directory holds one ``results_rank*.json`` (or equivalent) per
worker with the leaderboard's per-route records, and one sub-folder per
route holding that route's ``metric_info.json`` (the per-frame kinematic
log the comfort and standstill metrics are computed from).
"""

import glob
import json
import os
import re

import numpy as np

METRIC_KEYS = ("acceleration", "angular_velocity", "forward_vector",
               "right_vector", "location", "rotation")
COMPLETED_STATUSES = ("Completed", "Perfect")

# Per-rank result file names vary by evaluation harness.
_RESULT_PATTERNS = ("results_rank*.json", "simulation_results_rank*.json",
                    "checkpoint_endpoint_rank*.json")


def load_records(run_dir):
    """All route records from a run's per-rank leaderboard result files."""
    paths = []
    for pattern in _RESULT_PATTERNS:
        paths.extend(glob.glob(os.path.join(run_dir, pattern)))
    records = []
    for path in sorted(paths):
        with open(path) as f:
            records.extend(json.load(f)["_checkpoint"]["records"])
    return records


def short_route_id(route_id):
    """Route id without the ``_rep<N>`` repetition suffix."""
    match = re.match(r"RouteScenario_(.+?)(?:_rep\d+)?$", route_id or "")
    return match.group(1) if match else (route_id or "")


def _search_metric_info(folder):
    if not os.path.isdir(folder):
        return None
    direct = os.path.join(folder, "metric_info.json")
    if os.path.isfile(direct):
        return direct
    hits = glob.glob(os.path.join(folder, "**", "metric_info.json"), recursive=True)
    return hits[0] if hits else None


def find_metric_info(metric_dir, record):
    """Locate a record's ``metric_info.json``.

    Handles the small set of naming differences seen across agent
    submissions: a ``"<ScenarioClass>+"`` prefix on ``save_name``, a
    ``"_gpuN"`` folder suffix, and the metric file nested a few directories
    below the route folder instead of directly inside it.
    """
    save_name = record.get("save_name") or ""
    candidates = [save_name] if save_name else []
    if "+" in save_name:
        candidates.append(save_name.split("+", 1)[1])

    for name in candidates:
        hit = _search_metric_info(os.path.join(metric_dir, name))
        if hit:
            return hit
    for name in candidates:
        for folder in glob.glob(os.path.join(metric_dir, name + "_gpu*")):
            hit = _search_metric_info(folder)
            if hit:
                return hit

    match = re.match(r"RouteScenario_(.+?)_rep\d+", record.get("route_id", ""))
    if match:
        token = "Route" + match.group(1) + "_"
        for folder in glob.glob(os.path.join(metric_dir, "*")):
            if token in os.path.basename(folder):
                hit = _search_metric_info(folder)
                if hit:
                    return hit
        bare = _search_metric_info(os.path.join(metric_dir, match.group(1)))
        if bare:
            return bare
    return None


def load_episode(metric_info_path):
    """Per-frame kinematic signals from one route's ``metric_info.json``."""
    with open(metric_info_path) as f:
        data = json.load(f)
    episode = {key: [] for key in METRIC_KEYS}
    for frame in data.values():
        for key in METRIC_KEYS:
            episode[key].append(frame[key])
    return {key: np.asarray(values) for key, values in episode.items()}


def iter_routes(run_dir, metric_dir=None):
    """Yield ``(record, episode)`` for every route in a run.

    ``episode`` is ``None`` if its ``metric_info.json`` could not be found.
    """
    metric_dir = metric_dir or run_dir
    for record in load_records(run_dir):
        path = find_metric_info(metric_dir, record)
        episode = load_episode(path) if path else None
        yield record, episode


def _is_success(record):
    """A route counts as a success iff it completed and triggered no
    infraction, other than a min-speed infraction (which does not fail a
    route, only penalizes its efficiency)."""
    if record.get("status") not in COMPLETED_STATUSES:
        return False
    return all(
        len(values) == 0
        for key, values in record.get("infractions", {}).items()
        if key != "min_speed_infractions"
    )


def driving_score_and_success_rate(run_dir):
    """Mean composed score and success rate over all routes in a run."""
    records = load_records(run_dir)
    if not records:
        return None, None, 0
    scores = [float(r["scores"]["score_composed"]) for r in records]
    successes = sum(1 for r in records if _is_success(r))
    return float(np.mean(scores)), successes / len(records), len(records)


def efficiency(run_dir):
    """Mean of each route's min-speed-infraction percentages."""
    values = []
    for record in load_records(run_dir):
        infractions = record.get("infractions", {}).get("min_speed_infractions", [])
        route_values = []
        for entry in infractions:
            if not isinstance(entry, str):
                continue
            match = re.search(r"\d+\.?\d*%", entry)
            if not match:
                continue
            value = float(match.group().rstrip("%"))
            if value > 1000:
                continue
            route_values.append(value)
        if route_values:
            values.append(sum(route_values) / len(route_values))
    return float(np.mean(values)) if values else None
