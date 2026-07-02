# PR Comments Resolution (PRs 12–46)

Companion to `PR_COMMENTS.md`. Records the disposition of every review comment:
**implemented**, **already addressed**, **declined (with reasoning)**, or **deferred**.

- Date: 2026-06-29
- Verification: full host-safe suite → **118 tests, OK (skipped=1)** (was 117; +1 new
  regression test). All files changed below pass `ruff` clean.
- Constraint that shaped many decisions: the full Isaac/Newton runtime path is currently
  **un-runnable in this checkout** because `assets/robots/so101/files/so101.usd` is absent,
  so changes to Isaac-only code could not be validated and were treated conservatively.

---

## 1. Implemented

| PR | Change | File(s) |
| --- | --- | --- |
| #16 | **Bug fix.** Migrated `hybrid_residual` emitted plural `network_files` — an *unknown* key to `ResidualSpec`, which also requires the singular `network_file`. Any migrated hybrid config therefore failed to load. Now emits `network_file`. | `anchor_bench/migration/legacy.py` |
| #16 | **Regression test** for the above: migrate a `hybrid_residual` config and assert the residual block round-trips through `ResidualSpec.from_dict`. | `tests/test_actuator_schema.py` |
| #19, #20 | Replaced hardcoded `"Newton 1.2"` in command-plan note strings with `load_external_versions().newton_version` so they cannot rot when the manifest bumps. | `anchor_bench/sysid/runner.py`, `anchor_bench/benchmark/newton_runner.py` |
| #18 | `_select_joints` now collects **all** requested joints absent from `joint_list.txt` and reports them together, instead of raising on the first. | `anchor_bench/data/sage.py` |
| #23 | `to_torch` now converts `wp.array` → torch, passes through torch tensors, and **raises** on any other type (previously it silently returned unknown inputs unchanged). | `anchor_bench/runtime/so101_scene.py` |
| #23 | Added type hints to the previously-untyped runtime helpers (`so101_joint_names`, `to_torch`, `_joint_ids_to_list`, `_write_viscous_friction`, `_matrix_from_param_map`, `apply_static_actuator_params`, `_get_newton_model_for_viscous_friction`). | `anchor_bench/runtime/so101_scene.py` |
| #16 | Privatized `GRU_RUNTIME_SHIM_MESSAGE` → `_GRU_RUNTIME_SHIM_MESSAGE` (only used in-module). The raised message *text* is unchanged, so the regex assertion in `test_actuator_schema.py` still matches. | `anchor_bench/actuators/loader.py` |
| #12 | `AGENTS.md` now points at `versions/compatibility.toml` (the single source of truth) instead of duplicating the pinned versions/commit. | `AGENTS.md` |
| #12 | `test_versions.py` asserts `major.minor` for Isaac Sim/Newton (patch/build may bump without a test edit); Isaac Lab branch + commit stay exact (they are not semver). | `tests/test_versions.py` |

> **Heads-up on the semver change (#12):** this intentionally *loosens* the version-pin
> guard, exactly as the reviewer requested. If you prefer exact pins for reproducibility,
> revert `tests/test_versions.py`.

---

## 2. Already addressed in current code (no change needed)

| PR | Comment | Status |
| --- | --- | --- |
| #26.2 | Add type hints in `init_sync.py` | Module is already fully typed. |
| #26.3 | Inject `torch` / import at top | Already dependency-injected via `torch_module` / `warp_module` params. |
| #25.1 | Put sysid output / `run_summary.yaml` in `.gitignore` | `outputs/` is already ignored. |

---

## 3. Declined — with reasoning

### 3a. Lazy-import rule (AGENTS.md: keep Isaac/Newton imports lazy)
Moving these to module top breaks host-safe import **and** Isaac Sim's hard requirement that
`torch`/omni modules import only *after* `AppLauncher` starts.

- **#23.4, #23.5, #25.3, #25.5, #27.3, #28.1** — "imports at top" on `isaaclab` / `torch` / `warp` / `pxr` blocks.
- **#24.1** — `import cmaes` inside the optimizer: `cmaes` is an *optional* dependency; the lazy
  import is precisely what lets host-only tests run via `allow_random_fallback=True`.

### 3b. Would introduce a bug if applied
- **#19.3** `resolved = value or default`: `or` treats `0` as falsy, so a passed-in `0` would be
  silently replaced by the default instead of failing the `>= 1` check. The explicit `is None`
  test is correct and was kept.

### 3c. Correct / intentional as written
- **#21.1** analysis empty vs `*`: both `None` (unset) and `"*"` (explicit "all") mean "all
  motions" → an empty CLI selector list. Not a bug.
- **#23.6** `[...]` vs `.get`: raw access on `stiffness`/`damping` intentionally marks them
  *required*; `.get` marks the *optional* params.
- **#23.2** rename `so101_joint_names` → `validate_*`: it both validates **and returns** the
  names (parse-don't-validate); a `validate_` name would wrongly imply no return value.
- **#25.4** returning a class from `build_scene_class`: it returns an `InteractiveSceneCfg`
  subclass — the idiomatic IsaacLab configclass pattern. The closure captures static scene
  params; `num_envs`/`env_spacing` are supplied at instantiation.
- **#32.6** Isaac Sim `6.0.0.0` "typo?": no — Isaac Sim uses 4-component versioning, not 3-part semver.
- **#37.1** `applied_effort` "never used" in `ActuatorNetGRUResidual`: **deliberate.** The class
  subclasses Isaac Lab `ImplicitActuator`, which applies PD via joint gains and adds
  `joint_efforts` as feed-forward. Writing `applied_effort` (= clip(PD + residual)) back to
  `joint_efforts` would make the solver apply PD twice. `applied_effort`/`computed_effort` are
  the `ActuatorBase` logging/bookkeeping attributes. Verified against current code; matches the
  prior whole-codebase review's false-positive finding #6.

### 3d. Larger refactors — out of scope for a comment sweep, and the Isaac path can't be validated here
- **#12.1, #16.1, #18.2, #19.1** Pydantic migration: large architectural change + a new runtime
  dependency; reviewers themselves note the current validation is fine as-is.
- **#25.6, #25.7, #27.1, #27.4** break up / genericize the long runtime functions;
  **#29.1** experiment dataclass reuse; **#40.1** training `resolve → command` pattern — these
  touch deliberate, repo-wide patterns and are better as dedicated PRs.
- **#27.2** `_log` → `logging` module: a repo-wide logging decision (sysid/benchmark/analysis
  each define one), not a local fix.
- **#20.1** argparse-based command building: the reviewer marked it speculative ("not sure if
  this is worth it").
- **#13.1–#13.4** registry restructuring: the load-vs-validate split is intentional — `get_robot`
  raises a *combined* error, while `validate_robot` returns the error **list** for diagnostics.
  Folding validation into the loader would break that non-raising contract.
- **#16.3** USD `AddAppliedSchema`: felixmey's own comment is conditional ("*if* the schemas are
  registered"). The current `SetMetadata("apiSchemas", …)` works whether or not the vendored
  Newton schemas are registered; changing it is risky without runtime confirmation.

### 3e. Tracked elsewhere / needs a non-code decision
- **#16.2** legacy migrator rename + ownership and **#43.1** migration doc → Newton 1.3: tied to
  **DEVTECHEP-876** and an actual Newton bump. The repo still pins 1.2.0, and both
  `test_docker_setup` and the README link depend on the current `docs/migration-newton-1.2.md`
  filename.
- **#32.1, #32.2, #32.4** Docker version duplication / TOML→YAML+`yq`: `setup.sh` already parses
  `compatibility.toml` into `--build-arg`s (TOML is the chosen manifest format). **Real drift
  risk worth a follow-up:** the `docker compose build` path in `run-persist.sh` uses the
  hardcoded compose args, *not* the manifest — so a manifest bump can diverge from a compose
  build. Flagged but not changed (infra refactor, needs a full image rebuild to validate).
- **#32.5** EULA auto-accept and **#32.3** WebRTC vs X11: docs/policy, not code.
- **#12.4, #12.5, #13.5, #17** CI / type-checker-in-CI: no CI exists; standing one up needs infra
  decisions (runner type, GPU availability, 24 GB image caching) beyond a code pass.
- **#22.1** `app_launcher` deprecated flag: felixmey found no evidence of deprecation; left as-is.
- **#22.2** `environment.py` "is docker required?": the message is intentional guidance toward
  the supported container path, not a literal hard dependency.
- **#25.2** `seed = int(seed or 0)`: equivalent to the current explicit form for valid int seeds;
  left as the explicit `is None` style for consistency with the deliberate `or`-avoidance in
  `sysid/validation.py` (see #19.3).
- **#26.1** "hefty documentation/tutorial set": a docs effort, not a code change.

### 3f. Acknowledgements / approvals (no action)
- **#14, #15, #35** approvals / "looks good"; **#16 (thread), #22 (thread)** discussion that
  resolved without a code change; PRs **#30, #31, #34, #36, #38, #39, #41, #42, #44, #45, #46**
  had no comments.

---

## 4. Open question — surfaced, not silently "fixed"

**#25.8 (felixmey, `sysid/so101_runtime.py:264`).** The SysID loop applies `command[i]`, steps the
sim, then compares the **post-step** position to `measured[i]`. The concern is well-founded: the
post-step position is closer to timestamp `i+1`, so this looks like a one-step phase lead in the
objective. Notably, the **benchmark** loop uses a *different* convention (it records the settled
initial state as index 0, then post-step for `i ≥ 1`).

This is a physics / data-causality decision (how SAGE aligns control vs state samples), it changes
the fitted parameters, and it can only be validated against the runtime e2e — which currently
cannot run (missing `so101.usd`). **Left unchanged pending your decision**; happy to implement
whichever alignment you confirm once the asset is available.

---

## 5. Pre-existing issues noticed (not in `PR_COMMENTS.md`, left alone)

`ruff` flags two items that exist at HEAD independent of this work (confirmed by stashing the
changes and re-running):

- `tests/test_actuator_schema.py:3` — unused `from pathlib import Path`.
- `anchor_bench/actuators/loader.py:176` — unused local `effort` (dead code; `_author_pd_actuator`
  recomputes it).

Trivial to clean up, but out of scope for this task.
