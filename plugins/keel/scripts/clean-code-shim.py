"""Runs inside the clean-code tools' pinned environment (Python 3.12, started with `-I`), never on its own.

  clean-code-shim.py crapper <lcov> <args...>   crapper, reading coverage ONLY from <lcov>
  clean-code-shim.py mutator <lcov> <args...>   mutator, idem
  clean-code-shim.py dryer - <args...>          dryer, unchanged
  clean-code-shim.py spans - <file>             JSON list of the file's functions with their line spans

Why the coverage patch: crapper merges every `coverage/**/lcov.info` and `target/coverage/**/lcov.info` of the
project, and a stale report from another run would score code the tests no longer cover. keel generates a fresh
report per measured test and points the tools at it alone. `<lcov>` = `-` means no coverage.

The tools' source comes from the pinned checkouts listed in KEEL_TOOL_SRC; nothing is installed as a package.
"""
import json
import os
import sys
from pathlib import Path


def add_sources():
    for path in reversed(os.environ.get("KEEL_TOOL_SRC", "").split(os.pathsep)):
        if path:
            sys.path.insert(0, path)


def only_this_lcov(lcov):
    import crapper.coverage

    report = Path(lcov) if lcov != "-" else None
    crapper.coverage._lcov_paths = lambda root: [report] if report and report.is_file() else []


def spans(path):
    from crapper.discover import language_of
    from crapper.languages import functions_in_file

    file = Path(path)
    language = language_of(file)
    if language is None:
        return []
    source = file.read_text(encoding="utf-8", errors="replace")
    return [{"name": item.name, "start": item.start_line, "end": item.end_line}
            for item in functions_in_file(language, source, file.as_posix(), ".")]


def main(argv):
    add_sources()
    tool, lcov, args = argv[0], argv[1], argv[2:]
    if tool == "spans":
        print(json.dumps(spans(args[0])))
        return 0
    if tool in ("crapper", "mutator"):
        only_this_lcov(lcov)
    if tool not in ("crapper", "mutator", "dryer"):
        print("unknown tool: " + tool, file=sys.stderr)
        return 64
    module = __import__(tool + ".cli", fromlist=["main"])
    return module.main(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
