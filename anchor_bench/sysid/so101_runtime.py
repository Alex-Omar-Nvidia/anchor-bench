"""Backward-compatible SO-101 SysID entry point."""

from anchor_bench.sysid.runtime import (  # noqa: F401
    _apply_population,
    _resolve_optional_positive_int,
    _resolve_positive_int,
    _resolve_sysid_joint_names,
    _write_summary,
    run_robot_sysid,
)


def run_so101_sysid(*args, **kwargs):
    return run_robot_sysid("so101", *args, **kwargs)


__all__ = [
    "run_robot_sysid",
    "run_so101_sysid",
]
