from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

GRU_INPUT_COLUMNS = {"position", "position_error", "velocity", "solver_pd"}
_CMAES_KNOWN_KEYS = {"sigma", "max_iterations", "epsilon"}

def _validate_gru_columns(columns: Any, context: str) -> list[str]:
    if isinstance(columns, str):
        parsed = [item.strip() for item in columns.split(",") if item.strip()]
    elif isinstance(columns, (list, tuple)):
        parsed = [str(item).strip() for item in columns if str(item).strip()]
    else:
        raise ValueError(f"{context} must be a string or list of strings")
    if not parsed:
        raise ValueError(f"{context} must contain at least one column")
    unsupported = sorted(set(parsed) - GRU_INPUT_COLUMNS)
    if unsupported:
        raise ValueError(f"unsupported GRU input columns: {', '.join(unsupported)}")
    return parsed

@dataclass(frozen=True)
class CMAESConfig:
    sigma: float = 0.5
    max_iterations: int = 200
    epsilon: float | None = 0.01

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, context: str) -> "CMAESConfig":
        if not data:
            return cls()
        unknown = sorted(set(data) - _CMAES_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        return cls(
            sigma=float(data.get("sigma", 0.5)),
            max_iterations=int(data.get("max_iterations", 200)),
            epsilon=float(data["epsilon"]) if "epsilon" in data else 0.01,
        )


_RUN_KNOWN_KEYS = {"simulation", "benchmark", "analysis", "sysid", "training"}
_RUN_SIMULATION_KEYS = {
    "physics_freq", "control_freq", "render_freq", "integrator",
    "solver_iterations", "line_search_iterations", "ls_iterations",
}
_RUN_BENCHMARK_KEYS = {
    "dataset", "fix_root", "buffer_time", "motion_files", "motion_name",
    "output_folder", "real_init_pose_sync",
}
_RUN_ANALYSIS_KEYS = {"output_dir", "sample_dt", "motion_names"}
_RUN_SYSID_KEYS = {
    "output_dir", "real_data_dir", "joints", "num_envs", "buffer_time", "cmaes",
}
_TRAINING_MODELS = {"gru", "hybrid_residual"}
_RUN_TRAINING_KEYS = {
    "model", "real_data_dir", "output_dir", "joint_type", "skip_optuna",
    "trials", "trial_epochs", "final_epochs", "n_streams", "noise_std", "seed",
    "input_columns", "target_column",
}


def _section_data(
    data: dict[str, Any],
    section: str,
    source: str,
    known_keys: set[str],
) -> dict[str, Any]:
    value = data.get(section) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{source}.{section} must be a mapping")
    unknown = sorted(set(value) - known_keys)
    if unknown:
        raise ValueError(f"{source}.{section} has unknown keys: {', '.join(unknown)}")
    return value


def _optional_int(data: dict[str, Any], key: str, context: str, *, positive: bool = False) -> int | None:
    if key not in data:
        return None
    value = int(data[key])
    if positive and value < 1:
        raise ValueError(f"{context}.{key} must be >= 1")
    return value


def _optional_float(data: dict[str, Any], key: str, context: str, *, nonnegative: bool = False) -> float | None:
    if key not in data:
        return None
    value = float(data[key])
    if nonnegative and value < 0.0:
        raise ValueError(f"{context}.{key} must be >= 0")
    return value


def _optional_bool(data: dict[str, Any], key: str, context: str) -> bool | None:
    if key not in data:
        return None
    value = data[key]
    if not isinstance(value, bool):
        raise ValueError(f"{context}.{key} must be a boolean")
    return value


class ConfigSection(Mapping[str, Any]):
    """Read-only mapping compatibility for typed run-config sections."""

    def __getitem__(self, key: str) -> Any:
        if key not in {item.name for item in fields(self)}:
            raise KeyError(key)
        value = getattr(self, key)
        if value is None:
            raise KeyError(key)
        return value

    def __iter__(self) -> Iterator[str]:
        return (item.name for item in fields(self) if getattr(self, item.name) is not None)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in self:
            value = getattr(self, key)
            if isinstance(value, ConfigSection):
                result[key] = value.to_dict()
            elif isinstance(value, CMAESConfig):
                result[key] = {
                    "sigma": value.sigma,
                    "max_iterations": value.max_iterations,
                    "epsilon": value.epsilon,
                }
            else:
                result[key] = value
        return result


@dataclass(frozen=True)
class SimulationDefaults(ConfigSection):
    physics_freq: int | None = None
    control_freq: int | None = None
    render_freq: int | None = None
    integrator: str | None = None
    solver_iterations: int | None = None
    line_search_iterations: int | None = None
    ls_iterations: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "SimulationDefaults":
        return cls(
            physics_freq=_optional_int(data, "physics_freq", context, positive=True),
            control_freq=_optional_int(data, "control_freq", context, positive=True),
            render_freq=_optional_int(data, "render_freq", context, positive=True),
            integrator=str(data["integrator"]) if "integrator" in data else None,
            solver_iterations=_optional_int(data, "solver_iterations", context, positive=True),
            line_search_iterations=_optional_int(data, "line_search_iterations", context, positive=True),
            ls_iterations=_optional_int(data, "ls_iterations", context, positive=True),
        )


@dataclass(frozen=True)
class BenchmarkDefaults(ConfigSection):
    dataset: str | None = None
    fix_root: bool | None = None
    buffer_time: float | None = None
    motion_files: str | None = None
    motion_name: str | None = None
    output_folder: str | None = None
    real_init_pose_sync: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "BenchmarkDefaults":
        return cls(
            dataset=str(data["dataset"]) if "dataset" in data else None,
            fix_root=_optional_bool(data, "fix_root", context),
            buffer_time=_optional_float(data, "buffer_time", context, nonnegative=True),
            motion_files=str(data["motion_files"]) if "motion_files" in data else None,
            motion_name=str(data["motion_name"]) if "motion_name" in data else None,
            output_folder=str(data["output_folder"]) if "output_folder" in data else None,
            real_init_pose_sync=_optional_bool(data, "real_init_pose_sync", context),
        )


@dataclass(frozen=True)
class AnalysisDefaults(ConfigSection):
    output_dir: str | None = None
    sample_dt: float | None = None
    motion_names: str | list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "AnalysisDefaults":
        motion_names = data.get("motion_names")
        if motion_names is not None and not isinstance(motion_names, (str, list)):
            raise ValueError(f"{context}.motion_names must be a string or list")
        return cls(
            output_dir=str(data["output_dir"]) if "output_dir" in data else None,
            sample_dt=_optional_float(data, "sample_dt", context, nonnegative=True),
            motion_names=(
                [str(item) for item in motion_names]
                if isinstance(motion_names, list)
                else motion_names
            ),
        )


@dataclass(frozen=True)
class SysIdDefaults(ConfigSection):
    output_dir: str | None = None
    real_data_dir: str | None = None
    joints: str | list[str] | None = None
    num_envs: int | None = None
    buffer_time: float | None = None
    cmaes: CMAESConfig | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "SysIdDefaults":
        joints = data.get("joints")
        if joints is not None and not isinstance(joints, (str, list)):
            raise ValueError(f"{context}.joints must be a string or list")
        return cls(
            output_dir=str(data["output_dir"]) if "output_dir" in data else None,
            real_data_dir=str(data["real_data_dir"]) if "real_data_dir" in data else None,
            joints=[str(item) for item in joints] if isinstance(joints, list) else joints,
            num_envs=_optional_int(data, "num_envs", context, positive=True),
            buffer_time=_optional_float(data, "buffer_time", context, nonnegative=True),
            cmaes=(
                CMAESConfig.from_dict(data.get("cmaes"), f"{context}.cmaes")
                if "cmaes" in data
                else None
            ),
        )


@dataclass(frozen=True)
class TrainingDefaults(ConfigSection):
    model: str | None = None
    real_data_dir: str | None = None
    output_dir: str | None = None
    joint_type: str | None = None
    skip_optuna: bool | None = None
    trials: int | None = None
    trial_epochs: int | None = None
    final_epochs: int | None = None
    n_streams: int | None = None
    noise_std: float | None = None
    seed: int | None = None
    input_columns: list[str] | None = None
    target_column: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "TrainingDefaults":
        model = str(data["model"]) if "model" in data else None
        if model is not None and model not in _TRAINING_MODELS:
            raise ValueError(f"{context}.model {model!r} must be one of {sorted(_TRAINING_MODELS)}")
        return cls(
            model=model,
            real_data_dir=str(data["real_data_dir"]) if "real_data_dir" in data else None,
            output_dir=str(data["output_dir"]) if "output_dir" in data else None,
            joint_type=str(data["joint_type"]) if "joint_type" in data else None,
            skip_optuna=_optional_bool(data, "skip_optuna", context),
            trials=_optional_int(data, "trials", context, positive=True),
            trial_epochs=_optional_int(data, "trial_epochs", context, positive=True),
            final_epochs=_optional_int(data, "final_epochs", context, positive=True),
            n_streams=_optional_int(data, "n_streams", context, positive=True),
            noise_std=_optional_float(data, "noise_std", context, nonnegative=True),
            seed=_optional_int(data, "seed", context),
            input_columns=(
                _validate_gru_columns(data["input_columns"], f"{context}.input_columns")
                if "input_columns" in data
                else None
            ),
            target_column=str(data["target_column"]) if "target_column" in data else None,
        )


@dataclass(frozen=True)
class RobotRunFile(ConfigSection):
    simulation: SimulationDefaults = field(default_factory=SimulationDefaults)
    benchmark: BenchmarkDefaults = field(default_factory=BenchmarkDefaults)
    analysis: AnalysisDefaults = field(default_factory=AnalysisDefaults)
    sysid: SysIdDefaults = field(default_factory=SysIdDefaults)
    training: TrainingDefaults = field(default_factory=TrainingDefaults)

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str | Path) -> "RobotRunFile":
        text_context = str(source)
        if not isinstance(data, dict):
            raise ValueError(f"{text_context} must be a mapping")
        unknown = sorted(set(data) - _RUN_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{text_context} has unknown keys: {', '.join(unknown)}")
        return cls(
            simulation=SimulationDefaults.from_dict(
                _section_data(data, "simulation", text_context, _RUN_SIMULATION_KEYS),
                f"{text_context}.simulation",
            ),
            benchmark=BenchmarkDefaults.from_dict(
                _section_data(data, "benchmark", text_context, _RUN_BENCHMARK_KEYS),
                f"{text_context}.benchmark",
            ),
            analysis=AnalysisDefaults.from_dict(
                _section_data(data, "analysis", text_context, _RUN_ANALYSIS_KEYS),
                f"{text_context}.analysis",
            ),
            sysid=SysIdDefaults.from_dict(
                _section_data(data, "sysid", text_context, _RUN_SYSID_KEYS),
                f"{text_context}.sysid",
            ),
            training=TrainingDefaults.from_dict(
                _section_data(data, "training", text_context, _RUN_TRAINING_KEYS),
                f"{text_context}.training",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            key: section.to_dict()
            for key, section in (
                ("simulation", self.simulation),
                ("benchmark", self.benchmark),
                ("analysis", self.analysis),
                ("sysid", self.sysid),
                ("training", self.training),
            )
            if section
        }
