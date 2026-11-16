#!/usr/bin/env python3
"""PostToolUse (Write|Edit|MultiEdit): counts the lines of the edited file against its ceiling and warns the agent.

The ceiling comes from the project's `size-budget.json` (its own entry, or `defaultMax`), and without a budget it is
1,000 lines. What the budget doesn't cover (generated, lock, vendor, SQL migration, test, another extension) is skipped
the way the budget declares. It never blocks: the warning goes back as context for the agent. Fast and dependency-free:
no git, no network, one file read. A project that declined `/keel:clean-code` and has no budget gets no warning. An
internal failure stays quiet.
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DECLINED = ".keel-clean-code-declined"
NEAR = 0.9


def load_budget_module():
    spec = importlib.util.spec_from_file_location("size_budget", os.path.join(HERE, "size-budget.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_root(path):
    """The nearest folder with a `size-budget.json`, else the nearest with `.git`; None outside a project."""
    current = os.path.dirname(path)
    git_root = None
    while True:
        if os.path.isfile(os.path.join(current, "size-budget.json")):
            return current, True
        if git_root is None and os.path.exists(os.path.join(current, ".git")):
            git_root = current
        parent = os.path.dirname(current)
        if parent == current:
            return git_root, False
        current = parent


def main_root(root):
    """A worktree's `.git` is a file pointing into the main checkout's `.git/worktrees/`: the decline is the main's."""
    marker = os.path.join(root, ".git")
    if not os.path.isfile(marker):
        return root
    with open(marker, encoding="utf-8") as handle:
        line = handle.readline().strip()
    gitdir = line[len("gitdir:"):].strip() if line.startswith("gitdir:") else ""
    head, sep, _ = gitdir.partition(os.sep + ".git" + os.sep + "worktrees" + os.sep)
    return head if sep else root


def declined(root):
    """Same place `/keel:clean-code --decline` writes: this machine's folder for the project, outside the repo."""
    home = os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")
    slug = re.sub(r"[^A-Za-z0-9]", "-", main_root(root))
    return os.path.isfile(os.path.join(home, "projects", slug, DECLINED))


def message(relative, lines, ceiling, own):
    if lines > ceiling:
        kind = "its own ceiling in size-budget.json (it only goes down)" if own else "the ceiling for a file"
        return ("SIZE (keel clean-code): {} has {} lines, above {} of {}. Don't grow it: move what you added, or a "
                "whole responsibility, to its own file (skill keel:clean-code, size). The lint and the ratchet "
                "fail on it.".format(relative, lines, kind, ceiling))
    return ("SIZE (keel clean-code): {} has {} lines, close to its ceiling of {}. A new responsibility goes to its "
            "own file.".format(relative, lines, ceiling))


def edited_file(payload):
    path = (payload.get("tool_input") or {}).get("file_path")
    if not path:
        return None
    path = os.path.abspath(os.path.join(payload.get("cwd") or os.getcwd(), path))
    return path if os.path.isfile(path) else None


def rules_for(path):
    """(budget module, rules, root) that apply to the file, or None when nothing applies."""
    root, has_budget = project_root(path)
    if root is None or (not has_budget and declined(root)):
        return None
    budget_module = load_budget_module()
    budget = budget_module.read_budget(root) if has_budget else None
    return budget_module, budget_module.Rules(budget or {}), root


def verdict(budget_module, rules, path, relative):
    lines = budget_module.count_lines(path)
    ceiling = rules.ceiling(relative)
    own = relative in rules.files
    if lines > ceiling or (not own and lines >= NEAR * ceiling):
        return message(relative, lines, ceiling, own)
    return None


def check(payload):
    path = edited_file(payload)
    applying = rules_for(path) if path else None
    if not applying:
        return None
    budget_module, rules, root = applying
    relative = os.path.relpath(path, root).replace(os.sep, "/")
    return verdict(budget_module, rules, path, relative) if rules.covers(relative) else None


def main():
    try:
        text = check(json.load(sys.stdin))
    except Exception:
        return
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))


if __name__ == "__main__":
    main()
