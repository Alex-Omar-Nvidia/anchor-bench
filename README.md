
# Anchor Bench

Anchor Bench is a focused SysID and sim-to-real benchmark package for robot
actuator models on Isaac Sim 6.0, Newton 1.2, and Isaac Lab `develop`.

The repo provides robot configs, data loaders,
SysID command builders, Newton benchmark command builders, analysis helpers,
and agent/MCP tooling around the actuator-identification workflow.

## Compatibility

- Isaac Sim: `6.0.0.0`
- Newton: `1.2.0`
- Isaac Lab: `develop` at `9989d276ad825221b10f5a60de92762fd63a0faf`
- Python: `3.12`

## Quick Start

```bash
bash setup.sh --kitless
bash setup.sh --check
anchor-bench robots list
anchor-bench sysid --robot so101 --data examples/data/so101_sage --output /tmp/anchor-bench-sysid --dry-run
anchor-bench benchmark --robot so101 --motion examples/data/so101_sage --dry-run
anchor-bench analyze --robot so101 --result-folder examples/results/so101 --dry-run
```

Use `bash setup.sh --full` when the local machine should install Isaac Sim
`6.0.0.0` as well.

## Native Actuator Schema

Robot actuator configs use Newton 1.2-style composable components:

- `controller`: `pd`, `pid`, `mlp`, `lstm`, `gru`, `fmu`, or `torque_passthrough`
- `delay`: optional command delay
- `clamps`: optional effort, velocity, DC motor, or position clamps
- `physical_parameters`: armature, dynamic friction, viscous friction, and related fitted values


