from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPERIMENT_ACTUATOR_TYPES = {"pd", "pid", "mlp", "lstm", "gru", "fmu", "torque_passthrough", "implicit"}
EXPERIMENT_BENCHMARK_PARAMS = {"initial", "fitted"}

DatasetMotion = str | dict[str, str]
DatasetMotionSelection = str | list[DatasetMotion] | None
AnalysisSelector = str | list[str] | None

def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ValueError(f"{context} missing required key '{key}'")
    return mapping[key]



_EXPERIMENT_KNOWN_KEYS = {
    "schema_version", "robot", "outputs", "seeds", "benchmark",
    "datasets", "actuator_models", "analysis",
}
_EXPERIMENT_OUTPUTS_KEYS = {"benchmark", "analysis"}
_EXPERIMENT_BENCHMARK_KEYS = {"num_envs", "headless"}
_EXPERIMENT_DATASET_KEYS = {"real_root", "motions"}
_EXPERIMENT_ACTUATOR_MODEL_KEYS = {
    "type", "initial_params", "fitted_params", "benchmark_params",
}
_EXPERIMENT_ANALYSIS_KEYS = {
    "seeds", "datasets", "motions", "actuator_models", "plots",
}
_EXPERIMENT_ANALYSIS_PLOT_KEYS = {"joints", "end_effector", "require_end_effector"}


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _parse_seeds(value: Any, context: str) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return [int(seed) for seed in value]


def _parse_selector(value: Any, context: str) -> AnalysisSelector:
    if value is None or isinstance(value, str):
        return value
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list or string")
    return [str(item) for item in value]


def _parse_dataset_motions(value: Any, context: str) -> DatasetMotionSelection:
    if value is None or isinstance(value, str):
        return value
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list or string")
    motions: list[DatasetMotion] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            motions.append(item)
            continue
        if not isinstance(item, dict):
            raise ValueError(f"{context}[{index}] must be a string or mapping")
        unknown = sorted(set(item) - {"name", "motion", "path"})
        if unknown:
            raise ValueError(f"{context}[{index}] has unknown keys: {', '.join(unknown)}")
        motions.append({str(key): str(entry) for key, entry in item.items()})
    return motions


@dataclass(frozen=True)
class ExperimentOutputs:
    benchmark: str | None = None
    analysis: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, context: str) -> "ExperimentOutputs":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError(f"{context} must be a mapping")
        unknown = sorted(set(data) - _EXPERIMENT_OUTPUTS_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        return cls(
            benchmark=str(data["benchmark"]) if "benchmark" in data else None,
            analysis=str(data["analysis"]) if "analysis" in data else None,
        )

    def to_dict(self) -> dict[str, str]:
        return _without_none({"benchmark": self.benchmark, "analysis": self.analysis})


@dataclass(frozen=True)
class ExperimentBenchmark:
    num_envs: int | None = None
    headless: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, context: str) -> "ExperimentBenchmark":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError(f"{context} must be a mapping")
        unknown = sorted(set(data) - _EXPERIMENT_BENCHMARK_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        num_envs = int(data["num_envs"]) if "num_envs" in data else None
        if num_envs is not None and num_envs < 1:
            raise ValueError(f"{context}.num_envs must be >= 1")
        headless = data.get("headless")
        if headless is not None and not isinstance(headless, bool):
            raise ValueError(f"{context}.headless must be a boolean")
        return cls(num_envs=num_envs, headless=headless)

    def to_dict(self) -> dict[str, Any]:
        return _without_none({"num_envs": self.num_envs, "headless": self.headless})


@dataclass(frozen=True)
class ExperimentDataset:
    real_root: str
    motions: DatasetMotionSelection = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "ExperimentDataset":
        if not isinstance(data, dict):
            raise ValueError(f"{context} must be a mapping")
        unknown = sorted(set(data) - _EXPERIMENT_DATASET_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        return cls(
            real_root=str(_require(data, "real_root", context)),
            motions=_parse_dataset_motions(data.get("motions"), f"{context}.motions"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_none({"real_root": self.real_root, "motions": self.motions})


@dataclass(frozen=True)
class ExperimentActuatorModel:
    type: str
    initial_params: str | None = None
    fitted_params: str | None = None
    benchmark_params: str = "fitted"

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> "ExperimentActuatorModel":
        if "model_type" in data:
            raise ValueError(f"{context} uses legacy model_type")
        unknown = sorted(set(data) - _EXPERIMENT_ACTUATOR_MODEL_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        actuator_type = _require(data, "type", context)
        if actuator_type not in EXPERIMENT_ACTUATOR_TYPES:
            raise ValueError(
                f"{context}.type {actuator_type!r} must be one of "
                f"{sorted(EXPERIMENT_ACTUATOR_TYPES)}"
            )
        benchmark_params = str(data.get("benchmark_params", "fitted"))
        if benchmark_params not in EXPERIMENT_BENCHMARK_PARAMS:
            raise ValueError(
                f"{context}.benchmark_params {benchmark_params!r} must be one of "
                f"{sorted(EXPERIMENT_BENCHMARK_PARAMS)}"
            )
        return cls(
            type=actuator_type,
            initial_params=data.get("initial_params"),
            fitted_params=data.get("fitted_params"),
            benchmark_params=benchmark_params,
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "type": self.type,
                "initial_params": self.initial_params,
                "fitted_params": self.fitted_params,
                "benchmark_params": self.benchmark_params,
            }
        )


@dataclass(frozen=True)
class ExperimentAnalysisPlots:
    joints: bool | None = None
    end_effector: bool | None = None
    require_end_effector: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, context: str) -> "ExperimentAnalysisPlots":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError(f"{context} must be a mapping")
        unknown = sorted(set(data) - _EXPERIMENT_ANALYSIS_PLOT_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        for key, value in data.items():
            if not isinstance(value, bool):
                raise ValueError(f"{context}.{key} must be a boolean")
        return cls(
            joints=data.get("joints"),
            end_effector=data.get("end_effector"),
            require_end_effector=data.get("require_end_effector"),
        )

    def to_dict(self) -> dict[str, bool]:
        return _without_none(
            {
                "joints": self.joints,
                "end_effector": self.end_effector,
                "require_end_effector": self.require_end_effector,
            }
        )


@dataclass(frozen=True)
class ExperimentAnalysis:
    seeds: list[int] | None = None
    datasets: AnalysisSelector = None
    motions: AnalysisSelector = None
    actuator_models: AnalysisSelector = None
    plots: ExperimentAnalysisPlots | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, context: str) -> "ExperimentAnalysis":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError(f"{context} must be a mapping")
        unknown = sorted(set(data) - _EXPERIMENT_ANALYSIS_KEYS)
        if unknown:
            raise ValueError(f"{context} has unknown keys: {', '.join(unknown)}")
        plots = (
            ExperimentAnalysisPlots.from_dict(data["plots"], f"{context}.plots")
            if "plots" in data
            else None
        )
        return cls(
            seeds=_parse_seeds(data.get("seeds"), f"{context}.seeds"),
            datasets=_parse_selector(data.get("datasets"), f"{context}.datasets"),
            motions=_parse_selector(data.get("motions"), f"{context}.motions"),
            actuator_models=_parse_selector(data.get("actuator_models"), f"{context}.actuator_models"),
            plots=plots,
        )

    def to_dict(self) -> dict[str, Any]:
        result = _without_none(
            {
                "seeds": self.seeds,
                "datasets": self.datasets,
                "motions": self.motions,
                "actuator_models": self.actuator_models,
            }
        )
        if self.plots is not None:
            result["plots"] = self.plots.to_dict()
        return result


@dataclass(frozen=True)
class ExperimentFile:
    schema_version: int
    robot: str
    outputs: ExperimentOutputs
    seeds: list[int] | None
    benchmark: ExperimentBenchmark
    datasets: dict[str, ExperimentDataset]
    actuator_models: dict[str, ExperimentActuatorModel]
    analysis: ExperimentAnalysis

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str | Path) -> "ExperimentFile":
        text_context = str(source)
        if not isinstance(data, dict):
            raise ValueError(f"{text_context} must be a mapping")
        if "model_type" in data:
            raise ValueError(f"{text_context} uses legacy model_type")
        unknown = sorted(set(data) - _EXPERIMENT_KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{text_context} has unknown keys: {', '.join(unknown)}")
        schema_version = int(_require(data, "schema_version", text_context))
        if schema_version < 1:
            raise ValueError(f"{text_context} schema_version must be >= 1")
        robot = str(_require(data, "robot", text_context))

        datasets = data.get("datasets") or {}
        if not isinstance(datasets, dict) or not datasets:
            raise ValueError(
                f"{text_context}.datasets must be a non-empty mapping"
            )
        parsed_datasets = {
            str(name): ExperimentDataset.from_dict(dataset, f"{text_context}.datasets.{name}")
            for name, dataset in datasets.items()
        }

        actuator_models = data.get("actuator_models") or {}
        if not isinstance(actuator_models, dict) or not actuator_models:
            raise ValueError(
                f"{text_context}.actuator_models must be a non-empty mapping"
            )
        parsed_actuator_models = {
            str(name): ExperimentActuatorModel.from_dict(
                model or {}, f"{text_context}.actuator_models.{name}"
            )
            for name, model in actuator_models.items()
        }

        return cls(
            schema_version=schema_version,
            robot=robot,
            outputs=ExperimentOutputs.from_dict(data.get("outputs"), f"{text_context}.outputs"),
            seeds=_parse_seeds(data.get("seeds"), f"{text_context}.seeds"),
            benchmark=ExperimentBenchmark.from_dict(data.get("benchmark"), f"{text_context}.benchmark"),
            datasets=parsed_datasets,
            actuator_models=parsed_actuator_models,
            analysis=ExperimentAnalysis.from_dict(data.get("analysis"), f"{text_context}.analysis"),
        )
