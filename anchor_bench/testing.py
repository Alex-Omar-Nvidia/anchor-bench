from __future__ import annotations

import argparse
import sys
import unittest
from collections.abc import Callable, Sequence
from typing import Any, TextIO


def _test_label(test: unittest.case.TestCase) -> str:
    test_id = getattr(test, "id", None)
    return test_id() if callable(test_id) else str(test)


class TqdmTextTestResult(unittest.TextTestResult):
    def __init__(self, *args: Any, progress: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._progress = progress

    def startTest(self, test: unittest.case.TestCase) -> None:
        label = _test_label(test)
        self._progress.set_description_str(label[-80:], refresh=False)
        super().startTest(test)

    def stopTest(self, test: unittest.case.TestCase) -> None:
        try:
            super().stopTest(test)
        finally:
            self._progress.update(1)

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        super().addSuccess(test)
        self._progress.set_postfix_str("ok", refresh=False)

    def addFailure(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:
        super().addFailure(test, err)
        self._progress.set_postfix_str("failed", refresh=False)

    def addError(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:
        super().addError(test, err)
        self._progress.set_postfix_str("error", refresh=False)

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._progress.set_postfix_str("skipped", refresh=False)


class TqdmTextTestRunner(unittest.TextTestRunner):
    resultclass = TqdmTextTestResult

    def __init__(self, *args: Any, progress: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._progress = progress

    def _makeResult(self) -> unittest.TestResult:
        return self.resultclass(
            self.stream,
            self.descriptions,
            self.verbosity,
            progress=self._progress,
        )


def load_suite(
    tests: Sequence[str],
    *,
    start_directory: str = "tests",
    pattern: str = "test*.py",
    top_level_directory: str | None = None,
) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    if tests:
        return loader.loadTestsFromNames(list(tests))
    return loader.discover(
        start_dir=start_directory,
        pattern=pattern,
        top_level_dir=top_level_directory,
    )


def _default_tqdm_factory() -> Callable[..., Any]:
    try:
        from tqdm.auto import tqdm
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "tqdm is required for the progress test runner. "
            "Run tests inside the Anchor Bench container with `./setup.sh --shell python3 scripts/run_unit_tests.py`."
        ) from exc
    return tqdm


def run_suite(
    suite: unittest.TestSuite,
    *,
    stream: TextIO | None = None,
    failfast: bool = False,
    buffer: bool = False,
    verbosity: int = 0,
    tqdm_factory: Callable[..., Any] | None = None,
) -> unittest.TestResult:
    stream = stream or sys.stderr
    tqdm_factory = tqdm_factory or _default_tqdm_factory()
    total = suite.countTestCases()
    with tqdm_factory(total=total, unit="test", desc="unit tests", dynamic_ncols=True) as progress:
        runner = TqdmTextTestRunner(
            stream=stream,
            verbosity=verbosity,
            failfast=failfast,
            buffer=buffer,
            progress=progress,
        )
        result = runner.run(suite)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run unittest suites with a tqdm progress bar.")
    parser.add_argument("tests", nargs="*", help="Optional unittest module, class, or method names.")
    parser.add_argument("-s", "--start-directory", default="tests", help="Directory to discover tests from.")
    parser.add_argument("-p", "--pattern", default="test*.py", help="Discovery filename pattern.")
    parser.add_argument("-t", "--top-level-directory", help="Top-level project directory for discovery.")
    parser.add_argument("-f", "--failfast", action="store_true", help="Stop on the first failure or error.")
    parser.add_argument("-b", "--buffer", action="store_true", help="Buffer stdout/stderr during tests.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show unittest verbose output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    suite = load_suite(
        args.tests,
        start_directory=args.start_directory,
        pattern=args.pattern,
        top_level_directory=args.top_level_directory,
    )
    result = run_suite(
        suite,
        failfast=args.failfast,
        buffer=args.buffer,
        verbosity=2 if args.verbose else 0,
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
