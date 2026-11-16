"""Which test covers a source file, and the commands that run it with coverage and under the mutator.

Jest, Vitest and pytest, found from the project's own files; nothing is installed. A runner whose coverage provider
is missing stops the measurement with what to add, and adding it is the project's decision.
"""
import os
import shlex
import subprocess

JS_EXTENSIONS = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
JEST_CONFIGS = tuple("jest.config." + ext for ext in ("ts", "cts", "mts", "js", "cjs", "mjs", "json"))
VITEST_CONFIGS = tuple("{}.config.{}".format(name, ext) for name in ("vitest", "vite")
                       for ext in ("ts", "mts", "cts", "js", "mjs", "cjs"))


class RunnerError(Exception):
    """The file can't be measured as is; the message says what is missing."""


def upward(start, root):
    """Folders from `start` up to `root`, both included."""
    current = os.path.abspath(start)
    root = os.path.abspath(root)
    while True:
        yield current
        if current == root or os.path.dirname(current) == current:
            return
        current = os.path.dirname(current)


def find_test(source, root):
    """The test file of a source file by the usual conventions, or None."""
    directory, name = os.path.split(os.path.abspath(source))
    stem, extension = os.path.splitext(name)
    if extension == ".py":
        candidates = [os.path.join(directory, "test_" + name), os.path.join(directory, stem + "_test.py")]
        candidates += [os.path.join(folder, "tests", "test_" + name) for folder in upward(directory, root)]
    elif extension in JS_EXTENSIONS:
        candidates = [os.path.join(folder, stem + kind + ext)
                      for folder in (directory, os.path.join(directory, "__tests__"))
                      for kind in (".spec", ".test") for ext in JS_EXTENSIONS]
    else:
        candidates = []
    return next((path for path in candidates if os.path.isfile(path)), None)


def nearest(start, root, names):
    for folder in upward(os.path.dirname(os.path.abspath(start)), root):
        for name in names:
            if os.path.isfile(os.path.join(folder, name)):
                return os.path.join(folder, name)
    return None


def node_bin(start, root, name):
    for folder in upward(start, root):
        path = os.path.join(folder, "node_modules", ".bin", name)
        if os.path.isfile(path):
            return path
    return None


def has_package(start, root, package):
    return any(os.path.isdir(os.path.join(folder, "node_modules", package)) for folder in upward(start, root))


def relative(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def project_python(root):
    for candidate in (os.path.join(root, ".venv", "bin", "python"), os.path.join(root, "venv", "bin", "python")):
        if os.path.isfile(candidate):
            return candidate
    return "python3"


class Plan:
    """How to run one test file: with coverage into a folder, and as the mutator's kill command."""

    def __init__(self, runner, coverage_commands, mutant_command):
        self.runner = runner
        self.coverage_commands = coverage_commands
        self.mutant_command = mutant_command


def jest_plan(test, root, out):
    config = nearest(test, root, JEST_CONFIGS)
    binary = node_bin(os.path.dirname(config or test), root, "jest")
    if not binary:
        raise RunnerError("jest is not installed in node_modules (install the project's dependencies)")
    base = [relative(binary, root)] + (["-c", relative(config, root)] if config else []) + [relative(test, root)]
    quiet = ["--ci", "--silent", "--runInBand"]
    coverage = base + quiet + ["--coverage", "--coverageReporters=lcov", "--coverageDirectory=" + out]
    return Plan("jest", [coverage], " ".join(shlex.quote(part) for part in base + quiet))


def vitest_plan(test, root, out):
    config = nearest(test, root, VITEST_CONFIGS)
    start = os.path.dirname(config or test)
    binary = node_bin(start, root, "vitest")
    if not binary:
        raise RunnerError("vitest is not installed in node_modules (install the project's dependencies)")
    if not (has_package(start, root, "@vitest/coverage-v8") or has_package(start, root, "@vitest/coverage-istanbul")):
        raise RunnerError("Vitest has no coverage provider: the project needs @vitest/coverage-v8 (or -istanbul) as a "
                          "devDependency. keel never installs it; adding it is the project's decision")
    base = [relative(binary, root), "run"] + (["--config", relative(config, root)] if config else [])
    base += [relative(test, root), "--no-file-parallelism"]
    coverage = base + ["--coverage.enabled=true", "--coverage.reporter=lcov", "--coverage.reportsDirectory=" + out]
    return Plan("vitest", [coverage], " ".join(shlex.quote(part) for part in base))


def pytest_plan(test, root, out):
    python = project_python(root)
    probe = subprocess.run([python, "-c", "import coverage, pytest"], capture_output=True, cwd=root)
    if probe.returncode != 0:
        raise RunnerError("the project's Python ({}) lacks pytest or coverage: add them to its dev dependencies. "
                          "keel never installs them".format(python))
    shown = relative(python, root) if os.path.isabs(python) else python
    data = os.path.join(out, ".coverage")
    run = [shown, "-m", "coverage", "run", "--data-file=" + data, "-m", "pytest", "-q", "-x", relative(test, root)]
    report = [shown, "-m", "coverage", "lcov", "--data-file=" + data, "-o", os.path.join(out, "lcov.info")]
    mutant = " ".join(shlex.quote(part) for part in [shown, "-m", "pytest", "-q", "-x", relative(test, root)])
    return Plan("pytest", [run, report], mutant)


def plan_for(test, root, out):
    if test.endswith(".py"):
        return pytest_plan(test, root, out)
    if nearest(test, root, VITEST_CONFIGS) and not nearest(test, root, JEST_CONFIGS):
        return vitest_plan(test, root, out)
    return jest_plan(test, root, out)
