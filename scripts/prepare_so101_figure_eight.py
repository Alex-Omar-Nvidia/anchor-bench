#!/usr/bin/env python3
"""Download and convert NVIDIA Anchor-Lab SO-101 figure-eight data to SAGE."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml


SOURCE_URL = (
    "https://huggingface.co/datasets/nvidia/Anchor-Lab/resolve/main/"
    "data/so101_arm_50motion/so101-sysid-50motion-train-figure-eight.parquet"
)
SOURCE_COMMIT = "04cd282fadd4ea589c1181c5bb150667859757f6"
SOURCE_SHA256 = "49531adaf02ef0ec468c7593467d45a5718596118fa7834f41e13c07534efe8b"
DEFAULT_SOURCE = Path("inputs/datasets/so101/so101_arm_50motion/so101-sysid-50motion-train-figure-eight.parquet")
DEFAULT_OUTPUT = Path("inputs/datasets/so101/custom_figure8_with_camera")

JOINTS = (
    ("rotation", "Rotation"),
    ("pitch", "Pitch"),
    ("elbow", "Elbow"),
    ("wrist_pitch", "Wrist_Pitch"),
    ("wrist_roll", "Wrist_Roll"),
    ("jaw", "Jaw"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(source: Path) -> None:
    source.parent.mkdir(parents=True, exist_ok=True)
    temporary = source.with_suffix(source.suffix + ".part")
    print(f"downloading {SOURCE_URL}", flush=True)
    try:
        urllib.request.urlretrieve(SOURCE_URL, temporary)
        temporary.replace(source)
    finally:
        temporary.unlink(missing_ok=True)


def _signal_frame(frame: Any, suffix: str) -> Any:
    sources = [source for source, _ in JOINTS]
    selected = frame[frame["field"].isin([f"{joint}/{suffix}" for joint in sources])].copy()
    if selected.empty:
        raise ValueError(f"source parquet has no */{suffix} signals")
    selected["joint"] = selected["field"].str.removesuffix(f"/{suffix}")
    if selected.duplicated(["time_ns", "joint"]).any():
        raise ValueError(f"source parquet has duplicate */{suffix} samples")
    wide = selected.pivot(index="time_ns", columns="joint", values="value").sort_index()
    missing = [joint for joint in sources if joint not in wide]
    if missing:
        raise ValueError(f"source parquet */{suffix} signals are missing joints: {', '.join(missing)}")
    wide = wide[sources]
    wide.columns = [canonical for _, canonical in JOINTS]
    if wide.isna().any().any():
        raise ValueError(f"source parquet */{suffix} signals contain incomplete samples")
    return wide


def _vector_rows(frame: Any, row_type: str, origin_ns: int, *signals: Any) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for timestamp_ns, values in frame.iterrows():
        timestamp_s = round((int(timestamp_ns) - origin_ns) / 1e9, 12)
        row: list[Any] = [row_type, timestamp_s, [float(value) for value in values.tolist()]]
        for signal in signals:
            row.append([float(value) for value in signal.loc[timestamp_ns].tolist()])
        rows.append(row)
    return rows


def convert(source: Path, output: Path) -> None:
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise RuntimeError("conversion requires pandas and pyarrow; install anchor-bench[full]") from exc

    frame = pd.read_parquet(source, columns=["time_ns", "experiment", "field", "value"])
    experiments = sorted(str(value) for value in frame["experiment"].dropna().unique())
    if len(experiments) != 1:
        raise ValueError(f"expected one experiment in {source}, found {experiments}")

    commands = _signal_frame(frame, "command_q")
    positions = _signal_frame(frame, "actual_q")
    velocities = _signal_frame(frame, "dq")
    torques = _signal_frame(frame, "tau_abs")
    load_signals = _signal_frame(frame, "present_load_raw")
    state_index = (
        positions.index.intersection(velocities.index).intersection(torques.index).intersection(load_signals.index)
    )
    if state_index.empty:
        raise ValueError("actual_q, dq, tau_abs, and present_load_raw signals have no common timestamps")
    positions = positions.loc[state_index]
    velocities = velocities.loc[state_index]
    torques = torques.loc[state_index] * load_signals.loc[state_index].map(
        lambda value: -1.0 if value < 0.0 else 1.0 if value > 0.0 else 0.0
    )
    origin_ns = int(min(commands.index.min(), state_index.min()))

    output.mkdir(parents=True, exist_ok=True)
    (output / "joint_list.txt").write_text(
        "\n".join(canonical for _, canonical in JOINTS) + "\n",
        encoding="utf-8",
    )
    with (output / "control.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["type", "timestamp", "positions"])
        writer.writerows(_vector_rows(commands, "CONTROL", origin_ns))
    with (output / "state_motor.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["type", "timestamp", "positions", "velocities", "torques"])
        writer.writerows(_vector_rows(positions, "STATE_MOTOR", origin_ns, velocities, torques))
    metadata = {
        "schema": "sage",
        "time_unit": "seconds",
        "position_unit": "rad",
        "velocity_unit": "rad/s",
        "torque_unit": "N*m",
        "source": experiments[0],
        "source_url": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_sha256": _sha256(source),
        "source_fields": {
            "control_positions": "*/command_q",
            "state_positions": "*/actual_q",
            "state_velocities": "*/dq",
            "state_torque_magnitude": "*/tau_abs",
            "state_torque_sign": "*/present_load_raw",
        },
        "torque_semantics": "tau_abs magnitude multiplied by sign(present_load_raw)",
        "unit_note": (
            "The Anchor-Lab dataset card does not provide a full per-field data dictionary. "
            "Validate q/dq/tau_abs units against the source hardware calibration before fitting."
        ),
    }
    (output / "metadata.yaml").write_text(
        yaml.safe_dump(metadata, sort_keys=False),
        encoding="utf-8",
    )
    print(f"wrote {len(commands)} control rows and {len(positions)} state rows to {output}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args(argv)

    if not args.source.exists():
        if args.no_download:
            parser.error(f"source parquet does not exist: {args.source}")
        _download(args.source)
    digest = _sha256(args.source)
    if digest != SOURCE_SHA256:
        parser.error(f"source SHA-256 mismatch: expected {SOURCE_SHA256}, got {digest}")
    convert(args.source, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
