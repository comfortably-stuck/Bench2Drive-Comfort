"""Standstill benchmark: how much of a route the ego spends stationary.

Uses the same fixed 1-second segmentation as the comfort metric's original
and fixed implementations. A segment counts as a standstill iff the ego's
speed never exceeds ``SPEED_THRESHOLD`` for its whole duration.
"""

import numpy as np

FRAMES_PER_SEGMENT = 20   # 1 s at CARLA's 20 Hz logging rate
TIME_STEP = 0.05          # s, CARLA's logging interval

# Matches the CARLA leaderboard's own criterion for a blocked agent
# (``ActorBlockedTest(min_speed=0.1, ...)``).
SPEED_THRESHOLD = 0.1     # m/s


def compute_speed(locations):
    """Per-frame speed from consecutive ``(x, y)`` location samples.

    Speed is not logged directly, so it is derived via finite differences.
    The first frame reuses the second frame's speed.
    """
    xy = np.asarray(locations, dtype=float)[:, :2]
    if len(xy) < 2:
        return np.zeros(len(xy))
    step_speed = np.linalg.norm(np.diff(xy, axis=0), axis=1) / TIME_STEP
    return np.concatenate([step_speed[:1], step_speed])


def standstill_fraction(locations, per_step=FRAMES_PER_SEGMENT, speed_threshold=SPEED_THRESHOLD):
    """Fraction of fixed-length segments in which the ego never moves."""
    speed = compute_speed(locations)
    n_frames = len(speed)
    if n_frames == 0:
        return None
    stationary = speed < speed_threshold
    if n_frames <= per_step:
        return 1.0 if bool(np.all(stationary)) else 0.0
    num_segments = n_frames // per_step
    flags = [bool(np.all(stationary[s * per_step:(s + 1) * per_step])) for s in range(num_segments)]
    return sum(flags) / len(flags)
