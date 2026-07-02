from __future__ import annotations

from dataclasses import dataclass

from anchor_bench.core.plan import CommandPlan
from anchor_bench.core.run_config import resolve_repo_path_text, resolve_required_text
from anchor_bench.core.schemas import CMAESConfig, SysIdRunConfig
from anchor_bench.core.versions import load_external_versions
from anchor_bench.robots.registry import get_robot
from anchor_bench.sysid.validation import resolve_optional_positive_int


@dataclass(frozen=True)
class ResolvedSysIdRunConfig:
    robot: str
    data: str
    output: str
    dry_run: bool
    headless: bool
    num_envs: int | None
    max_iter: int
    max_trajectory_len: int | None
    seed: int | None
    config_sources: dict[str, str]


def _config_source(
    explicit: object,
    configured: object,
    *,
    configured_label: str = "run.yaml",
    fallback: str = "fallback",
) -> str:
    if explicit is not None:
        return "cli"
    return configured_label if configured is not None else fallback


def resolve_sysid_run_config(config: SysIdRunConfig) -> ResolvedSysIdRunConfig:
    bundle = get_robot(config.robot)
    sysid_cfg = bundle.run_config.sysid
    cmaes_cfg = sysid_cfg.cmaes or CMAESConfig()
    data = resolve_required_text(config.data, sysid_cfg.real_data_dir, None, "--data")
    output = resolve_required_text(config.output, sysid_cfg.output_dir, f"outputs/sysid/{config.robot}", "--output")
    num_envs = sysid_cfg.num_envs if config.num_envs is None else config.num_envs
    max_iter = cmaes_cfg.max_iterations if config.max_iter is None else config.max_iter
    config_sources = {
        "real_data_dir": _config_source(config.data, sysid_cfg.real_data_dir),
        "output_dir": _config_source(config.output, sysid_cfg.output_dir),
        "num_envs": _config_source(config.num_envs, sysid_cfg.num_envs),
        "max_iter": _config_source(
            config.max_iter,
            cmaes_cfg.max_iterations,
            configured_label="run.yaml.sysid.cmaes.max_iterations",
        ),
        "max_trajectory_len": _config_source(
            config.max_trajectory_len, None, fallback="unset"
        ),
        "seed": _config_source(config.seed, None, fallback="default"),
        "joints": _config_source(None, sysid_cfg.joints),
        "buffer_time": _config_source(None, sysid_cfg.buffer_time),
        "cmaes": _config_source(None, sysid_cfg.cmaes),
    }
    return ResolvedSysIdRunConfig(
        robot=config.robot,
        data=resolve_repo_path_text(data),
        output=resolve_repo_path_text(output),
        dry_run=config.dry_run,
        headless=config.headless,
        num_envs=resolve_optional_positive_int("num_envs", num_envs),
        max_iter=resolve_optional_positive_int("max_iter", max_iter) or cmaes_cfg.max_iterations,
        max_trajectory_len=resolve_optional_positive_int("max_trajectory_len", config.max_trajectory_len),
        seed=config.seed,
        config_sources=config_sources,
    )


def build_sysid_command(config: SysIdRunConfig) -> CommandPlan:
    bundle = get_robot(config.robot)
    resolved = resolve_sysid_run_config(config)
    versions = load_external_versions()
    command = [
        "anchor-bench",
        "sysid",
        "--robot",
        resolved.robot,
        "--data",
        resolved.data,
        "--output",
        resolved.output,
        "--max-iter",
        str(resolved.max_iter),
    ]
    if resolved.headless:
        command.append("--headless")
    if resolved.num_envs is not None:
        command.extend(["--num-envs", str(resolved.num_envs)])
    if resolved.max_trajectory_len is not None:
        command.extend(["--max-trajectory-len", str(resolved.max_trajectory_len)])
    if resolved.seed is not None:
        command.extend(["--seed", str(resolved.seed)])
    if resolved.dry_run:
        command.append("--dry-run")
    return CommandPlan(
        workflow="sysid",
        robot=resolved.robot,
        command=command,
        dry_run=resolved.dry_run,
        notes=[
            f"uses {bundle.paths.actuators.relative_to(bundle.paths.config_dir)} with Newton {versions.newton_version} native actuator components",
            f"requires newton {versions.newton_version} and Isaac Lab {versions.isaac_lab_branch}@{versions.isaac_lab_commit}",
        ],
    )


def run_sysid(config: SysIdRunConfig) -> CommandPlan:
    plan = build_sysid_command(config)
    resolved = resolve_sysid_run_config(config)
    if resolved.dry_run:
        return plan
    from anchor_bench.runtime.environment import require_full_runtime

    require_full_runtime(("isaaclab", "isaaclab_newton", "newton"), workflow="sysid")
    if resolved.robot != "so101":
        raise ValueError("Full runtime execution currently supports only robot=so101")
    from anchor_bench.runtime.assets import resolve_runtime_asset

    resolve_runtime_asset(get_robot(resolved.robot))
    from anchor_bench.sysid.so101_runtime import run_so101_sysid

    run_so101_sysid(
        data=resolved.data,
        output=resolved.output,
        headless=resolved.headless,
        num_envs=resolved.num_envs,
        max_iter=resolved.max_iter,
        max_trajectory_len=resolved.max_trajectory_len,
        seed=resolved.seed,
        config_sources=resolved.config_sources,
    )
    return plan
