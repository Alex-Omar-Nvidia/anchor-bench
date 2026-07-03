# Codebase Review and Improvement Plan

Review date: 2026-07-02

## Purpose

This review evaluates the repository as something another team should be able
to clone or install, connect to its own robot assets and measured data, and use
without first learning internal implementation history. The main design goal is
a short, visible path from robot/drive configuration to the code that executes
it, with configuration indirection only where it creates a real extension
point.

The review covered the Python package, every checked-in robot and experiment
configuration, Docker/setup scripts, documentation, tests, and CI. Runtime-only
Isaac Sim/Newton behavior was reviewed statically and through host-safe tests;
no GPU/full-runtime simulation was available in this environment.

## Executive assessment

Anchor Bench has a sound core direction:

- Robot definitions are declarative under `configs/robots/<robot>/`.
- Heavy Isaac Sim, Isaac Lab, Newton, Torch, and plotting imports are mostly
  kept behind runtime entry points.
- Config parsers reject unknown fields and legacy `model_type` actuator
  configuration.
- SysID, benchmark, training, analysis, and experiment planning all have
  host-safe dry-run paths.
- Generated artifacts and large/private inputs are clearly separated from
  source-controlled configuration.
- The host test suite is broad and currently passes: 124 tests passed, 3 were
  skipped, and 10 subtests passed.

The repository is not yet a dependable handoff for arbitrary drives and
robots. The largest problem is not the number of modules; it is that the
public configuration and CLI imply more runtime capability than the execution
path provides. A user can successfully list and validate a robot, or select an
actuator model by name, and still have no executable asset or implementation
behind it. Installation outside the source checkout is also broken because
runtime configuration is not included in the wheel.

The recommended sequence is:

1. Make distribution and runtime capability claims truthful.
2. Make drive selection select executable code rather than label output.
3. Fix benchmark signal correctness and provide one real end-to-end example.
4. Consolidate workflow resolution and split the largest runtime modules.
5. Tighten CI, documentation, and output safety.

## Current user and code paths

### Robot configuration path

```text
configs/robots/<robot>/robot.yaml
  -> anchor_bench.robots.registry.get_robot()
  -> robot.yaml references actuators.yaml, bounds.yaml, and an asset manifest
  -> run.yaml is loaded by each workflow resolver
  -> runtime.assets resolves robot.yaml:runtime_usd
```

The four-file robot directory is reasonable and easy to browse. The avoidable
indirection is that registration validates the presence of the manifest, but
not the executable asset named by `runtime_usd`, the workflow defaults, or the
runtime support for the declared controller.

### Workflow path

```text
anchor_bench.cli.parser
  -> anchor_bench.cli.commands
  -> <workflow>.runner resolves defaults and builds CommandPlan
  -> the runner resolves the same configuration again for execution
  -> <workflow>.runtime launches or performs the work
```

This is understandable, but the double resolution and reconstructed command
line add indirection without establishing a stronger boundary. A plan should
contain a single resolved configuration that is passed directly to its
executor.

### Actual benchmark/SysID drive path

```text
configs/robots/<robot>/actuators.yaml
  -> runtime.robot_config.load_implicit_actuator_params()
  -> runtime.robot_scene.build_scene_class()
  -> Isaac Lab ImplicitActuatorCfg
  -> static parameters are written directly to the articulation
```

This is not the Newton-native actuator-authoring path exported by
`anchor_bench.actuators`. That second path is tested in isolation but is not
called by benchmark or SysID. The split makes it difficult to know which
actuator declarations are operational.

## Priority 0: correctness and handoff blockers

### P0.1 Make an installed package self-contained or explicitly workspace-based

Evidence:

- `anchor_bench.core.paths.repo_root()` assumes the package is running from a
  source checkout and walks two parents above the module.
- Robot discovery, compatibility versions, assets, and relative input/output
  resolution all depend on that inferred checkout root.
- `pyproject.toml` only discovers `anchor_bench*` Python packages and declares
  no package data.
- A locally built wheel contained Python modules only. It did not contain
  `configs/`, `assets/`, or `versions/compatibility.toml`; an installed
  `anchor-bench robots list` therefore has no robot registry or version
  manifest.

Impact:

The console script looks installable, but it only works from the repository's
editable/Docker layout. This is a high-friction and surprising failure mode for
users copying the tool to another machine or drive.

Recommendation:

- Introduce one explicit `WorkspacePaths`/`ProjectContext` object with
  `root`, `configs`, `assets`, `inputs`, `outputs`, and `third_party` paths.
- Resolve it once at CLI startup from `--workspace`, then
  `ANCHOR_BENCH_WORKSPACE`, then the current checkout when detectable.
- Ship immutable built-in robot templates and the compatibility manifest as
  package resources, or make `anchor-bench init <directory>` materialize them
  into a workspace. Do not silently infer a nonexistent source root.
- Pass the context into registries and workflow resolvers rather than calling
  `repo_root()` throughout the package.

Acceptance criteria:

- Build and install the wheel into a clean virtual environment and a temporary
  working directory.
- `anchor-bench robots list`, `anchor-bench robots describe so101`, and a
  documented dry-run work without the repository on `PYTHONPATH`.
- A user can point inputs, assets, and outputs at mounted/external locations
  with one workspace option and no config rewrites.

### P0.2 Distinguish registered, configured, asset-ready, and runnable robots

Evidence:

- `robots list` reports `g1`, `h1`, `so101`, `teststand`, and `ur10e`.
- `robots describe` reports no validation errors for all five.
- Only SO-101 declares `runtime_usd`; the other four fail full benchmark or
  SysID execution at runtime asset resolution.
- `teststand` declares an FMU controller, while the shared runtime requires a
  single PD controller and converts it to implicit actuator parameters.
- UR10e cannot even build the default benchmark dry-run because `run.yaml`
  supplies no motion.
- Asset-manifest `expected_assets` are descriptive only and are not included in
  readiness validation.

Impact:

Users cannot tell whether a robot is a config example, training-only target,
or runnable simulation target. The first failure arrives late and often after
a large environment setup.

Recommendation:

- Add a small, explicit capability block to `robot.yaml`, for example:

  ```yaml
  runtime:
    usd: so101.usd
    drive: implicit_pd
    workflows: [sysid, benchmark, analysis, training]
  ```

  This replaces `runtime_usd`; it should not point to another capability file.
- Validate that each advertised workflow has its required asset, controller
  implementation, config defaults, and optional dependency.
- Make `robots list` show a concise status (`template`, `training`, `ready`) and
  add `anchor-bench robots check <robot> [--workflow benchmark]` with actionable
  missing items.
- Keep schema validation separate from execution readiness so external data
  can be reported as missing without making the declarative bundle invalid.

Acceptance criteria:

- Every robot's displayed workflow capability is executable when its reported
  external prerequisites are supplied.
- No robot with `errors: []` is described as benchmark-ready if it lacks a
  runtime USD or implemented drive.

### P0.3 Establish one truthful drive/actuator runtime interface

Evidence:

- The actuator schema accepts `pd`, `pid`, `mlp`, `lstm`, `gru`, `fmu`, and
  `torque_passthrough` controllers.
- `runtime.robot_config.build_implicit_actuator_params()` requires exactly one
  actuator group and a `pd` controller.
- Benchmark and SysID use that implicit path; they do not call
  `instantiate_newton_actuators()`.
- `--actuator-model` and experiment `actuator_models.*.type` do not choose an
  implementation. The former becomes an output-directory/summary label, while
  the parameter file is still loaded as an implicit PD overlay.
- Dry-run notes state that runs use Newton-native/composable actuator
  components even though execution builds an Isaac Lab
  `ImplicitActuatorCfg` and manually writes parameters.

Impact:

This is the most dangerous form of indirection in the repository: configuration
appears extensible, but the runtime path is narrower and selected indirectly.
Benchmark comparisons can be mislabeled as different actuator models even
when the same implicit implementation is used.

Recommendation:

- Define one generic drive interface under a plainly named package such as
  `anchor_bench/drives/`:

  ```text
  drives/base.py          # protocol and runtime context
  drives/implicit_pd.py   # current proven implementation
  drives/gru.py           # only when wired into scene execution
  drives/fmu.py           # only when implemented and tested
  ```

- Map the declarative `controller.type` (or an explicit `runtime.drive`) to
  exactly one implementation in a visible registry.
- Have a drive own scene actuator construction, parameter application, command
  application, effort observation, and reset behavior.
- Either integrate the Newton actuator-authoring API into that path or remove
  it from the public runtime story until it is used.
- Narrow accepted config values to implemented paths. It is better to reject
  `fmu` at config validation with a precise message than to register it as
  runnable.
- Rename `--actuator-model` to `--label` if it remains only a label; preferably
  make it select a named, validated drive entry from the experiment config.

Acceptance criteria:

- A reader can start at `controller.type` and reach the executing class in one
  registry lookup.
- Dry-run output states the exact implementation that execution will call.
- Two actuator-model experiment entries cannot produce different labels while
  resolving to the same implementation and parameter source unnoticed.

### P0.4 Record real simulated effort instead of zero torque

Evidence:

- `benchmark.runtime._append_benchmark_sample()` writes an all-zero `effort`
  vector to every simulated `state_motor.csv` row.
- Analysis reads and compares torque signals, so torque metrics/plots for
  benchmark simulation are not measurements of the actuator response.

Impact:

Position and velocity results can still be useful, but torque comparisons are
misleading and should not be published as benchmark metrics.

Recommendation:

- Make effort observation part of the drive interface and read the actual
  applied/computed joint effort after each simulation step.
- Until that is supported, omit the torque column/metric or mark it unavailable
  in metadata rather than writing plausible zero-valued data.
- Add a contract test that drives a nonzero trajectory and proves recorded
  effort is nonzero and has the configured joint order.

Acceptance criteria:

- Analysis never computes a torque metric from a placeholder signal.
- `run_summary.yaml` records which effort signal was captured and its units.

### P0.5 Provide one reproducible end-to-end quick start

Status: dataset preparation resolved on 2026-07-02. The documented SO-101
figure-eight input now has a pinned Hugging Face source plus a checksum-verified
download/conversion script. A bounded full-runtime CI smoke test remains open.

Evidence:

- README's SO-101 quick start launches real SysID and benchmark commands.
- The tracked SO-101 USD exists, and the referenced dataset is now prepared
  locally from the documented NVIDIA Anchor-Lab parquet source.
- The curated fitted parameter file exists, so the example is only partially
  self-contained.
- `check_environment.py --dry-run` passes even when the documented input data
  and all heavy runtimes are absent.

Impact:

The first documented workflow fails after setup, which damages confidence in
all other robot instructions.

Recommendation:

- Check in a deliberately tiny synthetic SAGE fixture under `examples/` (not a
  large measured dataset), or add a deterministic command that generates it.
- Make the default quick start use that fixture and a short trajectory.
- Separate checks into `anchor-bench doctor --host`, `--robot so101`, and
  `--workflow benchmark`; each should state what was and was not verified.
- Keep real datasets external and show the single command/path needed to mount
  them.

Acceptance criteria:

- A clean clone can run all documented dry-runs using paths that exist.
- The full image has a bounded SO-101 smoke test that starts the simulator,
  advances several steps, and writes a valid artifact when a GPU runner is
  available.

## Priority 1: simplify the main extension and execution paths

### P1.1 Make external data paths work consistently

`ANCHOR_BENCH_DATA_DIR` is mounted and exported by Docker scripts but is never
read by Python. Relative paths always resolve against `repo_root()`. Several
robot defaults also use older `inputs/motion_files` or `inputs/sysid_data`
layouts while the docs specify `inputs/datasets`.

Use the workspace context from P0.1 and define one rule:

- Config-relative paths are resolved relative to the workspace.
- Data references may use `data://...` (or a single `--data-root`) for an
  external dataset root.
- Asset references use the same resolver pattern, not separate ad hoc logic.
- Resolved dry-run output should include both the configured value and final
  path.

Migrate checked-in run defaults to the documented layout or mark them as
external examples with a clear missing-data message.

### P1.2 Resolve a workflow once and execute that object

Status: resolved on 2026-07-02. SysID, benchmark, training, and analysis now
expose resolved-object plan/execution functions. Their compatibility entry
points resolve once and delegate to those functions, while CLI handlers execute
the exact object they already validated. Experiment benchmark and analysis
load, discover, and expand once per invocation and reuse those runs for the
plan and executor.

Introduce workflow-specific immutable objects such as `ResolvedSysIdRun` and
`ResolvedBenchmarkRun` that contain:

- paths and provenance;
- robot and drive capability;
- simulation settings;
- input validation result;
- output identity;
- the exact executor parameters.

Use one flow:

```text
parse CLI -> resolve once -> validate -> render plan OR execute resolved object
```

Keep `CommandPlan` as a serialization/view type, not as a second representation
of execution. This removes repeated calls to `get_robot()`, reduces config
source bookkeeping, and prevents dry-run/execution drift.

### P1.3 Consolidate schema ownership

Status: validation cleanup completed on 2026-07-02; package ownership cleanup
remains. External robot, actuator, bounds, run, and experiment inputs now use a
shared immutable Pydantic base with unknown-key rejection and contextual error
formatting. GRU parsing is centralized, while resolved workflow/runtime values
remain dataclasses. The schema layer dropped from 1,054 hand-written lines to
613 lines including the shared adapter. `ConfigSection` still carries temporary
mapping compatibility and the models remain split across three core modules.

Recommended ownership:

```text
config/robot.py       # RobotSpec and bundle validation
config/actuator.py    # actuator schema
config/run.py         # workflow defaults
config/experiment.py  # experiment schema
config/paths.py       # ProjectContext and path references
```

Use one access style (typed attributes) in production code. Keep serialization
methods explicit. Remove the mapping compatibility only after confirming no
external consumers rely on dictionary-style access.

### P1.4 Split runtime orchestration from domain operations

`analysis/runtime.py` is about 900 lines and owns file discovery, resampling,
metrics, plotting, output layout, and Isaac Lab FK. `experiments/runner.py` is
over 500 lines and owns parsing, selection, discovery, batching, planning, and
execution. Benchmark and SysID each contain a large simulation loop with
overlapping reset/step/observation logic.

Split by responsibility, not by robot:

```text
analysis/discovery.py
analysis/metrics.py
analysis/plots.py
analysis/fk.py
analysis/service.py

experiments/expand.py
experiments/batch.py
experiments/service.py

runtime/session.py       # app lifetime and scene setup
runtime/trajectory.py    # reset, command stepping, observations
```

Do not add robot-named runtime modules. Robot differences should remain config
or generic drive implementations.

### P1.5 Remove or implement the `convert` command

The current command validates a SAGE input when present, ignores `--output`,
and prints success JSON for any requested `--format`. It performs no
conversion. This should not be a public command in its present form.

Either remove it until a source format is implemented, or define explicit
subcommands such as `convert sage-csv` with required input/output arguments,
supported formats, a dry-run plan, and an artifact test. Never return success
for a conversion that did not write output.

### P1.6 Protect outputs and make runs reproducible

Benchmark output identity is derived from robot, dataset, actuator label, and
motion, with an optional seed directory only in some experiment cases. Existing
files can be overwritten silently. SysID summaries include a wall-clock
timestamp but no code revision or config hashes.

Add a deterministic run identity and output policy:

- Default to a run directory containing a short config hash or explicit run
  name.
- Refuse to overwrite unless `--overwrite` is passed.
- Write resolved robot, drive, actuator parameters, data metadata/hash,
  compatibility-manifest values, package version, and Git revision when
  available.
- Write through a temporary directory and atomically finalize successful runs.
- Record failed/incomplete runs distinctly.

### P1.7 Use the compatibility manifest everywhere

`versions/compatibility.toml` is correctly used by `setup.sh` and Python, but
exact versions are duplicated in README, Dockerfile defaults,
`docker-compose.yaml`, and some help text. Direct Compose builds can therefore
drift from the manifest even if setup-driven builds do not.

- Make `setup.sh` (or a small manifest reader) the only supported build entry
  and pass every build argument from the manifest.
- Generate Compose environment values from the manifest or remove version
  defaults from Compose.
- Documentation should link to the compatibility manifest instead of copying
  exact pins.
- `check_environment.py` should compare installed versions/commit to expected
  values, not only report module presence.

### P1.8 Make the quality gate pass and be reproducible locally

Observed results:

- `python -m pytest -q`: passed (125 passed, 3 skipped, 10 subtests) after the
  single-resolution regression test was added.
- `python -m compileall -q anchor_bench`: passed.
- `python -m ruff check anchor_bench tests scripts`: passed; all seven findings
  identified during the review were fixed.
- Pyright and pytest-cov were declared as dev dependencies but were not
  installed in the review environment, so those local commands could not run.

Actions:

- Add one documented `make quality`, `tox`, or equivalent command that
  creates/uses the dev environment consistently.
- Add a wheel-content/install smoke test to CI.
- Expand Pyright gradually to runtime adapters; currently it targets a selected
  subset and omits most runtime code.
- Add a small number of contract tests at the drive boundary instead of more
  string-presence tests for Docker/docs.
- Keep full-runtime smoke tests separate and clearly optional because of their
  GPU/container cost.

## Priority 2: focused cleanup after the contracts are fixed

### P2.1 Make CLI help operational

Add help text and examples to arguments, show resolved defaults in dry-run, and
use consistent terms (`data` versus `motion`, `output` versus `output-folder`).
The CLI should expose `doctor/check` and robot workflow readiness before users
attempt execution.

### P2.2 Tighten validation at boundaries

Add validation for:

- unique robot joint names and aliases whose targets exist;
- duplicate/missing actuator joint coverage;
- complete per-joint maps when a runtime requires them;
- controller-specific parameters and clamp parameters;
- manifest name matching robot name;
- dataset row vector width, finite numeric values, monotonic/duplicate
  timestamps, and declared schema;
- output paths that escape an intended workspace only when explicitly allowed.

### P2.3 Remove small dead and compatibility surfaces

After checking external consumers, remove unused helpers such as redundant path
aliases and runtime YAML writers, or make them part of a documented flow. Decide
whether the custom unittest progress runner is still useful now that pytest is
the CI and documented test runner. Small cleanup matters most after the main
execution path is singular.

### P2.4 Correct documentation drift

- The CLI robot list omits G1 even though it is registered.
- Repository structure examples contain formatting inconsistencies.
- The Newton migration guide describes a native actuator path that benchmark
  and SysID do not use.
- Quick-start commands should state whether they are dry-run, synthetic smoke,
  or real-data runs.
- For every robot, document a short readiness table rather than implying that
  registration equals support.

## Proposed target layout

This layout keeps robot support declarative and makes the two real extension
points—robots and drives—obvious:

```text
anchor_bench/
  cli/
  config/
    paths.py
    robot.py
    actuator.py
    run.py
    experiment.py
  robots/
    registry.py
    readiness.py
  drives/
    base.py
    registry.py
    implicit_pd.py
    # gru.py and fmu.py only when executable
  workflows/
    sysid.py
    benchmark.py
    training.py
    analysis.py
  runtime/
    session.py
    scene.py
    trajectory.py
  data/
  analysis/

configs/robots/<robot>/
  robot.yaml
  actuators.yaml
  bounds.yaml
  run.yaml
```

The exact package moves are less important than these rules:

1. A robot file points directly to one implemented drive type.
2. A single registry maps that type to executable code.
3. One resolved workflow object crosses from CLI/configuration into execution.
4. All paths come from one explicit workspace context.
5. Capability and readiness are visible before launching the simulator.

## Suggested delivery sequence

### Milestone 1: truthful baseline

- Fix simulated effort recording or disable torque analysis.
- Mark robot workflow readiness and reject unsupported controllers early.
- Remove/rename misleading actuator-model selection and dry-run notes.
- Remove or disable the no-op conversion command.
- Repair the SO-101 quick start with an existing tiny dataset.
- Make Ruff/CI green.

### Milestone 2: portable workspace

- Add `ProjectContext`/workspace selection.
- Package templates and compatibility data or implement `anchor-bench init`.
- Add installed-wheel CI tests.
- Wire the Docker data mount to the same path resolver.

### Milestone 3: direct drive architecture

- Introduce the drive protocol and registry.
- Move the proven implicit PD implementation first.
- Route benchmark and SysID through the same drive/session boundary.
- Integrate or retire the separate Newton-native authoring path.
- Add GRU/FMU only with full execution tests.

### Milestone 4: workflow simplification

- Resolve each workflow exactly once.
- Split analysis and experiment modules by responsibility.
- Add output identity, overwrite protection, and provenance.
- Finish documentation/readiness tables for every robot.

## Definition of done for a new robot

A new robot should be considered supported only when all of the following are
true:

1. Its entire declarative definition is visible under
   `configs/robots/<robot>/`.
2. `robots check <robot>` identifies its asset, drive implementation, canonical
   joint order, available workflows, and external prerequisites.
3. Its configured drive maps directly to a tested implementation.
4. Host-safe dry-runs use existing example paths or clearly report external
   inputs without claiming readiness.
5. A bounded full-runtime smoke test loads the asset, resolves all joints,
   applies a nonzero command, observes position/velocity/effort, and writes a
   valid artifact.
6. The same robot works from an installed wheel plus a workspace, not only from
   an editable source checkout.

This definition preserves the repository's declarative approach while making
"supported" a verifiable runtime contract rather than a registry entry.
