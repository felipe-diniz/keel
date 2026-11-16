#!/usr/bin/env python3
"""File size budget with a ratchet. Installed by the keel plugin (`/keel:clean-code`); self-contained, stdlib only.

Every source file the budget covers has a line ceiling: `defaultMax` for files that fit it, and for files that were
already above it on the day of the baseline, their own count on that day, recorded in `size-budget.json` at the
project root. A ceiling ONLY GOES DOWN: `--update` after shrinking a file lowers its entry (or removes it when the file
fits the default). Raising a ceiling is a manual edit of the JSON, visible in the diff, with the reason in the commit.

  python3 scripts/size-budget.py            report: who is above their ceiling, who can go down; exit 1 on a breach
  python3 scripts/size-budget.py --update   lower ceilings and drop obsolete entries; never raises one
  python3 scripts/size-budget.py --init     write the baseline (refuses when the JSON already exists)

Lines are counted like ESLint's `max-lines` with blank lines and comments included: the file's lines, without the
empty line left by the final newline.
"""
import json
import os
import re
import subprocess
import sys

KEEL_PACKAGE = 1
BUDGET_NAME = "size-budget.json"
DEFAULT_MAX = 1000
DEFAULT_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".py", ".vue", ".svelte"]
# Generated code, dependencies, build output, lock files, SQL migrations and tests: what the budget doesn't count
# unless the project removes the pattern.
DEFAULT_IGNORE = [
    "**/node_modules/**", "**/vendor/**", "**/dist/**", "**/build/**", "**/out/**", "**/coverage/**",
    "**/.next/**", "**/.nx/**", "**/.angular/**", "**/.venv/**", "**/venv/**", "**/__pycache__/**", "**/target/**",
    "**/.metrics/**", "**/generated/**", "**/*.generated.*", "**/*.gen.*", "**/*.d.ts", "**/*.min.js",
    "**/*lock*", "**/migrations/**/*.sql", "**/*.spec.*", "**/*.test.*", "**/__tests__/**", "**/tests/**",
    "**/test/**", "**/test_*.py", "**/*_test.py", "**/conftest.py",
]
SKIP_DIRS = {"node_modules", "vendor", "dist", "build", "out", "coverage", ".next", ".nx", ".angular", ".venv",
             "venv", "__pycache__", "target", ".metrics", ".git"}


def glob_regex(pattern):
    """`**/` spans directories (zero or more), `*` and `?` stay inside one path segment."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def new_budget(files=None):
    return {"keel": KEEL_PACKAGE, "defaultMax": DEFAULT_MAX, "extensions": list(DEFAULT_EXTENSIONS),
            "ignore": list(DEFAULT_IGNORE), "files": dict(files or {})}


def with_defaults(budget):
    """The keys a budget may omit (an older or hand-written one) take the defaults; what it declares wins."""
    merged = new_budget()
    merged.update({key: value for key, value in budget.items() if value is not None})
    merged["files"] = dict(budget.get("files") or {})
    return merged


class Rules:
    """Which files the budget covers and the ceiling of each."""

    def __init__(self, budget):
        budget = with_defaults(budget)
        self.default_max = int(budget["defaultMax"])
        self.extensions = tuple(budget["extensions"])
        self.ignore = [glob_regex(pattern) for pattern in budget["ignore"]]
        self.files = {path: int(ceiling) for path, ceiling in budget["files"].items()}

    def covers(self, relative):
        relative = relative.replace(os.sep, "/")
        if not relative.endswith(self.extensions):
            return False
        return not any(pattern.match(relative) for pattern in self.ignore)

    def ceiling(self, relative):
        return self.files.get(relative.replace(os.sep, "/"), self.default_max)


def count_lines(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if not data:
        return 0
    lines = data.count(b"\n")
    return lines if data.endswith(b"\n") else lines + 1


def read_budget(root):
    path = os.path.join(root, BUDGET_NAME)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_budget(root, budget):
    budget = dict(budget)
    budget["files"] = dict(sorted(budget.get("files", {}).items()))
    with open(os.path.join(root, BUDGET_NAME), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(budget, indent=2, ensure_ascii=False) + "\n")


def git_files(root):
    try:
        result = subprocess.run(["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    names = result.stdout.decode("utf-8", "surrogateescape").split("\0")
    return [name for name in names if name and os.path.isfile(os.path.join(root, name))]


def walked_files(root):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for name in filenames:
            yield os.path.relpath(os.path.join(directory, name), root).replace(os.sep, "/")


def measure(root, rules):
    """{relative path: line count} of every file the budget covers."""
    names = git_files(root)
    if names is None:
        names = walked_files(root)
    return {name: count_lines(os.path.join(root, name)) for name in names if rules.covers(name)}


def baseline(counts, default_max=DEFAULT_MAX):
    return {path: lines for path, lines in counts.items() if lines > default_max}


def ratchet(budget, counts):
    """The budget after `--update`, and what it found: (files, breaches, lowered, removed).

    A ceiling never goes up and no entry is added: a file that crossed its ceiling is a breach, not a new baseline.
    """
    rules = Rules(budget)
    files, breaches, lowered, removed = {}, [], [], []
    for path, ceiling in sorted(rules.files.items()):
        lines = counts.get(path)
        if lines is None or lines <= rules.default_max:
            removed.append((path, ceiling, lines))
        elif lines > ceiling:
            breaches.append((path, lines, ceiling))
            files[path] = ceiling
        else:
            if lines < ceiling:
                lowered.append((path, ceiling, lines))
            files[path] = lines
    for path, lines in sorted(counts.items()):
        if lines > rules.default_max and path not in rules.files:
            breaches.append((path, lines, rules.default_max))
    return files, breaches, lowered, removed


def find_root(start):
    current = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(current, BUDGET_NAME)) or os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.abspath(start)
        current = parent


def rows(items):
    return "\n".join("  {}  {} -> {}".format(path, a, "deleted" if b is None else b) for path, a, b in items)


def init(root):
    if read_budget(root) is not None:
        print("{} already exists. Use --update (only lowers) or edit it by hand.".format(BUDGET_NAME))
        return 1
    budget = new_budget()
    budget["files"] = baseline(measure(root, Rules(budget)))
    write_budget(root, budget)
    print("Baseline written: {} files above {} lines.".format(len(budget["files"]), DEFAULT_MAX))
    return 0


def report(root, update):
    budget = read_budget(root)
    if budget is None:
        print("No {} at {}. Run with --init to write the baseline.".format(BUDGET_NAME, root))
        return 1
    files, breaches, lowered, removed = ratchet(budget, measure(root, Rules(budget)))
    if update:
        budget["files"] = files
        write_budget(root, budget)
        print("Budget updated: {} files with their own ceiling.".format(len(files)))
    if lowered:
        print("{} ({}):\n{}".format("Lowered" if update else "Can go down (--update)", len(lowered), rows(lowered)))
    if removed:
        print("{} ({}):\n{}".format("Removed" if update else "Obsolete (--update removes)", len(removed), rows(removed)))
    if breaches:
        print("ABOVE their ceiling ({}):\n{}".format(len(breaches), rows(breaches)), file=sys.stderr)
        return 1
    print("No file above its ceiling ({} with their own ceiling, default {}).".format(
        len(files), Rules(budget).default_max))
    return 0


def main(argv):
    root = find_root(os.getcwd())
    if "--init" in argv:
        return init(root)
    return report(root, "--update" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
