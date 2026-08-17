"""Run the whole No-Tube-Rot test suite.

    python tests/run.py            everything
    python tests/run.py -v         name every test as it runs
    python tests/run.py -k shorts  only tests whose name matches

Two runners sit behind this one command, because the repository is two
languages: unittest for the Python tests, and Node's built-in test runner for
the content script, which needs a JavaScript engine to mean anything. Neither
needs anything installed beyond the interpreter itself.

If Node isn't available the JavaScript tests are skipped with a note rather
than failing the run — the same way checks.py skips the YAML validation when
PyYAML isn't installed. CI has both, so nothing is skipped there.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import unittest

# Never leave a __pycache__/ behind: it is a reserved underscore-prefixed name
# and Firefox refuses to load any extension folder containing one (issue #1).
sys.dont_write_bytecode = True

HERE = pathlib.Path(__file__).resolve().parent
JS = HERE / "js"


def run_python(verbosity: int, pattern: str | None) -> bool:
    print("Python tests", flush=True)
    sys.path.insert(0, str(HERE))
    loader = unittest.TestLoader()
    if pattern:
        loader.testNamePatterns = [f"*{pattern}*"]
    suite = loader.discover(start_dir=str(HERE), top_level_dir=str(HERE))
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return result.wasSuccessful()


def run_js(verbosity: int, pattern: str | None) -> bool | None:
    """True/False, or None if Node isn't installed."""
    print("\nJavaScript tests (content.js)", flush=True)
    node = shutil.which("node")
    if node is None:
        print("  skip  Node is not installed")
        return None
    files = sorted(JS.glob("*.test.js"))
    if not files:
        print("  skip  no test files")
        return None
    # Explicit paths rather than the directory: Node changed how it resolves a
    # directory argument to --test between releases, and the files are right
    # here anyway.
    argv = [node, "--test"]
    if verbosity > 1:
        argv.append("--test-reporter=spec")
    if pattern:
        argv += ["--test-name-pattern", pattern]
    argv += [str(path) for path in files]
    sys.stdout.flush()
    return subprocess.run(argv, cwd=HERE.parent).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-v", "--verbose", action="store_true", help="name every test")
    ap.add_argument("-k", metavar="PATTERN", help="only tests matching PATTERN")
    ap.add_argument("--python-only", action="store_true")
    ap.add_argument("--js-only", action="store_true")
    args = ap.parse_args()
    verbosity = 2 if args.verbose else 1

    python_ok = js_ok = True
    if not args.js_only:
        python_ok = run_python(verbosity, args.k)
    if not args.python_only:
        js_ok = run_js(verbosity, args.k)
        if js_ok is None:
            print("\nnote: Node was not found — the content script was not tested")
            js_ok = True

    print()
    if python_ok and js_ok:
        print("All tests passed.")
        return 0
    print("Tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
