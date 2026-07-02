from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class GenericRuntimeTests(unittest.TestCase):
    def test_scalar_pd_group_values_expand_to_configured_joints(self):
        from anchor_bench.robots.registry import get_robot
        from anchor_bench.runtime.robot_config import build_implicit_actuator_params

        bundle = get_robot("ur10e")
        params = build_implicit_actuator_params(bundle)

        self.assertEqual(set(bundle.spec.joint_names), set(params["stiffness"]))
        self.assertEqual({120.0}, set(params["stiffness"].values()))
        self.assertEqual({0.01}, set(params["armature"].values()))

    def test_non_pd_controller_fails_with_explicit_runtime_error(self):
        from anchor_bench.robots.registry import get_robot
        from anchor_bench.runtime.robot_config import build_implicit_actuator_params

        with self.assertRaisesRegex(ValueError, "requires a pd controller"):
            build_implicit_actuator_params(get_robot("teststand"))

    def test_analysis_uses_requested_robot_layout_and_metric_name(self):
        from anchor_bench.analysis.runtime import run_robot_analysis

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "bench" / "real" / "ur10e" / "example" / "motion"
            sim = root / "bench" / "sim" / "ur10e" / "example" / "implicit" / "motion"
            for folder in (real, sim):
                folder.mkdir(parents=True)
                (folder / "joint_list.txt").write_text("shoulder_pan_joint\n", encoding="utf-8")
                (folder / "control.csv").write_text(
                    'type,timestamp,positions\nCONTROL,0.0,"[0.0]"\n'
                    'CONTROL,1000.0,"[1.0]"\n',
                    encoding="utf-8",
                )
                (folder / "state_motor.csv").write_text(
                    'type,timestamp,positions,velocities,torques\n'
                    'STATE_MOTOR,0.0,"[0.0]","[0.0]","[0.0]"\n'
                    'STATE_MOTOR,1000.0,"[1.0]","[1.0]","[1.0]"\n',
                    encoding="utf-8",
                )

            output = root / "analysis"
            result = run_robot_analysis(
                "ur10e",
                root / "bench",
                output,
                make_joint_plots=False,
                make_end_effector_plots=False,
            )

            self.assertEqual(output / "metrics" / "ur10e_metrics.csv", result)
            self.assertTrue(result.exists())
            self.assertFalse((output / "metrics" / "so101_metrics.csv").exists())

    def test_dispatchers_forward_non_so101_robot(self):
        from anchor_bench.analysis.runner import run_analysis
        from anchor_bench.benchmark.newton_runner import BenchmarkMotion, run_benchmark_batch
        from anchor_bench.core.schemas import SysIdRunConfig
        from anchor_bench.sysid.runner import run_sysid

        with patch("anchor_bench.runtime.environment.require_full_runtime"), patch(
            "anchor_bench.runtime.assets.resolve_runtime_asset"
        ), patch("anchor_bench.benchmark.runtime.run_robot_benchmark_batch") as benchmark:
            run_benchmark_batch(
                "ur10e",
                [BenchmarkMotion("motion")],
                dry_run=False,
            )
        self.assertEqual("ur10e", benchmark.call_args.args[0])

        with patch("anchor_bench.runtime.environment.require_full_runtime"), patch(
            "anchor_bench.runtime.assets.resolve_runtime_asset"
        ), patch("anchor_bench.sysid.runtime.run_robot_sysid") as sysid:
            run_sysid(
                SysIdRunConfig(
                    robot="ur10e",
                    data="motion",
                    output="output",
                    dry_run=False,
                    max_iter=1,
                )
            )
        self.assertEqual("ur10e", sysid.call_args.args[0])

        with patch("anchor_bench.analysis.runtime.run_robot_analysis") as analysis:
            run_analysis(
                "ur10e",
                result_folder="results",
                output="output",
                dry_run=False,
            )
        self.assertEqual("ur10e", analysis.call_args.args[0])
