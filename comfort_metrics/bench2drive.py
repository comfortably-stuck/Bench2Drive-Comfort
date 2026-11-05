"""Resolve the Bench2Drive checkout used by the evaluation helpers."""

import os


def get_bench2drive_root():
    """Return ``BENCH2DRIVE_ROOT`` or this repository's Bench2Drive submodule."""
    root = os.environ.get("BENCH2DRIVE_ROOT")
    if root:
        return os.path.abspath(os.path.expanduser(root))
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "Bench2Drive")
