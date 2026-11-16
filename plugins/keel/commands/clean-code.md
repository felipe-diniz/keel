---
description: Install or update keel's clean-code package in this project - size budget with a ratchet (new files up to 1,000 lines), its script, the lint block, and the pinned crapper/dryer/mutator tools
allowed-tools: Bash(python3 *)
disable-model-invocation: true
---

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/clean-code.py"` from the project root and show the user the plan as it came: what it would write, the notes (lowered, adopted and above-ceiling files) and the lint block.
2. If it says there is nothing to write, go to step 5. If the user doesn't want the package in this project, run it with `--decline` and stop.
3. Ask whether to apply. Only with a yes in this session, run it again with `--apply` and show the result. It writes `size-budget.json`, `scripts/size-budget.py` and the `.gitignore` lines, nothing else.
4. Lint: with an ESLint config, show the block the plan printed and where it goes, and ask. Only with a yes, insert it in the project's config, in that file's style, and run the project's lint on one file to prove it loads. A file the lint now flags above its ceiling was already above it: report it, don't raise its ceiling. Without ESLint (Python), propose adding `python3 scripts/size-budget.py` to the project's pre-commit or CI, in the project's own format, and apply only with a yes.
5. Tools: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/clean-code-measure.py" status`. If they are not ready, say that installing clones crapper, dryer and mutator at pinned SHAs, creates a Python 3.12 environment with hash-pinned dependencies and downloads the grammars checked against keel's sha256, all in `~/.cache/keel/tools`, using the network once; ask, and only with a yes run it with `install`. If this machine has no network sandbox, say so: measuring will need an explicit `--no-sandbox`.
6. Commit the files written in steps 3 and 4, by path, in one commit of their own, following the project's commit convention. No push.
