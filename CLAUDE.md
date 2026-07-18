# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Converts the dependencies in a `uv.lock` file (read from stdin) into Homebrew Formula `resource` blocks (written to stdout). Requires Python >=3.13 and uses `uv` for environment management.

## Commands

```shell
# Run the script
uv run main.py < uv.lock

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_main.py::TestMain::test_script
```

Pass `-v`/`--verbose` to the script to print debug output to stderr.

## Architecture

All logic lives in `main.py`:

- `StdinReader` wraps `sys.stdin` with single-line lookahead (`peek()`/`next()`) and line-number tracking.
- The parser is a hand-rolled, line-oriented parser using regexes on lines — it does not parse TOML generally. It skips the lockfile's initial fields, then processes each `[[package]]` section: extracting `name` (with `-` converted to `_`) and the `sdist` url/hash. Packages without an sdist entry (e.g. virtual packages) are silently skipped.
- Output is printed directly during parsing, one Homebrew `resource` block per package.

The single test in `tests/test_main.py` is end-to-end: it patches stdin/stdout and compares the full output for a sample lockfile.
