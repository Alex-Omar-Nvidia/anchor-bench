"""Backward-compatible SO-101 benchmark entry points."""

from anchor_bench.benchmark.runtime import (  # noqa: F401
    RobotBenchmarkMotion,
    _append_benchmark_sample,
    _buffer_substeps,
    _build_run_summary,
    _copy_real_sage,
    _timestamp_us_text,
    _write_sage,
    run_robot_benchmark,
    run_robot_benchmark_batch,
)

So101BenchmarkMotion = RobotBenchmarkMotion


def run_so101_benchmark(*args, **kwargs):
    return run_robot_benchmark("so101", *args, **kwargs)


def run_so101_benchmark_batch(*args, **kwargs):
    return run_robot_benchmark_batch("so101", *args, **kwargs)


__all__ = [
    "So101BenchmarkMotion",
    "run_so101_benchmark",
    "run_so101_benchmark_batch",
]
