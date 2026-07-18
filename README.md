# pythonformula

Generates or updates a Homebrew formula for a uv-based Python project.

Point it at a project directory containing `pyproject.toml` and `uv.lock`. If
the formula already exists in your tap, it is updated surgically (top-level
`url`, `sha256`, python `depends_on`, and all `resource` blocks are replaced;
everything else, e.g. `desc` and the `test` block, is preserved). Otherwise a
complete new formula is generated.

## Usage

```shell
# Write Formula/<name>.rb into the tap (auto-detected: homebrew-tap next to
# the project, or ~/github/homebrew-tap)
uv run pythonformula ../myproject

# Print the formula instead of writing it
uv run pythonformula ../myproject --stdout

# Explicit tap and release tag
uv run pythonformula ../myproject --tap ../homebrew-tap --tag v1.2

# Skip the tarball download (leaves a sha256 placeholder)
uv run pythonformula ../myproject --offline
```

The release tag defaults to the project's latest git tag; the GitHub archive
URL is derived from the project's `origin` remote, and its sha256 is computed
by downloading the tarball. Deployment stays manual — the tool prints the
`brew audit` / install / commit steps to follow.

## Run Tests

```shell
uv run pytest
```
