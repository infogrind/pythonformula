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

# Test a tag before pushing it: build the tarball locally with git archive
# and point the formula at it via a file:// url
uv run pythonformula ../myproject --local
```

The release tag defaults to the project's latest git tag; the GitHub archive
URL is derived from the project's `origin` remote, and its sha256 is computed
by downloading the tarball. Deployment stays manual — the tool prints the
`brew audit` / install / commit steps to follow.

## Development Cycle

The tool is built to let you iterate entirely locally before doing anything
that touches GitHub or the tap's git history.

### 1. Local, side-effect-free iteration

Repeat this as many times as needed; none of it pushes anything or leaves
your machine:

- `uv run pythonformula ../myproject --stdout --offline` renders the formula
  to stdout with no network access and no files written — the fastest way
  to check the output.
- Bump the version in `pyproject.toml` and create a local tag
  (`git tag vX.Y.Z`) in the project.
- `uv run pythonformula ../myproject --local` builds a tarball from that tag
  with `git archive` and points the formula at it via a `file://` url, so it
  never touches the network or GitHub.
- Run the printed `brew reinstall --build-from-source` and `brew test`
  commands to actually install and exercise the formula.
- If something's wrong, delete the local tag (`git tag -d vX.Y.Z`), fix it,
  and retag — nothing has been published, so there's nothing to undo.

### 2. Publish

Only once local testing passes:

- Push the tag: `git push --tags`.
- Rerun without `--local` (`uv run pythonformula ../myproject`) to fetch the
  real GitHub release tarball and compute its sha256.
- Run the printed `brew audit --strict`, install, and test commands again,
  now against the real url.
- Commit and push the formula in the tap, as printed in the final step.

## Run Tests

```shell
uv run pytest
```
