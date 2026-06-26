from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from anchor_bench.core.paths import repo_root


@dataclass(frozen=True)
class SimulationTiming:
    physics_freq: int
    control_freq: int
    render_freq: int

    @property
    def physics_dt(self) -> float:
        return 1.0 / self.physics_freq

    @property
    def control_dt(self) -> float:
        return 1.0 / self.control_freq

    @property
    def control_divisor(self) -> int:
        return self.physics_freq // self.control_freq

    @property
    def render_interval(self) -> int:
        return self.physics_freq // self.render_freq


def _positive_int(name: str, value: Any, context: str) -> int:
    resolved = int(value)
    if resolved < 1:
        raise ValueError(f"{context}.{name} must be >= 1")
    return resolved


def resolve_simulation_timing(sim_cfg: Mapping[str, Any] | None, context: str) -> SimulationTiming:
    cfg = sim_cfg or {}
    physics_freq = _positive_int("physics_freq", cfg.get("physics_freq", 500), context)
    control_freq = _positive_int("control_freq", cfg.get("control_freq", physics_freq), context)
    render_freq = _positive_int("render_freq", cfg.get("render_freq", control_freq), context)
    if physics_freq % control_freq != 0:
        raise ValueError(f"{context} requires physics_freq divisible by control_freq")
    if physics_freq % render_freq != 0:
        raise ValueError(f"{context} requires physics_freq divisible by render_freq")
    return SimulationTiming(
        physics_freq=physics_freq,
        control_freq=control_freq,
        render_freq=render_freq,
    )


def defaulted_value(explicit: Any, default: Any, fallback: Any = None) -> Any:
    return explicit if explicit is not None else default if default is not None else fallback


def resolve_required_text(explicit: Any, default: Any, fallback: Any, label: str) -> str:
    value = defaulted_value(explicit, default, fallback)
    if value is None or str(value) == "":
        raise ValueError(f"{label} is required; pass it explicitly or set it in run.yaml")
    return str(value)


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return repo_root() / path


def resolve_repo_path_text(value: str | Path) -> str:
    return str(resolve_repo_path(value))
