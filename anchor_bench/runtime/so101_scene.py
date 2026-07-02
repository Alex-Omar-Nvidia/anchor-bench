"""Backward-compatible alias for the robot-parameterized scene module."""

import sys

from anchor_bench.runtime import robot_scene as _robot_scene

sys.modules[__name__] = _robot_scene
