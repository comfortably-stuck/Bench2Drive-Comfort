"""The three comfort-metric variants compared in the paper.

All three judge a segment of a route "comfortable" iff every logged frame in
it satisfies all six kinematic thresholds from ``smoothing.py``; they differ
in how the underlying signals are computed and how routes are segmented:

* ``traditional_comfort`` -- Bench2Drive's original metric, unmodified. It is
  imported directly from the ``Bench2Drive`` submodule rather than
  reimplemented, so this repository never redistributes a modified copy of
  it. Segments are fixed 20-frame (1 s) chunks, each smoothed independently.

* ``fixed_comfort`` -- the same fixed-length segmentation, but computed from
  the nuPlan-faithful, smooth-first signals in ``smoothing.py``: the whole
  episode is smoothed once (no segment-boundary artifacts), with the correct
  sampling rate, window lengths, yaw derivative and yaw unit.

* ``distance_comfort`` -- the metric proposed in the paper: the same
  smooth-first signals, but segmented into ``NUM_DISTANCE_SEGMENTS`` equal
  bins of route progress rather than fixed time windows.

Aggregation across routes differs between variants; see
``scripts/evaluate_comfort.py``.
"""

import os
import sys

import numpy as np

from . import smoothing
from .route_geometry import route_progress

METRIC_KEYS = ("acceleration", "angular_velocity", "forward_vector",
               "right_vector", "location", "rotation")

FRAMES_PER_SEGMENT = 20     # 1 s at CARLA's 20 Hz logging rate
NUM_DISTANCE_SEGMENTS = 100

_SUBMODULE_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Bench2Drive", "tools")


def _original_seg_compute_comfort_metric():
    """Bench2Drive's own comfort function, loaded from the submodule.

    Loaded lazily and from the submodule's source (rather than vendored
    here) so this repository never carries its own copy of Bench2Drive code.
    """
    if _SUBMODULE_TOOLS_DIR not in sys.path:
        sys.path.insert(0, _SUBMODULE_TOOLS_DIR)
    from efficiency_smoothness_benchmark import seg_compute_comfort_metric
    return seg_compute_comfort_metric


def traditional_comfort(episode, per_step=FRAMES_PER_SEGMENT):
    """Bench2Drive's original, unmodified comfort score for one route."""
    seg_compute_comfort_metric = _original_seg_compute_comfort_metric()
    args = [episode[key] for key in METRIC_KEYS]
    return seg_compute_comfort_metric(*args, per_step=per_step)


def _segment_flags(signals, segment_ids, num_segments, min_frames):
    """Comfortable/uncomfortable flag for each segment that reaches ``min_frames``."""
    flags = []
    for segment in range(num_segments):
        frame_idx = np.where(segment_ids == segment)[0]
        if len(frame_idx) < min_frames:
            continue
        segment_signals = {key: values[frame_idx] for key, values in signals.items()}
        flags.append(smoothing.within_bounds(segment_signals))
    return flags


def fixed_comfort_flags(episode, per_step=FRAMES_PER_SEGMENT):
    """Per-segment comfort flags for the fixed (time-based) implementation."""
    n_frames = len(episode["angular_velocity"])
    signals = smoothing.compute_signals(
        episode["acceleration"], episode["angular_velocity"],
        episode["forward_vector"], episode["right_vector"])
    if n_frames <= per_step:
        return [smoothing.within_bounds(signals)]
    segment_ids = np.arange(n_frames) // per_step
    num_segments = n_frames // per_step
    return _segment_flags(signals, segment_ids, num_segments, min_frames=per_step)


def distance_comfort_flags(episode, waypoints, num_segments=NUM_DISTANCE_SEGMENTS):
    """Per-segment comfort flags for the distance-based implementation."""
    signals = smoothing.compute_signals(
        episode["acceleration"], episode["angular_velocity"],
        episode["forward_vector"], episode["right_vector"])
    locations = np.asarray(episode["location"])[:, :2]
    progress = route_progress(locations, waypoints)
    segment_ids = np.minimum((progress * num_segments).astype(int), num_segments - 1)
    return _segment_flags(signals, segment_ids, num_segments, min_frames=1)
