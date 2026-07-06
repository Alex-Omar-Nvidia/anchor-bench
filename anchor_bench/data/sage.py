from __future__ import annotations

import ast
import csv
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from anchor_bench.data.motion import JointLayout, MotionData, MotionSignal
from anchor_bench.data.validation import validate_sage_dir


def load_joint_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_vector(value: str) -> list[float]:
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, list):
        raise ValueError(f"expected vector list, got {value!r}")
    result = [float(item) for item in parsed]
    if not np.all(np.isfinite(result)):
        raise ValueError("vector contains non-finite values")
    return result


def load_vector_csv(
    path: Path,
    columns: tuple[str, ...],
    *,
    row_type: str | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    timestamps: list[float] = []
    vectors: dict[str, list[list[float]]] = {column: [] for column in columns}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = set(reader.fieldnames or [])
        missing = [column for column in ("timestamp", *columns) if column not in fieldnames]
        if missing:
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
        for row in reader:
            if row_type is not None and row.get("type") not in (None, "", row_type):
                continue
            timestamps.append(float(row["timestamp"]))
            for column in columns:
                vectors[column].append(parse_vector(row[column]))
    return np.asarray(timestamps, dtype=float), {
        column: np.asarray(values, dtype=float) for column, values in vectors.items()
    }


def _time_scale(metadata: dict[str, Any]) -> float:
    unit = metadata.get("time_unit")
    if unit == "seconds":
        return 1.0
    if unit == "microseconds":
        return 1e-6
    raise ValueError("metadata.yaml time_unit must be one of ['microseconds', 'seconds']")


def _sorted_signal(
    timestamps: np.ndarray,
    values: np.ndarray,
    *,
    scale: float,
    unit: str,
    name: str,
) -> MotionSignal:
    if values.ndim != 2:
        raise ValueError(f"{name} must be a 2-D vector trace")
    order = np.argsort(timestamps, kind="stable")
    return MotionSignal(
        time=np.asarray(timestamps, dtype=float)[order] * scale,
        values=np.asarray(values, dtype=float)[order],
        unit=unit,
        name=name,
    )


def load_sage_motion(
    data_dir: str | Path,
    *,
    joint_names: Sequence[str] | None = None,
    target_dt: float | None = None,
    require_velocity: bool = False,
    require_effort: bool = False,
) -> MotionData:
    """Load and normalize one SAGE motion into the shared motion model."""

    root = Path(data_dir)
    metadata = validate_sage_dir(root)
    layout = JointLayout(tuple(load_joint_list(root / "joint_list.txt")))
    control_time, control_vectors = load_vector_csv(root / "control.csv", ("positions",), row_type="CONTROL")
    state_path = root / "state_motor.csv"
    with state_path.open(newline="", encoding="utf-8") as stream:
        state_fields = set(csv.DictReader(stream).fieldnames or [])
    state_columns = ["positions"]
    for optional in ("velocities", "torques"):
        if optional in state_fields:
            state_columns.append(optional)
    if require_velocity and "velocities" not in state_columns:
        raise ValueError(f"{state_path} missing required column: velocities")
    if require_effort and "torques" not in state_columns:
        raise ValueError(f"{state_path} missing required column: torques")
    state_time, state_vectors = load_vector_csv(state_path, tuple(state_columns), row_type="STATE_MOTOR")

    scale = _time_scale(metadata)
    normalized_metadata = dict(metadata)
    normalized_metadata["source_time_unit"] = metadata["time_unit"]
    normalized_metadata["time_unit"] = "seconds"
    motion = MotionData(
        joints=layout,
        command_position=_sorted_signal(
            control_time,
            control_vectors["positions"],
            scale=scale,
            unit=str(metadata["position_unit"]),
            name="command_position",
        ),
        position=_sorted_signal(
            state_time,
            state_vectors["positions"],
            scale=scale,
            unit=str(metadata["position_unit"]),
            name="position",
        ),
        velocity=(
            _sorted_signal(
                state_time,
                state_vectors["velocities"],
                scale=scale,
                unit=str(metadata["velocity_unit"]),
                name="velocity",
            )
            if "velocities" in state_vectors
            else None
        ),
        effort=(
            _sorted_signal(
                state_time,
                state_vectors["torques"],
                scale=scale,
                unit=str(metadata["torque_unit"]),
                name="effort",
            )
            if "torques" in state_vectors
            else None
        ),
        metadata=normalized_metadata,
        source=root,
    )
    if joint_names is not None:
        motion = motion.select_joints(joint_names)
    if target_dt is not None:
        motion = motion.resample(float(target_dt))
    return motion
