"""Backward-compatible alias for the robot-parameterized analysis runtime."""

import sys

from anchor_bench.analysis import runtime as _runtime

sys.modules[__name__] = _runtime
