# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Generates or updates Homebrew formulas for uv-based Python projects. Pointed at a project directory (with `pyproject.toml` + `uv.lock`), it either writes a complete new `Formula/<name>.rb` into a local tap clone or surgically updates an existing one. Deployment is manual; the tool prints the steps. Requires Python >=3.13, zero runtime dependencies (stdlib only), managed with `uv`.

## Commands

```shell
# Run the tool
uv run pythonformula <project-dir> [--tap PATH] [--tag TAG] [--stdout] [--offline] [-v]

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_formula.py::test_update_formula
```

## Architecture

- `pythonformula/cli.py` — argparse, orchestration, warnings (stderr), tap auto-detection (`homebrew-tap` next to the project, then `~/github/homebrew-tap`), and printing the manual deploy steps.
- `pythonformula/uvlock.py` — parses `uv.lock` with stdlib `tomllib`; computes the transitive closure of the root package's *runtime* dependencies (dev groups excluded) and returns one `Resource` (name/url/sha256) per package with an sdist. Package names are PEP-503-normalized for matching; resource names use `-`→`_`.
- `pythonformula/project.py` — pyproject metadata (`ProjectInfo`) and git queries (latest tag, GitHub owner/repo from the `origin` remote) as small subprocess-based functions so tests can monkeypatch them.
- `pythonformula/formula.py` — renders a full formula (house style: `Language::Python::Virtualenv`, `virtualenv_install_with_resources`) and performs the surgical update: a line-oriented pass over the existing `.rb` that replaces only the top-level `url`/`sha256`, the python `depends_on`, and the `resource … end` blocks, preserving all hand-written parts (`desc`, `license`, `test do`, other `depends_on`).
- `pythonformula/tarball.py` — downloads the GitHub release tarball and computes its sha256 (skipped with `--offline`, which emits a `PLACEHOLDER`).

Key behaviors: the packaged version comes from the git tag, not pyproject's `version` (a mismatch triggers a warning, as do placeholder descriptions, missing licenses, no-sdist dependencies, and unexpected `depends_on` entries).

Tests are pytest-style; `tests/test_cli.py` runs `cli.main()` end-to-end on temp fixtures with git/network monkeypatched (`--offline`), and reuses the fixture lockfile from `tests/test_uvlock.py`.
