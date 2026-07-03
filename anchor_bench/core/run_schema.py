from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, StrictBool, field_validator

from anchor_bench.core.config_model import ConfigModel, parse_gru_columns


class CMAESConfig(ConfigModel):
    sigma: float = Field(default=0.5, gt=0.0)
    max_iterations: int = Field(default=200, ge=1)
    epsilon: float | None = Field(default=0.01, ge=0.0)


class ConfigSection(ConfigModel, Mapping[str, Any]):
    """Read-only mapping compatibility for typed run-config sections."""

    def __getitem__(self, key: str) -> Any:
        if key not in type(self).model_fields:
            raise KeyError(key)
        value = getattr(self, key)
        if value is None:
            raise KeyError(key)
        return value

    def __iter__(self) -> Iterator[str]:
        return (name for name in type(self).model_fields if getattr(self, name) is not None)

    def __len__(self) -> int:
        return sum(1 for _ in self)


class SimulationDefaults(ConfigSection):
    physics_freq: int | None = Field(default=None, ge=1)
    control_freq: int | None = Field(default=None, ge=1)
    render_freq: int | None = Field(default=None, ge=1)
    integrator: str | None = None
    solver_iterations: int | None = Field(default=None, ge=1)
    line_search_iterations: int | None = Field(default=None, ge=1)
    ls_iterations: int | None = Field(default=None, ge=1)


class BenchmarkDefaults(ConfigSection):
    dataset: str | None = None
    fix_root: StrictBool | None = None
    buffer_time: float | None = Field(default=None, ge=0.0)
    motion_files: str | None = None
    motion_name: str | None = None
    output_folder: str | None = None
    real_init_pose_sync: StrictBool | None = None


class AnalysisDefaults(ConfigSection):
    output_dir: str | None = None
    sample_dt: float | None = Field(default=None, ge=0.0)
    motion_names: str | list[str] | None = None

    @field_validator("motion_names", mode="before")
    @classmethod
    def _validate_motion_names(cls, value: Any) -> Any:
        if value is None or isinstance(value, str):
            return value
        if not isinstance(value, list):
            raise ValueError("must be a string or list")
        return [str(item) for item in value]


class SysIdDefaults(ConfigSection):
    output_dir: str | None = None
    real_data_dir: str | None = None
    joints: str | list[str] | None = None
    num_envs: int | None = Field(default=None, ge=1)
    buffer_time: float | None = Field(default=None, ge=0.0)
    cmaes: CMAESConfig | None = None

    @field_validator("joints", mode="before")
    @classmethod
    def _validate_joints(cls, value: Any) -> Any:
        if value is None or isinstance(value, str):
            return value
        if not isinstance(value, list):
            raise ValueError("must be a string or list")
        return [str(item) for item in value]


class TrainingDefaults(ConfigSection):
    model: Literal["gru", "hybrid_residual"] | None = None
    real_data_dir: str | None = None
    output_dir: str | None = None
    joint_type: str | None = None
    skip_optuna: StrictBool | None = None
    trials: int | None = Field(default=None, ge=1)
    trial_epochs: int | None = Field(default=None, ge=1)
    final_epochs: int | None = Field(default=None, ge=1)
    n_streams: int | None = Field(default=None, ge=1)
    noise_std: float | None = Field(default=None, ge=0.0)
    seed: int | None = None
    input_columns: list[str] | None = None
    target_column: str | None = None

    @field_validator("input_columns", mode="before")
    @classmethod
    def _validate_input_columns(cls, value: Any) -> list[str] | None:
        return None if value is None else parse_gru_columns(value)


class RobotRunFile(ConfigSection):
    simulation: SimulationDefaults = Field(default_factory=SimulationDefaults)
    benchmark: BenchmarkDefaults = Field(default_factory=BenchmarkDefaults)
    analysis: AnalysisDefaults = Field(default_factory=AnalysisDefaults)
    sysid: SysIdDefaults = Field(default_factory=SysIdDefaults)
    training: TrainingDefaults = Field(default_factory=TrainingDefaults)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None, source: str | Path) -> "RobotRunFile":
        return super().from_dict(data, source)

    def to_dict(self) -> dict[str, Any]:
        return {
            name: section.to_dict()
            for name, section in (
                ("simulation", self.simulation),
                ("benchmark", self.benchmark),
                ("analysis", self.analysis),
                ("sysid", self.sysid),
                ("training", self.training),
            )
            if len(section)
        }
