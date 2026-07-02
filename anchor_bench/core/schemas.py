
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from anchor_bench.core.experiment_schema import (
    ExperimentActuatorModel,
    ExperimentAnalysis,
    ExperimentAnalysisPlots,
    ExperimentBenchmark,
    ExperimentDataset,
    ExperimentFile,
    ExperimentOutputs,
)
from anchor_bench.core.run_schema import (
    AnalysisDefaults,
    BenchmarkDefaults,
    CMAESConfig,
    ConfigSection,
    RobotRunFile,
    SimulationDefaults,
    SysIdDefaults,
    TrainingDefaults,
)


CONTROLLERS = {"pd", "pid", "mlp", "lstm", "gru", "fmu", "torque_passthrough"}
GRU_INPUT_COLUMNS = {"position", "position_error", "velocity", "solver_pd"}
CLAMPS = {"effort", "velocity", "dc_motor", "position", "none"}

_CONTROLLER_KNOWN_KEYS = {"type", "parameters", "source", "network_file"}
_RESIDUAL_KNOWN_KEYS = {"type", "network_file", "stats_file", "input_columns", "output_column", "source", "parameters"}
_DELAY_KNOWN_KEYS = {"duration_ms"}
_CLAMP_KNOWN_KEYS = {"type", "parameters"}
_ACTUATOR_SPEC_KNOWN_KEYS = {
    "name", "joints", "controller", "delay", "clamps",
    "physical_parameters", "residual",
}
_BOUNDS_RANGE_KNOWN_KEYS = {"lower", "upper"}


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ValueError(f"{context} missing required key '{key}'")
    return mapping[key]


def _parse_column_list(value: Any, context: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        columns = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple)):
        columns = [str(item).strip() for item in value]
    else:
        raise ValueError(f"{context} must be a string or list of strings")
    columns = [column for column in columns if column]
    if not columns:
        raise ValueError(f"{context} must contain at least one column")
    return columns


def _validate_gru_columns(columns: Any, context: str) -> list[str]:
    parsed = _parse_column_list(columns, context)
    unsupported = sorted(set(parsed) - GRU_INPUT_COLUMNS)
    if unsupported:
        raise ValueError(f"unsupported GRU input columns: {', '.join(unsupported)}")
    return parsed


@dataclass(frozen=True)
class ControllerSpec:
    type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    network_file: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "ControllerSpec":
        unknown = sorted(set(data) - _CONTROLLER_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        ctype = _require(data, "type", context)
        if ctype not in CONTROLLERS:
            raise ValueError(f"{context} has unsupported controller '{ctype}'")
        if ctype == "gru" and not data.get("network_file"):
            raise ValueError(f"{context}.type 'gru' requires network_file")
        parameters = dict(data.get("parameters", {}))
        if ctype == "gru" and "input_columns" in parameters:
            parameters["input_columns"] = _validate_gru_columns(parameters["input_columns"], f"{context}.parameters.input_columns")
        return cls(
            type=ctype,
            parameters=parameters,
            source=data.get("source"),
            network_file=data.get("network_file"),
        )


@dataclass(frozen=True)
class ResidualSpec:
    type: str
    network_file: str
    stats_file: str | None = None
    input_columns: list[str] = field(default_factory=lambda: ["position", "position_error", "velocity"])
    output_column: str = "torque_residual"
    source: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "ResidualSpec":
        unknown = sorted(set(data) - _RESIDUAL_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        rtype = _require(data, "type", context)
        if rtype != "gru":
            raise ValueError(f"{context}.type {rtype!r} must be 'gru'")
        network_file = _require(data, "network_file", context)
        columns = _validate_gru_columns(
            data.get("input_columns", ["position", "position_error", "velocity"]),
            f"{context}.input_columns",
        )
        output_column = str(data.get("output_column", "torque_residual"))
        return cls(
            type=str(rtype),
            network_file=str(network_file),
            stats_file=data.get("stats_file"),
            input_columns=columns,
            output_column=output_column,
            source=data.get("source"),
            parameters=dict(data.get("parameters", {})),
        )


@dataclass(frozen=True)
class DelaySpec:
    duration_ms: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, context: str = "delay") -> "DelaySpec":
        if not data:
            return cls()
        unknown = sorted(set(data) - _DELAY_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        return cls(duration_ms=float(data.get("duration_ms", 0.0)))


@dataclass(frozen=True)
class ClampingSpec:
    type: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "ClampingSpec":
        unknown = sorted(set(data) - _CLAMP_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        ctype = _require(data, "type", context)
        if ctype not in CLAMPS:
            raise ValueError(f"{context} has unsupported clamp '{ctype}'")
        return cls(type=ctype, parameters=dict(data.get("parameters", {})))


@dataclass(frozen=True)
class ActuatorSpec:
    name: str
    joints: list[str]
    controller: ControllerSpec
    delay: DelaySpec = field(default_factory=DelaySpec)
    clamps: list[ClampingSpec] = field(default_factory=list)
    physical_parameters: dict[str, Any] = field(default_factory=dict)
    residual: ResidualSpec | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "ActuatorSpec":
        if "model_type" in data:
            raise ValueError(f"{context} uses legacy model_type")
        unknown = sorted(set(data) - _ACTUATOR_SPEC_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        return cls(
            name=_require(data, "name", context),
            joints=list(_require(data, "joints", context)),
            controller=ControllerSpec.from_dict(_require(data, "controller", context), f"{context}.controller"),
            delay=DelaySpec.from_dict(data.get("delay"), f"{context}.delay"),
            clamps=[
                ClampingSpec.from_dict(item, f"{context}.clamps[{idx}]")
                for idx, item in enumerate(data.get("clamps", []))
            ],
            physical_parameters=dict(data.get("physical_parameters", {})),
            residual=ResidualSpec.from_dict(data["residual"], f"{context}.residual") if data.get("residual") else None,
        )


@dataclass(frozen=True)
class ActuatorFile:
    schema_version: int
    backend: str
    actuators: list[ActuatorSpec]

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str | Path) -> "ActuatorFile":
        text_context = str(source)
        if "model_type" in data:
            raise ValueError(f"{text_context} uses legacy model_type")
        schema_version = int(_require(data, "schema_version", text_context))
        if schema_version < 2:
            raise ValueError(f"{text_context} schema_version must be >= 2")
        backend = _require(data, "backend", text_context)
        if backend != "newton":
            raise ValueError(f"{text_context} backend must be 'newton'")
        actuators = [
            ActuatorSpec.from_dict(item, f"{text_context}.actuators[{idx}]")
            for idx, item in enumerate(_require(data, "actuators", text_context))
        ]
        return cls(schema_version=schema_version, backend=backend, actuators=actuators)


_ROBOT_KNOWN_KEYS = {
    "schema_version", "name", "display_name", "fixed_base", "asset_path",
    "joint_names", "joint_aliases", "actuator_file", "bounds_file",
    "ee_frame", "runtime_usd",
}


@dataclass(frozen=True)
class RobotSpec:
    name: str
    display_name: str
    fixed_base: bool
    asset_path: str
    joint_names: list[str]
    joint_aliases: dict[str, str]
    actuator_file: str
    bounds_file: str
    ee_frame: str | None = None
    runtime_usd: str | None = None
    schema_version: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RobotSpec":
        if "model_type" in data:
            raise ValueError("robot uses legacy model_type")
        unknown = sorted(set(data) - _ROBOT_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"robot has unknown keys: {', '.join(unknown)}")
        schema_version = int(_require(data, "schema_version", "robot"))
        if schema_version < 1:
            raise ValueError("robot schema_version must be >= 1")
        joints = list(_require(data, "joint_names", "robot"))
        return cls(
            name=_require(data, "name", "robot"),
            display_name=data.get("display_name", data["name"]),
            fixed_base=bool(data.get("fixed_base", True)),
            asset_path=_require(data, "asset_path", "robot"),
            joint_names=joints,
            joint_aliases=dict(data.get("joint_aliases", {})),
            actuator_file=data.get("actuator_file", "actuators.yaml"),
            bounds_file=data.get("bounds_file", "bounds.yaml"),
            ee_frame=data.get("ee_frame"),
            runtime_usd=data.get("runtime_usd"),
            schema_version=schema_version,
        )


@dataclass(frozen=True)
class BoundsRange:
    lower: float
    upper: float

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "BoundsRange":
        unknown = sorted(set(data) - _BOUNDS_RANGE_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        lower = float(_require(data, "lower", context))
        upper = float(_require(data, "upper", context))
        if upper < lower:
            raise ValueError(f"{context}: upper ({upper}) must be >= lower ({lower})")
        return cls(lower=lower, upper=upper)


_BOUNDS_KNOWN_KEYS = {"schema_version", "mirror", "joint_types", "parameters", "fixed"}


@dataclass(frozen=True)
class SysIdBoundsFile:
    schema_version: int
    mirror: bool
    joint_types: list[str]
    parameters: dict[str, BoundsRange]
    fixed: dict[str, float]

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str | Path) -> "SysIdBoundsFile":
        text_context = str(source)
        if "model_type" in data:
            raise ValueError(f"{text_context} uses legacy model_type")
        unknown = sorted(set(data) - _BOUNDS_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{text_context} has unknown keys: {', '.join(unknown)}")
        schema_version = int(_require(data, "schema_version", text_context))
        if schema_version < 2:
            raise ValueError(f"{text_context} schema_version must be >= 2")
        parameters_raw = _require(data, "parameters", text_context)
        if not isinstance(parameters_raw, dict) or not parameters_raw:
            raise ValueError(f"{text_context}.parameters must be a non-empty mapping")
        parameters = {
            str(name): BoundsRange.from_dict(value, f"{text_context}.parameters.{name}")
            for name, value in parameters_raw.items()
        }
        joint_types = list(_require(data, "joint_types", text_context))
        if not joint_types:
            raise ValueError(f"{text_context}.joint_types must be non-empty")
        return cls(
            schema_version=schema_version,
            mirror=bool(data.get("mirror", False)),
            joint_types=joint_types,
            parameters=parameters,
            fixed={str(k): float(v) for k, v in (data.get("fixed") or {}).items()},
        )


@dataclass(frozen=True)
class SysIdRunConfig:
    robot: str
    data: str | None = None
    output: str | None = None
    dry_run: bool = True
    headless: bool = False
    num_envs: int | None = None
    max_iter: int | None = None
    max_trajectory_len: int | None = None
    seed: int | None = None


@dataclass(frozen=True)
class TrainActuatorRunConfig:
    robot: str
    model: str | None = None
    data: str | None = None
    output: str | None = None
    joint_type: str | None = None
    input_columns: list[str] | None = None
    target_column: str | None = None
    dry_run: bool = True
    skip_optuna: bool | None = None
    trials: int | None = None
    trial_epochs: int | None = None
    final_epochs: int | None = None
    n_streams: int | None = None
    noise_std: float | None = None
    seed: int | None = None


@dataclass(frozen=True)
class BenchmarkRunConfig:
    robot: str
    motion: str | None = None
    output: str | None = None
    dry_run: bool = True
    headless: bool = False
    motion_name: str | None = None
    actuator_params: str | None = None
    dataset: str | None = None
    actuator_model: str | None = None
    seed: int | None = None

__all__ = [
    "ActuatorFile",
    "ActuatorSpec",
    "AnalysisDefaults",
    "BenchmarkDefaults",
    "BenchmarkRunConfig",
    "BoundsRange",
    "CMAESConfig",
    "ClampingSpec",
    "ConfigSection",
    "ControllerSpec",
    "DelaySpec",
    "ExperimentActuatorModel",
    "ExperimentAnalysis",
    "ExperimentAnalysisPlots",
    "ExperimentBenchmark",
    "ExperimentDataset",
    "ExperimentFile",
    "ExperimentOutputs",
    "ResidualSpec",
    "RobotRunFile",
    "RobotSpec",
    "SimulationDefaults",
    "SysIdBoundsFile",
    "SysIdDefaults",
    "SysIdRunConfig",
    "TrainingDefaults",
    "TrainActuatorRunConfig",
]
