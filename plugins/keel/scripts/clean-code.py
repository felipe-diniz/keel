#!/usr/bin/env python3
"""The clean-code package in a project: size ratchet, its script, the tools' ignored outputs and the lint proposal.

Usage (from inside the project):
  clean-code.py             plan for this project (nothing is written)
  clean-code.py --apply     write size-budget.json, scripts/size-budget.py and the .gitignore lines
  clean-code.py --decline   don't install the package here: silences the suggestion (stored on this machine)
  clean-code.py --hook      SessionStart: says something only when the package is missing or behind

Rerunning keeps every ceiling already lowered: an entry only goes down, and a file that grew past its ceiling is
reported, never re-baselined. The lint block is printed for the agent to apply after the user's confirmation; this
script never edits a lint config.
"""
import datetime
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "size-budget.py")
SCRIPT_PATH = "scripts/size-budget.py"
DECLINED = ".keel-clean-code-declined"
GITIGNORE_LINES = ["/.metrics/", "/target/mutation-workers/", "/target/mutator-backup/"]
JS_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"]
PYTHON_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile")
FLAT_CONFIGS = tuple("eslint.config." + ext for ext in ("js", "mjs", "cjs", "ts", "mts", "cts"))
LEGACY_CONFIGS = (".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml")
SUGGEST = "PLUGIN NOTICE (clean-code): {} In the first reply, suggest the user run /keel:clean-code.\n"


def load_budget_module():
    spec = importlib.util.spec_from_file_location("size_budget", TEMPLATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


budget_module = load_budget_module()


def read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def find_root(start):
    current = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def main_root(root):
    marker = os.path.join(root, ".git")
    if not os.path.isfile(marker):
        return root
    line = (read(marker) or "").strip()
    gitdir = line[len("gitdir:"):].strip() if line.startswith("gitdir:") else ""
    head, sep, _ = gitdir.partition(os.sep + ".git" + os.sep + "worktrees" + os.sep)
    return head if sep else root


def declined_marker(root):
    home = os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")
    slug = re.sub(r"[^A-Za-z0-9]", "-", main_root(root))
    return os.path.join(home, "projects", slug, DECLINED)


def package_json(root):
    try:
        data = json.loads(read(os.path.join(root, "package.json")) or "null")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


FRAMEWORKS = (("Angular", "@angular/core"), ("Next.js", "next"), ("React", "react"), ("Vue", "vue"),
              ("Svelte", "svelte"))


def dependencies(package):
    deps = {}
    for key in ("dependencies", "devDependencies"):
        deps.update(package.get(key) or {})
    return deps


def first_file(root, names):
    return next((name for name in names if os.path.isfile(os.path.join(root, name))), None)


def eslint_flavor(root, package):
    """("flat" | "legacy", config) or None."""
    flat = first_file(root, FLAT_CONFIGS)
    if flat:
        return "flat", flat
    legacy = first_file(root, LEGACY_CONFIGS)
    if legacy:
        return "legacy", legacy
    return ("legacy", "package.json#eslintConfig") if package.get("eslintConfig") else None


def detect(root):
    """The stack as the lint proposal and the budget's extensions need it."""
    package = package_json(root)
    deps = dependencies(package or {})
    return {
        "js": package is not None,
        "python": first_file(root, PYTHON_MARKERS) is not None,
        "frameworks": [name for name, dep in FRAMEWORKS if dep in deps],
        "eslint": eslint_flavor(root, package or {}),
        "sonarjs": os.path.isdir(os.path.join(root, "node_modules", "eslint-plugin-sonarjs")),
    }


def extensions(stack):
    found = list(JS_EXTENSIONS) if stack["js"] else []
    found += [".vue"] if "Vue" in stack["frameworks"] else []
    found += [".svelte"] if "Svelte" in stack["frameworks"] else []
    found += [".py"] if stack["python"] else []
    return found or list(budget_module.DEFAULT_EXTENSIONS)


def planned_budget(root, stack):
    """(budget to write, notes). New: the baseline. Existing: only lowered, never raised, nothing re-baselined."""
    current = budget_module.read_budget(root)
    fresh = budget_module.new_budget()
    fresh["extensions"] = extensions(stack)
    fresh["script"] = SCRIPT_PATH
    if current is None:
        fresh["files"] = budget_module.baseline(budget_module.measure(root, budget_module.Rules(fresh)))
        return fresh, ["new baseline: {} files above {} lines keep their own ceiling".format(
            len(fresh["files"]), fresh["defaultMax"])]
    adopting = "keel" not in current
    merged = dict(fresh)
    merged.update({key: value for key, value in current.items() if key not in ("keel", "files")})
    merged["files"] = dict(current.get("files") or {})
    counts = budget_module.measure(root, budget_module.Rules(merged))
    files, breaches, lowered, removed = budget_module.ratchet(merged, counts)
    notes = ["ceiling lowered: {} {} -> {}".format(*item) for item in lowered]
    notes += ["entry dropped (fits the default now): {}".format(item[0]) for item in removed]
    for path, lines, ceiling in breaches:
        if adopting and path not in merged["files"]:
            files[path] = lines
            notes.append("adopted: {} ({} lines) was outside the old budget's scope".format(path, lines))
        else:
            notes.append("ABOVE its ceiling, kept at {}: {} has {} lines (shrink it; never raise it here)".format(
                ceiling, path, lines))
    merged["files"] = files
    merged["keel"] = budget_module.KEEL_PACKAGE
    return merged, notes


def gitignore_missing(root):
    text = read(os.path.join(root, ".gitignore")) or ""
    present = {line.strip() for line in text.splitlines()}
    return [line for line in GITIGNORE_LINES if line not in present and line.lstrip("/") not in present]


def script_state(root, budget):
    path = os.path.join(root, budget.get("script") or SCRIPT_PATH)
    installed = read(path)
    if installed is None:
        return "missing"
    return "current" if installed == read(TEMPLATE) else "outdated"


FLAT_BLOCK = """// keel clean-code: file size ratchet (size-budget.json, only goes down) and function alarms.
// ESM config; in eslint.config.cjs use: const sizeBudget = require('./size-budget.json');
import {{ readFileSync }} from 'node:fs';
{sonar_import}const sizeBudget = JSON.parse(readFileSync(new URL('./size-budget.json', import.meta.url), 'utf8'));
const sizeRule = (max) => ['error', {{ max, skipBlankLines: false, skipComments: false }}];

// inside the exported array:
  {{
    files: ['{files_glob}'],
    ignores: sizeBudget.ignore,
{sonar_plugin}    rules: {{
      'max-lines': sizeRule(sizeBudget.defaultMax),
      'max-lines-per-function': ['warn', {{ max: 150, skipBlankLines: true, skipComments: true, IIFEs: true }}],
{sonar_rule}    }},
  }},
  ...Object.entries(sizeBudget.files).map(([file, max]) => ({{ files: [file], rules: {{ 'max-lines': sizeRule(max) }} }})),
"""

LEGACY_BLOCK = """// keel clean-code, legacy .eslintrc (a JSON or YAML config can't read the budget: convert it to .eslintrc.js,
// or write one override per entry of size-budget.json and regenerate them after each --update).
const sizeBudget = require('./size-budget.json');
const sizeRule = (max) => ['error', {{ max, skipBlankLines: false, skipComments: false }}];
module.exports = {{
  // ...the existing config
{sonar_plugin_legacy}  rules: {{
    'max-lines': sizeRule(sizeBudget.defaultMax),
    'max-lines-per-function': ['warn', {{ max: 150, skipBlankLines: true, skipComments: true, IIFEs: true }}],
{sonar_rule}  }},
  ignorePatterns: sizeBudget.ignore,
  overrides: Object.entries(sizeBudget.files).map(([file, max]) => ({{ files: [file], rules: {{ 'max-lines': sizeRule(max) }} }})),
}};
"""


SONAR_VALUES = {
    "sonar_import": "import sonarjs from 'eslint-plugin-sonarjs';\n",
    "sonar_plugin": "    plugins: { sonarjs },\n",
    "sonar_plugin_legacy": "  plugins: ['sonarjs'],\n",
    "sonar_rule": "      'sonarjs/cognitive-complexity': ['warn', 15],\n",
}
NO_SONAR_NOTE = ("eslint-plugin-sonarjs is not installed, so cognitive complexity is left out; adding it is the "
                 "project's decision (keel installs nothing).\n")


def files_glob(budget):
    """`**/*.ts` for one extension, `**/*{.ts,.tsx}` for several: minimatch reads a one-element brace literally."""
    exts = [ext for ext in budget["extensions"] if ext in JS_EXTENSIONS + [".vue", ".svelte"]]
    if len(exts) == 1:
        return "**/*" + exts[0]
    return "**/*{" + ",".join(exts) + "}" if exts else None


def lint_proposal(stack, budget):
    glob = files_glob(budget)
    if not stack["eslint"] or not glob:
        return None
    sonar = stack["sonarjs"]
    values = dict(SONAR_VALUES) if sonar else dict.fromkeys(SONAR_VALUES, "")
    values["files_glob"] = glob
    kind, config = stack["eslint"]
    if kind == "flat":
        block = FLAT_BLOCK.format(**values)
    else:
        block = LEGACY_BLOCK.format(**values).replace("      'sonarjs", "    'sonarjs")
    return "Lint block for {} ({}):\n{}{}".format(config, kind, "" if sonar else NO_SONAR_NOTE, block)


def plan(root):
    stack = detect(root)
    budget, notes = planned_budget(root, stack)
    steps = []
    existing = budget_module.read_budget(root)
    if existing is None:
        steps.append(("budget", "create size-budget.json (defaultMax {}, {} own ceilings)".format(
            budget["defaultMax"], len(budget["files"]))))
    elif json.dumps(existing, sort_keys=True) != json.dumps(budget, sort_keys=True):
        steps.append(("budget", "update size-budget.json (ceilings only go down)"))
    state = script_state(root, budget)
    if state != "current":
        steps.append(("script", "{} {}".format("create" if state == "missing" else "update", budget["script"])))
    missing = gitignore_missing(root)
    if missing:
        steps.append(("gitignore", "add to .gitignore: {}".format(" ".join(missing))))
    return {"root": root, "stack": stack, "budget": budget, "notes": notes, "steps": steps, "gitignore": missing}


def apply(state):
    root, budget = state["root"], state["budget"]
    done = []
    for kind, text in state["steps"]:
        if kind == "budget":
            budget_module.write_budget(root, budget)
        elif kind == "script":
            target = os.path.join(root, budget["script"])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(read(TEMPLATE))
            os.chmod(target, 0o755)
        elif kind == "gitignore":
            path = os.path.join(root, ".gitignore")
            text_before = read(path) or ""
            block = ("" if not text_before or text_before.endswith("\n") else "\n")
            block += "\n# keel clean-code: tools' outputs\n" + "\n".join(state["gitignore"]) + "\n"
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(block)
        done.append(text)
    return done


def describe(state):
    stack = state["stack"]
    kinds = [name for name, on in (("JS/TS", stack["js"]), ("Python", stack["python"])) if on]
    lines = ["Project: {}".format(state["root"]),
             "Stack: {}{}".format(", ".join(kinds) or "not detected (default extensions)",
                                  " ({})".format(", ".join(stack["frameworks"])) if stack["frameworks"] else "")]
    lines += ["- " + text for _, text in state["steps"]] or ["Nothing to write: the package is installed and current."]
    lines += ["Note: " + note for note in state["notes"]]
    proposal = lint_proposal(stack, state["budget"])
    if proposal:
        lines.append(proposal)
    lines.append("CI and pre-commit: run `python3 {}` (exit 1 when a file is above its ceiling).".format(
        state["budget"]["script"]))
    return "\n".join(lines)


def is_code_project(root):
    return os.path.isfile(os.path.join(root, "package.json")) or any(
        os.path.isfile(os.path.join(root, name)) for name in PYTHON_MARKERS)


MISSING = ("this project has no size budget (keel's standard: new files up to 1,000 lines, existing ones on a "
           "ceiling that only goes down) and no clean-code measurement. The user can also decline there.")
BEHIND = ("the clean-code package in this project is behind the plugin's (size budget or its script); rerunning "
          "updates it and keeps every ceiling already lowered.")


def installed_package(root, budget):
    """The lower of the budget's and the script's package numbers (0 when either is missing)."""
    script = read(os.path.join(root, budget.get("script") or SCRIPT_PATH)) or ""
    found = re.search(r"^KEEL_PACKAGE = (\d+)", script, re.M)
    return min(int(budget.get("keel") or 0), int(found.group(1)) if found else 0)


def hook_output(cwd, source):
    root = find_root(cwd)
    if not root or source not in ("startup", "clear"):
        return ""
    budget = budget_module.read_budget(root)
    if budget is not None:
        return SUGGEST.format(BEHIND) if installed_package(root, budget) < budget_module.KEEL_PACKAGE else ""
    if is_code_project(root) and not os.path.isfile(declined_marker(root)):
        return SUGGEST.format(MISSING)
    return ""


def decline(root):
    marker = declined_marker(root)
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write(datetime.date.today().isoformat() + "\n")


def run_hook():
    try:
        payload = json.load(sys.stdin)
        sys.stdout.write(hook_output(payload.get("cwd") or os.getcwd(), payload.get("source") or "startup"))
    except Exception:
        pass
    return 0


def install(root, applying):
    state = plan(root)
    print(describe(state))
    if not state["steps"]:
        return 0
    if applying:
        print("Done:\n" + "\n".join("- " + text for text in apply(state)))
    else:
        print("Nothing was written. Apply with --apply after the user confirms.")
    return 0


def main(argv):
    if "--hook" in argv:
        return run_hook()
    root = find_root(os.getcwd())
    if not root:
        print("Not inside a git repository: the package needs one.")
        return 1
    if "--decline" in argv:
        decline(root)
        print("Declined on this machine, outside the repo: the plugin no longer suggests the package here.")
        return 0
    return install(root, "--apply" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
