"""Backward-compatible imports for the former SO-101-specific config module."""

from anchor_bench.runtime.robot_config import (
    build_implicit_actuator_params,
    load_implicit_actuator_params,
    load_sysid_bounds,
    write_runtime_actuator_yaml,
)

__all__ = [
    "build_implicit_actuator_params",
    "load_implicit_actuator_params",
    "load_sysid_bounds",
    "write_runtime_actuator_yaml",
]
