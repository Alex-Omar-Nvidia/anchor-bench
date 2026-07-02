# PR Comments Accumulation (PRs 12–46)

Repository: `NVIDIA-dev/anchor-bench`  
Generated: 2026-06-26  
Scope: all open "Review split" PRs from #12 through #46.

Each comment shows author, file location (for inline comments), and body.

---

## PR #12 — Review split 01: core package contracts

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/core/schemas.py` (line 56)

I think all of these config schemas and the `from_dict` calls can be replaced with pydantic. Can we use AI to try to swap all of this to use pydantic instead of having our own validation logic?

### Inline comment by @Alex-Omar-Nvidia

**File:** `tests/test_versions.py` (line 10)

it would be great if we had semver equality, so we only accepted aparticular major and mijor version, but allowed the patch version to be anything

### Inline comment by @Alex-Omar-Nvidia

**File:** `AGENTS.md` (line 4)

this information can reference the `versions/compatibility.toml` file instead of duplicating the information in two places

### Inline comment by @Alex-Omar-Nvidia

**File:** `tests/test_versions.py` (line 17)

can we add CI here so that these tests run automatically when we create a new PR? It doesnt look like we have any CI yet 

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/core/schemas.py` (line 580)

There is another comment about CI elsewhere but I wanted to follow up here too,

This codebase makes great use of python types. Can we run a type checker in CI? I've used mypy and pyright and both are great (pyright is nice because it plugs into VS Code) but it would be great to run the type checker in CI to catch any type issues before they merge

---

## PR #13 — Review split 02: robot registry and base configs

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/robots/registry.py` (line 52)

i dont understand the purpose of doing from_dict and then to_dict. The downstream of this variable just takes a dict but that dict must be of type RobotRunFile? Can we remove this `to_dict` call and have the downstream consumers be typed to take `RobotRunFile`?

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/robots/registry.py` (line 66)

Instead of creating a `RobotBundle` with `_load_robot_bundle` and then having to call `validate_robot_bundle`, can we just always call `validate_robot_bundle` from inside `_load_robot_bundle` before we return the `RobotBundle`? This simplifies the API (one less call to make) and guarantees that we can never create an inconsistent `RobotBundle` from `_load_robot_bundle`.

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/robots/registry.py` (line 101)

Most error handling in this codebase raises an exception but this function returns a list of validation errors. If we want to collect all the errors we can before we throw thats fine, but at the end can we make a new error with all these errors inside it and raise that up the stack?

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/robots/registry.py` (line 107)

down here we collect these errors into a bundle and raise them all together, instead, lets move all this error handling inside `load_robot_bundle` so that is collects and throws errors for us. and we can actually remove this function `get_robot` (or rename `load_robot_bundle` to `get_robot`. either way we can remove ` layer of API here.

### Inline comment by @Alex-Omar-Nvidia

**File:** `tests/test_registry.py` (line 83)

lets get these added to CI too

---

## PR #14 — Review split 03: SO-101 declarative config

### Review by @felixmey (COMMENTED)

Looks good to me as well

### Comment by @Alex-Omar-Nvidia

looks good to me! I would still merge these in-order, but this one is nice and scoped, tyty!

---

## PR #15 — Review split 04: G1 declarative config

### Review by @Alex-Omar-Nvidia (APPROVED)

Same comment as Split #3, this one looks good to me!

### Comment by @felixmey

Looks good to me as well

---

## PR #16 — Review split 05: actuator loader and migration

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/actuators/loader.py` (line 246)

If we were using pydantic then that comes with a build in `to_dict` class

```py
from typing import Any

# Assuming ResidualSpec is a Pydantic model
# class ResidualSpec(BaseModel):
#     type: str
#     network_file: str
#     ...

def _residual_to_dict(residual: ResidualSpec | None) -> dict[str, Any] | None:
    if residual is None:
        return None
    
    # model_dump() automatically converts all the model's fields to a dictionary
    return residual.model_dump()
```

Or better yet, just ditch the original function and rely on `residual.model_dump()`

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/migration/legacy.py` (line 13)

What are model_type configs? and can we rename this to be more clear so it's not just "Legacy" its like "migrate_isaac_lab_2_2_actuator_to_newton" or something?

If we are going to publish a migrator between these two components I think we should add some tests and make sure we vouch for this. because i dont want to break someone's random workflow and then they have a bad experience.

I wonder if such a migrator is something that should be owned by another team? or if we do really want it to be here? This seems like a thing that Isaac Lab may want upstreamed.

@es-rl just wondering if you had thoughts on if we should move this to IL? We can merge it into Anchor Bench for now (to keep the merge flow moving) and then maybe open up a conversation with Kelly about upstreaming this? WDYT?

### Inline comment by @es-rl

**File:** `anchor_bench/migration/legacy.py` (line 13)

Good point! It's Newton 1.0 to Newton 1.2 actuator model migration. I'm not sure how both Newton and IL are planning to handle users updating their actuators to the new schema but you're right that it could be a feature added. I think IL may ask us to merge with Newton since this is purely actuator related. 

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/migration/legacy.py` (line 13)

That makes sense, I cut this ticket https://jirasw.nvidia.com/browse/DEVTECHEP-876 to capture this work

### Inline comment by @felixmey

**File:** `anchor_bench/actuators/loader.py` (line 101)

If the USD schemas are registered the 3 lines can be replaced with a loop and `prim.AddAppliedSchema(schema)`

### Inline comment by @felixmey

**File:** `anchor_bench/actuators/loader.py` (line 151)

Only use of that constant is in the function below, I would either inline it or make it a private constant

### Inline comment by @felixmey

**File:** `anchor_bench/migration/legacy.py` (line 55)

Shouldn't this be `network_file` without the s?

---

## PR #17 — Review split 06: actuator schema tests

### Review by @Alex-Omar-Nvidia (CHANGES_REQUESTED)

I love tests thank you!

Can we make sure these are running in CI before we merge? tyty

---

## PR #18 — Review split 07: SAGE data loader

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/data/sage.py` (line 69)

nit: might be nice to find all the joints in `requested_joints` not in `source_joints` and then raise them all in error message

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/data/sage.py` (line 1)

Your current code is actually quite robust! It is modular, well-typed, and has comprehensive error handling. If you don't want to add new dependencies, **it is perfectly fine as it is.**

However, it *can* be simplified. Right now, you are manually writing a lot of validation boilerplate and reinventing some time-series data alignment logic.

Here is a breakdown of how Pydantic and a data manipulation library (like Pandas or Polars) could clean this up, along with the pros and cons.

### 1. Where Pydantic Shines: Metadata & State Validation

You have a lot of manual validation logic in `validate_sage_dir` (checking if keys are in expected sets). Pydantic is built exactly for this.

Instead of manual `if ... not in allowed: raise ValueError` checks, you can define a Pydantic model for your YAML file.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class SageMetadata(BaseModel):
    time_unit: Literal["microseconds", "seconds"]
    position_unit: Literal["rad"]
    velocity_unit: Literal["rad/s"]
    torque_unit: Literal["N*m", "Nm"]
    
    # You can allow extra fields to pass through using model_config
    model_config = {"extra": "allow"}

# Now your validation logic becomes a single line:
# metadata = SageMetadata(**yaml.safe_load(...))

```

You can also swap your `@dataclass` definitions for Pydantic `BaseModel`s. This gives you automatic type coercion (e.g., if a timestamp comes in as a string `"1.5"`, Pydantic will convert it to a `float` `1.5` automatically).

*Warning:* **Do not** use Pydantic to validate individual CSV rows if your files have thousands of rows. Pydantic validation adds overhead and will slow down your file loading significantly compared to raw Python loops. Use it for the final output containers and metadata.

### 2. The CSV Bottleneck: `ast.literal_eval`

The biggest performance trap in your current code is this:

```python
def parse_vector(value: str) -> list[float]:
    parsed = ast.literal_eval(value)

```

Running `ast.literal_eval` inside a standard `csv.DictReader` loop for every column of every row is very slow for large datasets.

If your CSVs contain stringified lists like `"[0.1, 0.2, -0.5]"`, there's no magic bullet, but a library like **Pandas** or **Polars** provides vectorized string operations that are much faster.

### 3. Time-Series Alignment: Reinventing the Wheel

Your helper functions `_sort_rows`, `_uniform_grid`, and `_interpolate_positions` are manually doing time-series alignment and interpolation.

If you introduce **Pandas**, you can delete almost all of that manual math logic. Pandas has built-in interpolation for time-series data.

Here is roughly what your interpolation logic would look like if you used Pandas:

```python
import pandas as pd

# Load CSV and parse the list strings using pandas apply
df = pd.read_csv(root / "control.csv")
df['positions'] = df['positions'].apply(eval) # Still uses eval, but vectorized mapped

# Set the timestamp as the dataframe index
df.set_index('timestamp', inplace=True)

# Interpolate to your target_dt instantly
target_index = np.arange(overlap_start, overlap_end, target_dt)
df_reindexed = df.reindex(df.index.union(target_index)).interpolate(method='time')
final_df = df_reindexed.loc[target_index]

```

### Summary Recommendation

* **Keep it as is IF:** You want to avoid heavy dependencies (like Pandas), your CSV files are relatively small (under 10,000 rows), and the code currently runs fast enough for your needs.
* **Refactor IF:** Your CSV files are huge and loading is slow, or if you want to eliminate the ~40 lines of manual array interpolation and metadata validation.

How large are the typical `control.csv` and `state_motor.csv` files you are processing with this script?

---

## PR #19 — Review split 08: SysID command planning

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/runner.py` (line 27)

can be pydantic-ized

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/runner.py` (line 92)

im worried if we call out Newton 1.2 here this code will rot as we upgrade the dependencies

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/validation.py` (line 5)

This can be

```
resolved = value or default
```

---

## PR #20 — Review split 09: benchmark command planning

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/benchmark/newton_runner.py` (line 50)

i wonder if there is a better way to build commands, but im not sure what that would be right now. maybe we could use argparse to provide structure to the command format and then pass this string into argparse for checking? Not sure if this is worth it but might be interesting to investigate.

My goals for this command building would be
* fewer bugs can surface here
* easier to maintain

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/benchmark/newton_runner.py` (line 77)

I wonder if we can parse the compatibility.toml file and load the newton version into a global variable or have some globally accessible getter?

---

## PR #21 — Review split 10: analysis command planning

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/analysis/runner.py` (line 51)

it seems a bit odd that both empty and `*` (all) return the same thing

---

## PR #22 — Review split 11: runtime environment helpers

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/runtime/app_launcher.py` (line 17)

IIRC this flag is deprecated and instead the renderer is pulled in based on a combination of other flags? Can we double check this

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/runtime/environment.py` (line 16)

is docker required here?

### Inline comment by @felixmey

**File:** `anchor_bench/runtime/app_launcher.py` (line 17)

Where do you get the information from that it is deprecated? I only stumbled over `--viz kit` as a contradicting flag and the specific renderer selection flags `renderer=newton_renderer` and `renderer=isaacsim_rtx_renderer`, but I have not found anything about deprecation

---

## PR #23 — Review split 12: SO-101 runtime config helpers

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/runtime/so101_scene.py` (line 15)

This function makes me sad because if i pass `value` as anything other than a `wp.array` then this returns value unchanged, so it doesn't always do a `to_torch`.

I would update this to do implement this logic
* if this is torch, return torch
* if this is wp, convert and return torch
* throw

Also just thinking aloud, if we use python types here for this function then can we have mypy detect errors here without having to assert on type? maybe we should continue to have to assert on type regardless

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/runtime/so101_scene.py` (line 7)

is this function needed? we are just doing an access.

If we need to validate the state of `bundle` maybe this can be called `validate_so101_joint_names`?

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/runtime/so101_scene.py` (line 43)

these functions dont have their arguments typed but most other functions in this code do. can we add typing hints here? 

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/runtime/so101_scene.py` (line 40)

instead of returning this class handle from the function, can we move this import to the top of the file? or is there a reason that we want to do this importing like this?

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/runtime/so101_scene.py` (line 119)

can these be at the top of the file?

### Inline comment by @felixmey

**File:** `anchor_bench/runtime/so101_scene.py` (line 107)

Nitpicking but mix of dict access `[...]` and `.get(...)`, also if key is not present it boils up raw key access error

---

## PR #24 — Review split 13: SysID optimizer

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/optimizer.py` (line 66)

can this be at the top of the file?

---

## PR #25 — Review split 14: SO-101 SysID runtime

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 46)

can `run_summary.yaml` (or the entire output directory) be in the .gitignore

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 114)

`seed = int(seed or 0)`

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 131)

can we move this to the top of the file

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 153)

this is not a class named SceneCfg, this is a curried class (anonymous class? parameterized instanced class?) 

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 153)

i think?

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 153)

i dont love returning classes, i'd rather return an object. and so for this API call stack, i'd rather this be a builder that gives me an instantiated object than a class that i need to instantiate myself

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 181)

can this be at the top of the file

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 222)

this is inside the `run_so101_sysid` function but how much of this is specific to so101? or is this a general Sys ID algorithm that can be genericized?

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/sysid/so101_runtime.py` (line 90)

this function is 200 lines long. can we break this up into more individual components?

### Inline comment by @felixmey

**File:** `anchor_bench/sysid/so101_runtime.py` (line 264)

Is this correct to compare sim_pos to the measured pos post sim with the same index?
Isn't this causing a problem as sim_pos for index 0 post simulation is essentially index 1?

---

## PR #26 — Review split 15: benchmark initial-state sync

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/benchmark/init_sync.py` (line 13)

just a general comment but there are a lot of data classes in this repo and I wonder if we should get some pretty hefty documentation/tutorial set up so people know what they need to modify to get started

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/benchmark/init_sync.py` (line 17)

can we add type hints here 

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/benchmark/init_sync.py` (line 56)

does this take `torch_module` as an input so we can do dependency injection? If not, can we import torch at the top of the file

---

## PR #27 — Review split 16: SO-101 benchmark runtime

### Inline comment by @Alex-Omar-Nvidia

**File:** `anchor_bench/benchmark/so101_runtime.py` (line 158)

this function is long and if we could break it upinto pieces and then unit test those pieces that would be cool

### Inline comment by @felixmey

**File:** `anchor_bench/benchmark/so101_runtime.py` (line 30)

I don't see why this logging should be so101 specific, might be worth using a logging library anyway

### Inline comment by @felixmey

**File:** `anchor_bench/benchmark/so101_runtime.py` (line 181)

A lot of dynamic imports in function, should be at top

### Comment by @felixmey

A lot of this code seems to be general and not to specific to so101, might be worth to refactor it out into reusable components

---

## PR #28 — Review split 17: SO-101 analysis runtime

### Inline comment by @felixmey

**File:** `anchor_bench/analysis/so101_analysis.py` (line 556)

Many dynamic imports that are all needed, should be at the top

---

## PR #29 — Review split 18: experiment runner

### Inline comment by @felixmey

**File:** `anchor_bench/experiments/runner.py` (line 73)

The dataclasses look like a lot of duplicated information scattered in each, I think there should be reuse between them, that would also reduce the boiler plate code to populate all the same fields

---

## PR #30 — Review split 19: experiment tests

_No comments._

---

## PR #31 — Review split 20: SO-101 runtime tests

_No comments._

---

## PR #32 — Review split 21: Docker build configuration

### Inline comment by @Alex-Omar-Nvidia

**File:** `docker/Dockerfile` (line 64)

i wonder if we can consume these dependencies from the compatibility.toml instead of duplicating it here

### Inline comment by @Alex-Omar-Nvidia

**File:** `docker/Dockerfile` (line 64)

if compatibliity.toml were a yaml file we could use `yq` to parse it easily in this dockerfile

### Inline comment by @Alex-Omar-Nvidia

**File:** `docker/x11.yaml` (line 14)

instead of x11 forwarding, which can be flakey on non-ubuntu (e.g. redhat) can we recommend people use web rtc streaming to view this GUI?

### Inline comment by @Alex-Omar-Nvidia

**File:** `docker-compose.yaml` (line 9)

can this also pull from compatibility.toml

### Inline comment by @felixmey

**File:** `docker/Dockerfile` (line 118)

This might be tricky to auto accept the eula if the user never saw it, not sure if it would be sufficient to just have reading the eula as part of the docs, or if there is a different workflow needed to accept the eula

### Inline comment by @felixmey

**File:** `docker-compose.yaml` (line 12)

Does isaac sim not align with Semantic versioning or is that a typo?

---

## PR #33 — Review split 22: setup bootstrap script

### Inline comment by @Alex-Omar-Nvidia

**File:** `setup.sh` (line 13)

if this was yaml and not toml we could use `yq` and not have to have this bash 

---

## PR #34 — Review split 23: Docker run scripts

_No comments._

---

## PR #35 — Review split 24: Docker persist script

### Comment by @felixmey

Looks good to me

---

## PR #36 — Review split 25: Docker tests

_No comments._

---

## PR #37 — Review split 26: GRU runtime shim

### Inline comment by @felixmey

**File:** `anchor_bench/runtime/actuator_net_gru.py` (line 208)

applied_effort is never used in ActuatorNetGRUResidual

---

## PR #38 — Review split 27: training data and export helpers

_No comments._

---

## PR #39 — Review split 28: training trainer core

_No comments._

---

## PR #40 — Review split 29: training runner

### Inline comment by @felixmey

**File:** `anchor_bench/training/runner.py` (line 158)

It feels like a lot of boiler plate to have config -> resolved to parameters -> parsed to a config again

---

## PR #41 — Review split 30: training tests

_No comments._

---

## PR #42 — Review split 31: CLI dry-run wiring

_No comments._

---

## PR #43 — Review split 32: CLI and artifact docs

### Inline comment by @felixmey

**File:** `docs/migration-newton-1.2.md` (line 4)

This should be based on Newton 1.3 going forward

---

## PR #44 — Review split 33: README and repo structure docs

_No comments._

---

## PR #45 — Review split 34: robot plugin docs

_No comments._

---

## PR #46 — Review split 35: G1 neural actuator docs

_No comments._

