from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def validate_sage_dir(data_dir: str | Path) -> dict[str, Any]:
    root = Path(data_dir)
    required = ["control.csv", "state_motor.csv", "joint_list.txt", "metadata.yaml"]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"{root} missing required SAGE files: {', '.join(missing)}")
    metadata = yaml.safe_load((root / "metadata.yaml").read_text(encoding="utf-8")) or {}
    expected = {
        "time_unit": {"microseconds", "seconds"},
        "position_unit": {"rad"},
        "velocity_unit": {"rad/s"},
        "torque_unit": {"N*m", "Nm"},
    }
    for key, allowed in expected.items():
        if metadata.get(key) not in allowed:
            raise ValueError(f"metadata.yaml {key} must be one of {sorted(allowed)}")
    return metadata
