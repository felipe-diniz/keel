#!/usr/bin/env python3
"""Measures code with Robert C. Martin's tools (crapper, dryer, mutator), pinned, checked and without network.

Run from the project root (or any folder inside it):
  clean-code-measure.py status                  are the tools installed and verified; which sandbox this machine has
  clean-code-measure.py install                 install them in ~/.cache/keel/tools (uses the network; explicit)
  clean-code-measure.py crap FILE...            CRAP per function, with coverage from each file's own test
  clean-code-measure.py dry [PATH...]           structural duplication >= 0.8 (default: the files changed vs HEAD)
  clean-code-measure.py mutate FILE...          mutation testing of each file against its own test
Options:
  --test PATH       the test of the (single) FILE when the naming convention doesn't find it
  --diff [BASE]     mutate: only the functions the diff against BASE (default HEAD, untracked included) touches
  --budget SECONDS  mutate: total time; a file that doesn't finish is reported as not measured (default 600)
  --min-lines N     dry: smallest form compared, in lines (default 4, the tool's)
  --json            machine-readable summary on stdout (the gate reads it)
  --no-sandbox      run without network isolation when this machine has none (explicit, never the default)

Outputs stay in `.metrics/` and `target/mutation-workers/`, which must be ignored by git: the run refuses otherwise.
Coverage comes only from the report generated here for the measured test, never from older reports on disk.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CRAP_LIMIT = 10.0
DRY_THRESHOLD = "0.8"
OUTPUT_PATHS = (".metrics", "target/mutation-workers", "target/mutator-backup")
DI_CONSTRUCTOR = re.compile(r"^\s*constructor\s*\((?:[^()]|\([^()]*\))*\)\s*\{\s*\}\s*$", re.S)
MUTANT_LINE = re.compile(r"^SURVIVED\s+(\S+?):(\d+)\s+(.*)$")
TOTAL_LINE = re.compile(r"^Total\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", re.M)


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tools = load("clean-code-tools")
runners = load("clean-code-runners")


class Stop(Exception):
    """The run can't go on; the message says what to do."""


def diff_base(args):
    """`--diff BASE`, or HEAD when the next word is a flag or an existing path (the first file to measure)."""
    if args and not args[0].startswith("-") and not os.path.exists(args[0]):
        return args.pop(0)
    return "HEAD"


class Options:
    VALUED = {"--test": ("test", str), "--budget": ("budget", float), "--min-lines": ("min_lines", lambda v: str(int(v)))}
    SWITCHES = {"--json": "json", "--no-sandbox": "no_sandbox"}

    def __init__(self, argv):
        self.command = argv[0] if argv else "status"
        self.paths, self.test, self.diff, self.budget = [], None, None, 600.0
        self.min_lines, self.json, self.no_sandbox = "4", False, False
        self.help, self.unknown = False, []
        args = list(argv[1:])
        while args:
            self.take(args.pop(0), args)

    def take(self, arg, args):
        if arg in self.VALUED:
            name, convert = self.VALUED[arg]
            setattr(self, name, convert(args.pop(0)))
        elif arg in self.SWITCHES:
            setattr(self, self.SWITCHES[arg], True)
        elif arg == "--diff":
            self.diff = diff_base(args)
        elif arg in ("-h", "--help"):
            self.help = True
        elif arg.startswith("-"):
            self.unknown.append(arg)
        else:
            self.paths.append(os.path.abspath(arg))


def git(root, *args):
    result = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def project_root():
    top = git(os.getcwd(), "rev-parse", "--show-toplevel")
    if not top:
        raise Stop("not inside a git repository")
    return top.strip()


def check_outputs_ignored(root):
    for path in OUTPUT_PATHS:
        if subprocess.run(["git", "-C", root, "check-ignore", "-q", path + "/x"]).returncode != 0:
            raise Stop("`{}/` is not ignored by git, so the tools' outputs would dirty the repo. Run /keel:clean-code "
                       "(it adds the tools' output folders to .gitignore)".format(path))


def sandbox(options):
    prefix = tools.sandbox_prefix()
    if prefix is None and not options.no_sandbox:
        raise Stop("this machine has no network sandbox (macOS sandbox-exec, Linux bwrap or unshare). Install "
                   "bubblewrap, or rerun with --no-sandbox to accept running third-party code and the tests with "
                   "network access")
    if prefix is None:
        print("WARNING: running WITHOUT network isolation (--no-sandbox).", file=sys.stderr)
    return prefix or []


def run(command, root, env=None, timeout=None):
    """Runs in its own process group so a timeout kills the test runners it started too."""
    process = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, start_new_session=True)
    try:
        output, _ = process.communicate(timeout=timeout)
        return process.returncode, output
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        return None, output


def coverage_dir(root, test):
    key = hashlib.sha256(os.path.relpath(test, root).encode()).hexdigest()[:12]
    return os.path.join(root, ".metrics", "keel", "coverage", key)


def measured_test(source, root, options):
    test = options.test if options.test and len(options.paths) == 1 else runners.find_test(source, root)
    return os.path.abspath(test) if test else None


def generate_coverage(test, root, prefix):
    """Runs the test once with coverage; returns (plan, lcov path)."""
    out = coverage_dir(root, test)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    plan = runners.plan_for(test, root, out)
    for command in plan.coverage_commands:
        code, output = run(prefix + command, root)
        if code != 0:
            tail = "\n".join(output.strip().splitlines()[-15:])
            raise Stop("the test {} fails or doesn't run (exit {}); fix it before measuring:\n{}".format(
                runners.relative(test, root), code, tail))
    return plan, os.path.join(out, "lcov.info")


def run_tool(tool, lcov, args, root, prefix, timeout=None):
    command, env = tools.tool_command(tool, [lcov] + args, prefix)
    return run(command, root, env, timeout)


def merged_lcov(root, paths):
    target = os.path.join(root, ".metrics", "keel", "coverage", "merged.lcov")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as out:
        for path in paths:
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as handle:
                    out.write(handle.read().rstrip("\n") + "\n")
    return target


EDN_ENTRY = re.compile(r':name "((?:[^"\\]|\\.)*)", :namespace "((?:[^"\\]|\\.)*)", :complexity (\d+), '
                       r':coverage (nil|[\d.]+), :crap (nil|[\d.]+)')


def crap_entries(root):
    with open(os.path.join(root, ".metrics", "crap.edn"), encoding="utf-8") as handle:
        text = handle.read()
    return [{"name": name, "namespace": namespace, "complexity": int(cc),
             "coverage": None if cov == "nil" else float(cov), "crap": None if crap == "nil" else float(crap)}
            for name, namespace, cc, cov, crap in EDN_ENTRY.findall(text)]


def command_crap(options, root, prefix):
    lcovs, untested = [], []
    for source in options.paths:
        test = measured_test(source, root, options)
        if test is None:
            untested.append(runners.relative(os.path.abspath(source), root))
            continue
        lcovs.append(generate_coverage(test, root, prefix)[1])
    code, output = run_tool("crapper", merged_lcov(root, lcovs), ["--use-existing-coverage"] + options.paths,
                            root, prefix)
    if code not in (0, 2):
        raise Stop("crapper failed:\n" + output[-2000:])
    entries = crap_entries(root)
    above = [entry for entry in entries if entry["crap"] is not None and entry["crap"] >= CRAP_LIMIT]
    return {"tool": "crapper", "functions": len(entries), "above_limit": above, "untested": untested,
            "report": output}


def changed_files(root):
    tracked = git(root, "diff", "--name-only", "HEAD") or ""
    untracked = git(root, "ls-files", "--others", "--exclude-standard") or ""
    return sorted({name for name in (tracked + untracked).splitlines() if name and os.path.isfile(
        os.path.join(root, name))})


def read_span(root, span):
    with open(os.path.join(root, span["file"]), encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    return "\n".join(lines[span["start"] - 1:span["end"]])


DRY_ENTRY = re.compile(r':score ([\d.]+)\s+:language "(\w+)"\s+:left \{:file "((?:[^"\\]|\\.)*)", :start-line (\d+), '
                       r':end-line (\d+)\}\s+:right \{:file "((?:[^"\\]|\\.)*)", :start-line (\d+), :end-line (\d+)\}')


def dry_pairs(root):
    snapshot = os.path.join(root, ".metrics", "dry.edn")
    if not os.path.isfile(snapshot):
        return []
    with open(snapshot, encoding="utf-8") as handle:
        text = handle.read()
    pairs = []
    for score, language, lf, ls, le, rf, rs, re_ in DRY_ENTRY.findall(text):
        left = {"file": lf, "start": int(ls), "end": int(le)}
        right = {"file": rf, "start": int(rs), "end": int(re_)}
        pairs.append({"score": float(score), "language": language, "left": left, "right": right})
    return pairs


def injection_only(root, pair):
    """A constructor that only declares injected dependencies is wiring, not duplicated logic."""
    return all(DI_CONSTRUCTOR.match(read_span(root, pair[side])) for side in ("left", "right"))


def command_dry(options, root, prefix):
    paths = options.paths or changed_files(root)
    if not paths:
        return {"tool": "dryer", "pairs": [], "ignored_constructors": 0, "report": "No files to compare.\n"}
    args = ["--threshold", DRY_THRESHOLD, "--min-lines", options.min_lines] + paths
    code, output = run_tool("dryer", "-", args, root, prefix)
    if code != 0:
        raise Stop("dryer failed:\n" + output[-2000:])
    pairs = dry_pairs(root)
    kept = [pair for pair in pairs if not injection_only(root, pair)]
    return {"tool": "dryer", "pairs": kept, "ignored_constructors": len(pairs) - len(kept), "report": output}


def touched_lines(root, source, base):
    relative = runners.relative(os.path.abspath(source), root)
    if not git(root, "ls-files", "--error-unmatch", relative):
        return None
    if git(root, "rev-parse", "--verify", "--quiet", base + "^{commit}") is None:
        raise Stop("`--diff {}` is not a commit in this repository".format(base))
    diff = git(root, "diff", "-U0", base, "--", relative) or ""
    lines = set()
    for start, count in re.findall(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, count = int(start), int(count or "1")
        lines.update(range(start, start + max(count, 1)))
    return lines


def touched_function_lines(root, source, base, prefix):
    """Lines of every function the diff touches; None = the whole file (new file); empty = nothing to mutate."""
    lines = touched_lines(root, source, base)
    if lines is None:
        return None
    code, output = run_tool("spans", "-", [os.path.abspath(source)], root, prefix)
    if code != 0:
        raise Stop("could not read the functions of {}:\n{}".format(source, output[-1000:]))
    selected = set()
    for span in json.loads(output.strip().splitlines()[-1]):
        if any(span["start"] <= line <= span["end"] for line in lines):
            selected.update(range(span["start"], span["end"] + 1))
    return selected


def workers():
    return str(max(1, min(4, (os.cpu_count() or 2) // 2)))


def parse_mutants(output):
    survived = [{"file": path, "line": int(line), "mutation": mutation.strip()}
                for path, line, mutation in (match.groups() for match in map(MUTANT_LINE.match, output.splitlines())
                                             if match)]
    totals = TOTAL_LINE.findall(output)
    killed, _, uncovered, _ = (int(value) for value in totals[-1]) if totals else (0, 0, 0, 0)
    return {"killed": killed, "survived": survived, "uncovered": uncovered,
            "sites": killed + len(survived) + uncovered}


def mutate_file(source, root, options, prefix, deadline):
    relative = runners.relative(os.path.abspath(source), root)
    test = measured_test(source, root, options)
    if test is None:
        return {"file": relative, "status": "no test", "survived": []}
    lines = touched_function_lines(root, source, options.diff, prefix) if options.diff else None
    if lines is not None and not lines:
        return {"file": relative, "status": "no function touched", "survived": []}
    plan, lcov = generate_coverage(test, root, prefix)
    args = ["--use-existing-coverage", "--max-workers", workers(), "--test-command", plan.mutant_command]
    args += ["--lines", ",".join(str(line) for line in sorted(lines))] if lines else []
    started = time.time()
    code, output = run_tool("mutator", lcov, args + [relative], root, prefix, max(1.0, deadline - time.time()))
    result = dict(parse_mutants(output), file=relative, test=runners.relative(test, root),
                  seconds=round(time.time() - started, 1))
    result["status"] = {None: "not finished (budget)", 0: "all killed", 3: "survivors", 2: "baseline failed"}.get(
        code, "error {}".format(code))
    if code not in (0, 3):
        result["output"] = output[-1500:]
    return result


def clean_workers(root, before):
    base = os.path.join(root, "target", "mutation-workers")
    for name in set(os.listdir(base)) - before if os.path.isdir(base) else ():
        if name.startswith("run-"):
            shutil.rmtree(os.path.join(base, name), ignore_errors=True)


def command_mutate(options, root, prefix):
    deadline = time.time() + options.budget
    base = os.path.join(root, "target", "mutation-workers")
    before = set(os.listdir(base)) if os.path.isdir(base) else set()
    results = []
    try:
        for source in options.paths:
            if time.time() >= deadline:
                results.append({"file": runners.relative(source, root), "status": "not run (budget)",
                                "survived": []})
                continue
            results.append(mutate_file(source, root, options, prefix, deadline))
    finally:
        clean_workers(root, before)
    return {"tool": "mutator", "files": results, "budget_seconds": options.budget}


def print_crap(result):
    print(result["report"].rstrip())
    print("\nAt or above CRAP {}: {}".format(int(CRAP_LIMIT), len(result["above_limit"])))
    for entry in result["above_limit"]:
        print("  {namespace}.{name}  CC {complexity}  coverage {coverage}%  CRAP {crap}".format(**entry))
    for path in result["untested"]:
        print("  no test found for {}: its functions score 0% coverage".format(path))


def span_text(span):
    return "{}:{}-{}".format(span["file"], span["start"], span["end"])


def print_dry(result):
    print("Pairs >= {}: {} ({} injection-only constructors left out)".format(
        DRY_THRESHOLD, len(result["pairs"]), result["ignored_constructors"]))
    for pair in result["pairs"]:
        print("  {:.2f}  {}  ~  {}".format(pair["score"], span_text(pair["left"]), span_text(pair["right"])))


def print_mutate(result):
    for item in result["files"]:
        took = " in {}s".format(item["seconds"]) if "seconds" in item else ""
        print("{}: {}{}".format(item["file"], item["status"], took))
        for mutant in item["survived"]:
            print("  SURVIVED {}:{} {}".format(mutant["file"], mutant["line"], mutant["mutation"]))
        if item.get("output"):
            print(item["output"])


PRINTERS = {"crapper": print_crap, "dryer": print_dry, "mutator": print_mutate}


def print_human(result):
    PRINTERS[result["tool"]](result)


COMMANDS = {"crap": command_crap, "dry": command_dry, "mutate": command_mutate}


def main(argv):
    options = Options(argv)
    if options.command in ("status", "install"):
        return tools.main([options.command])
    if options.help or options.command in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if options.command not in COMMANDS:
        print(__doc__)
        return 64
    if options.unknown:
        print("Stopped: unknown option {}".format(" ".join(options.unknown)), file=sys.stderr)
        return 64
    try:
        root = project_root()
        check_outputs_ignored(root)
        prefix = sandbox(options)
        if options.command != "dry" and not options.paths:
            raise Stop("name the files to measure")
        result = COMMANDS[options.command](options, root, prefix)
    except (Stop, tools.ToolError, runners.RunnerError) as error:
        print("Stopped: {}".format(error), file=sys.stderr)
        return 1
    if options.json:
        result.pop("report", None)
        print(json.dumps(result, indent=1))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
