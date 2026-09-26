"""Projection of ego trajectories onto Bench2Drive route polylines.

The distance-based comfort metric needs to know how far along its route each
logged ego position is. Routes are given as sparse waypoints; this module
turns them into a polyline and projects points onto it to obtain normalized
route progress.
"""

import xml.etree.ElementTree as ET

import numpy as np


def load_route_waypoints(route_xml_path):
    """Parse a Bench2Drive leaderboard route XML into ``{route_id: (N, 2) xy}``."""
    root = ET.parse(route_xml_path).getroot()
    waypoints = {}
    for route in root.iter("route"):
        route_id = route.get("id")
        points = [(float(p.get("x")), float(p.get("y"))) for p in route.iter("position")]
        if route_id is not None and len(points) >= 2:
            waypoints[route_id] = np.asarray(points, dtype=float)
    return waypoints


def route_progress(locations, waypoints):
    """Normalized route progress (0 to 1) of each ``(x, y)`` location.

    Each point is projected onto the nearest segment of the ``waypoints``
    polyline; progress is the arc length up to that projection divided by the
    total route length.
    """
    segment_starts = waypoints[:-1]
    segment_vectors = waypoints[1:] - waypoints[:-1]
    segment_lengths_sq = np.einsum("ij,ij->i", segment_vectors, segment_vectors)
    segment_lengths_sq = np.where(segment_lengths_sq > 0, segment_lengths_sq, 1e-9)
    segment_lengths = np.sqrt(segment_lengths_sq)
    cumulative_length = np.concatenate([[0.0], np.cumsum(segment_lengths)])
    total_length = cumulative_length[-1] if cumulative_length[-1] > 0 else 1e-9

    progress = np.empty(len(locations))
    for i, point in enumerate(locations):
        offsets = point - segment_starts
        t = np.clip(np.einsum("ij,ij->i", offsets, segment_vectors) / segment_lengths_sq, 0.0, 1.0)
        projections = segment_starts + t[:, None] * segment_vectors
        diffs = point - projections
        nearest = int(np.argmin(np.einsum("ij,ij->i", diffs, diffs)))
        progress[i] = (cumulative_length[nearest] + t[nearest] * segment_lengths[nearest]) / total_length
    return np.clip(progress, 0.0, 1.0)
