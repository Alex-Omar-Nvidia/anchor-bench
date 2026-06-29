from __future__ import annotations

import io
import unittest

from anchor_bench.testing import run_suite


class _FakeProgress:
    instances = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.total = kwargs["total"]
        self.n = 0
        self.descriptions = []
        self.postfixes = []
        _FakeProgress.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, value):
        self.n += value

    def set_description_str(self, value, refresh=True):
        self.descriptions.append(value)

    def set_postfix_str(self, value, refresh=True):
        self.postfixes.append(value)


class _PassingTests(unittest.TestCase):
    def test_one(self):
        self.assertTrue(True)

    def test_two(self):
        self.assertEqual(2, 1 + 1)


class ProgressUnitTestRunnerTests(unittest.TestCase):
    def test_progress_updates_once_per_test_case(self):
        _FakeProgress.instances = []
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(_PassingTests)
        stream = io.StringIO()

        result = run_suite(suite, stream=stream, tqdm_factory=_FakeProgress)

        self.assertTrue(result.wasSuccessful())
        self.assertEqual(2, result.testsRun)
        self.assertEqual(1, len(_FakeProgress.instances))
        progress = _FakeProgress.instances[0]
        self.assertEqual(2, progress.total)
        self.assertEqual(2, progress.n)
        self.assertTrue(any("_PassingTests.test_one" in item for item in progress.descriptions))
        self.assertEqual(["ok", "ok"], progress.postfixes)
        self.assertIn("Ran 2 tests", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
