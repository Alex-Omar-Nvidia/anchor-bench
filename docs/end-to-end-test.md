# Host-Safe End-to-End Pipeline Test

`tests/test_pipeline_contract.py` verifies the host-safe contract across the
SO-101 SysID, benchmark, and analysis workflow. It is an end-to-end unit test
for the pipeline wiring, not a full Isaac Sim or Newton runtime test.

## What It Proves

- A SysID-style `best_params.yaml` can be consumed by benchmark actuator-param
  loading.
- Experiment benchmark expansion passes the expected seed, output folder,
  actuator params, dataset, actuator model, motion name, and headless setting
  into the benchmark runtime boundary.
- Benchmark outputs in CSV trajectory directories can be consumed by the real
  analysis reader.
- Analysis writes `so101_metrics.csv` rows for the selected dataset, motion,
  actuator model, seed, and joints.
- Plot dependencies stay lazy: `_load_pyplot()` is not called when joint and
  end-effector plots are disabled.

## What It Does Not Prove

- CMA-ES optimizer convergence.
- Isaac Sim, Isaac Lab, Newton, Torch, or Warp runtime availability.
- Physical accuracy of the simulated trajectory.
- GUI, GPU, or container behavior.

Those checks belong in runtime or integration validation, not the normal
host-side unit-test suite.

## Test Shape

The test creates all inputs in a temporary directory:

```text
datasets/custom_motion/
  control.csv
  state_motor.csv
  joint_list.txt
  metadata.yaml
sysid/
  seed_42/best_params.yaml
  seed_7/best_params.yaml
benchmark/
  seed_42/
    real/so101/synthetic/custom_motion/
    sim/so101/synthetic/fitted_implicit/custom_motion/
analysis/
  metrics/so101_metrics.csv
```

The experiment config uses two benchmark seeds so the experiment layer is
required to create seed-specific benchmark output roots:

```yaml
seeds: [42, 7]

actuator_models:
  fitted_implicit:
    type: implicit
    fitted_params: <tmp>/sysid/seed_{seed}/best_params.yaml
    benchmark_params: fitted

analysis:
  seeds: [42]
  plots:
    joints: false
    end_effector: false
```

Using `analysis.seeds: [42]` proves that the analysis stage can select one
seed from a multi-seed benchmark layout.

## Runtime Boundary

The test patches `anchor_bench.benchmark.newton_runner.run_benchmark_batch`.
That keeps the unit test host-safe while still checking the exact arguments that
would be handed to the Newton benchmark runtime.

After the patched benchmark call is verified, the test writes synthetic
benchmark artifacts and calls `run_experiment_analysis(..., dry_run=False)` so
the real analysis implementation reads the generated trajectory directories and writes
metrics.

## Run It

Focused test:

```bash
./setup.sh --shell python3 scripts/run_unit_tests.py tests.test_pipeline_contract
```

Adjacent coverage:

```bash
./setup.sh --shell python3 scripts/run_unit_tests.py tests.test_experiments tests.test_so101_runtime tests.test_cli_dry_run
```

Full container suite:

```bash
./setup.sh --shell python3 scripts/run_unit_tests.py
```


