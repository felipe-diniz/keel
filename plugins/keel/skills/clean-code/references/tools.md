# The tools: audit, pins and updates

Read when installing the tools, updating one of them, reviewing what third-party code runs in the repository, or
when `status` reports a checkout, environment or grammar problem.

## Pins

All in `scripts/clean-code-tools.json` and `scripts/clean-code-requirements.txt` of the plugin; nothing else decides
a version.

| Tool | Repository | SHA (audited 15 Nov 2026) | License |
|---|---|---|---|
| crapper | github.com/unclebob/crapper | `c757ec79a6c15dc815238bbd9c2f4601eb54d3cc` | 0BSD |
| dryer | github.com/unclebob/dryer | `66ff6d21a42c04afcad89c78a80066176d1294b0` | 0BSD |
| mutator | github.com/unclebob/mutator | `830ec7e9c39664d753f8699015bc796df67727b9` | 0BSD |

Dependencies (the same for the three), installed with every hash required and wheels only: `tree-sitter 0.26.1`
(MIT) and `tree-sitter-language-pack 1.25.2` (MIT). Python 3.12 through `uv`. The tools themselves are not installed
as packages: their source runs from the pinned checkouts.

## What each tool does, as audited

| | crapper | dryer | mutator |
|---|---|---|---|
| Reads | the source files named (or the tree; `--changed` uses `git status`), LCOV / Go / JaCoCo reports | the source files named (or the tree; `--changed` uses `git status`) | the source files, the coverage reports (through crapper), its own `.metrics/mutate` history |
| Writes | `.metrics/crap.edn` | `.metrics/dry.edn` | `.metrics/mutate/*.edn`; worker overlays in `target/mutation-workers/run-*`, removed per file; restores files from `target/mutator-backup/` if a crashed old run left them |
| Executes | `git`; in its default coverage mode, the project's tests through `npm run coverage`, `vitest`, `npx --yes c8`, `coverage`/`pytest`, `cargo`, `mvn` | `git` | the test command once in the real tree (baseline), then per mutant inside the worker overlay |
| Installs (default mode only) | `npm install --no-save @vitest/coverage-v8`, `pip install coverage pytest` into the project's interpreter, `cargo install cargo-llvm-cov`, `npx --yes c8` | nothing | the same as crapper when it generates coverage |
| Network | none of its own; the installs above, and the grammar download | the grammar download | idem crapper |
| Telemetry | none in its Python source | none in its Python source | none in its Python source |

The source files are only read; mutants are written to private copies in the overlay, never to the original file.
The language pack's native library was checked only for the URLs it fetches (its release manifest and bundles);
the sandbox is what guarantees it reaches nothing at run time.

### How keel neutralizes the risks

- Coverage: crapper and mutator always run with `--use-existing-coverage`, and the shim points them at the report
  keel generated with the project's own runner. The default mode, which installs packages and runs `npx --yes`, never
  runs.
- Test command: the mutator's default for TypeScript is `npm test` (the whole suite per mutant); keel passes the
  single test file's command.
- Grammars: `tree-sitter-language-pack` 1.x downloads a bundle of native libraries from its GitHub release on the
  first use of a language, checked against a manifest that also comes from GitHub. keel downloads only in
  `install`, then checks the bundle and each library (TypeScript, TSX, JavaScript, Python) against the sha256
  recorded in keel for macOS arm64/x86_64 and Linux x86_64/aarch64. A mismatch deletes the download and aborts.
  Every run re-checks the libraries. Proxy environment variables don't stop that download; only the sandbox does.
- Network: every run, test runs included, is inside a sandbox without outbound network. On macOS the profile allows
  outbound traffic only to loopback; a profile that also allowed unix sockets was measured letting traffic out and
  was dropped.
- Integrity: each run checks that every checkout is at its SHA with no local change.

## Install, status, uninstall

```bash
python3 <plugin>/scripts/clean-code-measure.py status    # what is missing; no network
python3 <plugin>/scripts/clean-code-measure.py install   # uses the network once; writes only in ~/.cache/keel/tools
rm -rf ~/.cache/keel/tools                                # uninstall
```

`KEEL_TOOLS_HOME` moves the cache. Layout: `<tool>@<sha>/` (checkouts), `venv@<requirements hash>-py3.12/`,
`parsers@tslp-<version>/` (grammars). A new pin installs next to the old one; nothing is overwritten in place.

## Updating a tool (explicit, never automatic)

1. Read the diff between the pinned SHA and the new one: anything that runs commands, writes files, opens sockets,
   installs packages or changes the CLI flags keel passes (`--use-existing-coverage`, `--test-command`, `--lines`,
   `--max-workers`, `--threshold`, `--min-lines`) or the private function the shim patches
   (`crapper.coverage._lcov_paths`) and the EDN formats the wrapper parses.
2. If dependencies changed: regenerate `clean-code-requirements.txt` with
   `uv pip compile --generate-hashes --universal --python-version 3.12` from the exact versions.
3. If `tree-sitter-language-pack` changed: download each platform bundle from its release, compute its sha256
   yourself, extract the four libraries and record their sha256 too. Never copy the hashes from the release manifest.
4. Edit `clean-code-tools.json`, run the plugin's tests, measure one real file per runner, and update this file's
   audit date. One commit, with what changed and how it was checked.
