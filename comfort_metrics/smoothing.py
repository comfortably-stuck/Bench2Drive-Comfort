"""Kinematic comfort signals and thresholds, following nuPlan's calibration.

Bench2Drive's comfort metric follows nuPlan (Caesar et al., 2021): six
kinematic signals are derived from the ego trajectory and checked against
fixed thresholds. This module computes those signals once for a whole
episode (rather than independently per segment), which avoids the
smoothing edge artifacts that appear at segment boundaries when each
segment is smoothed in isolation.
"""

import numpy as np
from scipy.signal import savgol_filter

# nuPlan-calibrated comfort thresholds (Caesar et al., 2021).
MAX_ABS_LON_JERK = 4.13     # m/s^3
MAX_ABS_MAG_JERK = 8.37     # m/s^3
MAX_ABS_LAT_ACCEL = 4.89    # m/s^2
MAX_LON_ACCEL = 2.40        # m/s^2
MIN_LON_ACCEL = -4.05       # m/s^2
MAX_ABS_YAW_ACCEL = 1.93    # rad/s^2
MAX_ABS_YAW_RATE = 0.95     # rad/s

# nuPlan operates at 10 Hz, smoothing acceleration over an 8-frame window and
# computing jerk over 15 frames (0.8 s / 1.5 s). CARLA logs at 20 Hz, so the
# window lengths are doubled to preserve these physical time spans.
ACCEL_WINDOW = 16
JERK_WINDOW = 30
POLY_ORDER = 2
TIME_STEP = 0.05  # s, CARLA's logging interval


def compute_signals(acceleration, angular_velocity, forward_vector, right_vector,
                     accel_window=ACCEL_WINDOW, jerk_window=JERK_WINDOW,
                     poly_order=POLY_ORDER, time_step=TIME_STEP):
    """Derive the six comfort signals for one episode's raw kinematics.

    ``acceleration``, ``forward_vector`` and ``right_vector`` are logged as
    3D CARLA vectors; only the ground-plane (x, y) components are used.
    ``angular_velocity`` is logged in degrees/second and converted to
    radians/second to match nuPlan's thresholds.
    """
    accel_window = min(accel_window, len(acceleration))
    jerk_window = min(jerk_window, len(acceleration))

    accel_xy = np.asarray(acceleration)[:, :2]
    forward_xy = np.asarray(forward_vector)[:, :2]
    right_xy = np.asarray(right_vector)[:, :2]
    yaw_rate = np.deg2rad(np.asarray(angular_velocity)[:, 2])

    lon_accel = np.einsum("ij,ij->i", accel_xy, forward_xy)
    lat_accel = np.einsum("ij,ij->i", accel_xy, right_xy)
    mag_accel = np.hypot(accel_xy[:, 0], accel_xy[:, 1])

    def smooth(signal, window, deriv=0):
        return savgol_filter(signal, window_length=window, polyorder=poly_order,
                              deriv=deriv, delta=time_step, axis=-1)

    yaw_accel = smooth(yaw_rate, jerk_window, deriv=1)
    yaw_rate = smooth(yaw_rate, accel_window)
    lon_accel = smooth(lon_accel, accel_window)
    lat_accel = smooth(lat_accel, accel_window)
    mag_accel = smooth(mag_accel, accel_window)
    lon_jerk = smooth(lon_accel, jerk_window, deriv=1)
    mag_jerk = smooth(mag_accel, jerk_window, deriv=1)

    return {
        "lon_accel": lon_accel,
        "lat_accel": lat_accel,
        "lon_jerk": lon_jerk,
        "mag_jerk": mag_jerk,
        "yaw_accel": yaw_accel,
        "yaw_rate": yaw_rate,
    }


def within_bounds(signals):
    """True iff every frame of every signal stays within its comfort threshold."""
    checks = (
        (signals["lon_accel"], MIN_LON_ACCEL, MAX_LON_ACCEL),
        (signals["lat_accel"], -MAX_ABS_LAT_ACCEL, MAX_ABS_LAT_ACCEL),
        (signals["mag_jerk"], -MAX_ABS_MAG_JERK, MAX_ABS_MAG_JERK),
        (signals["lon_jerk"], -MAX_ABS_LON_JERK, MAX_ABS_LON_JERK),
        (signals["yaw_accel"], -MAX_ABS_YAW_ACCEL, MAX_ABS_YAW_ACCEL),
        (signals["yaw_rate"], -MAX_ABS_YAW_RATE, MAX_ABS_YAW_RATE),
    )
    return all(np.all((values > lo) & (values < hi)) for values, lo, hi in checks)
