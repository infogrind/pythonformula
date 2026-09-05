import argparse
import sys
import tempfile
import urllib.error
from pathlib import Path

from pythonformula import formula, project, tarball, uvlock

SHA_PLACEHOLDER = "PLACEHOLDER"

verbose = False


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def debug(message: str) -> None:
    if verbose:
        print(f" 🐞 {message}", file=sys.stderr)


def find_tap(project_dir: Path) -> Path | None:
    candidates = (
        project_dir.parent / "homebrew-tap",
        Path.home() / "github" / "homebrew-tap",
    )
    for candidate in candidates:
        if (candidate / "Formula").is_dir():
            return candidate
    return None


def print_next_steps(
    tap: Path, formula_path: Path, name: str, tag: str, *, local: bool = False
) -> None:
    relative = formula_path.relative_to(tap)
    tap_id = project.tap_name(tap) or "<owner>/<tap>"
    steps = [f"Review:  git -C {tap} diff {relative}"]
    if local:
        steps += [
            f"Install: brew reinstall --build-from-source {tap_id}/{name}",
            f"Test:    brew test {name}",
            f"Publish: push the tag ({tag}) to GitHub, rerun pythonformula "
            "without --local, then commit and push the tap",
        ]
    else:
        steps += [
            f"Audit:   brew audit --strict {tap_id}/{name}",
            f"Install: brew install --build-from-source {tap_id}/{name}",
            f"Test:    brew test {name}",
            f'Publish: git -C {tap} add {relative} && git -C {tap} commit -m "{name} {tag}" && git -C {tap} push',
        ]
    # Homebrew only installs formulas addressed through an installed tap. If
    # the tap directory is not brew's own clone, the formula must be staged
    # there for the brew commands to see it, and cleaned up afterwards.
    if "Library/Taps" not in str(tap.resolve()):
        brew_clone = f'"$(brew --repository {tap_id})"'
        steps.insert(1, f"Stage:   cp {formula_path} {brew_clone}/Formula/")
        steps.append(f"Clean:   git -C {brew_clone} checkout Formula/ && brew update")
    numbered = "\n".join(f"  {n}. {step}" for n, step in enumerate(steps, 1))
    print(f"\nNext steps:\n{numbered}", file=sys.stderr)


WORKFLOW = """\
Recommended workflow:
  1. Local, side-effect-free iteration (repeat freely; nothing external changes):
       - Preview the rendered formula with --stdout --offline: no network
         access, no files written, no tap required.
       - Bump the version in pyproject.toml and `git tag vX.Y.Z` locally.
       - Run with --local to build the formula against a tarball made from
         that tag with `git archive` (a file:// url), so it can be
         installed and tested before the tag is pushed anywhere.
       - `brew reinstall --build-from-source <tap>/<name>` and
         `brew test <name>` to validate. Freely `git tag -d` and retag to
         iterate; nothing has left your machine yet.

  2. Publish (only once local testing passes):
       - Push the tag: `git push --tags`.
       - Rerun pythonformula without --local to fetch the real GitHub
         release tarball and compute its sha256.
       - `brew audit --strict`, install, and test again, now against the
         real url.
       - Commit and push the updated formula in the tap.

Every run prints the exact next steps (Review/Audit/Install/Test/Publish)
for the mode it ran in.
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate or update a Homebrew formula for a uv-based Python project.",
        epilog=WORKFLOW,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Directory containing pyproject.toml and uv.lock.",
    )
    parser.add_argument(
        "--tap",
        type=Path,
        help="Path to a local Homebrew tap clone (default: homebrew-tap next to "
        "the project, then ~/github/homebrew-tap).",
    )
    parser.add_argument(
        "--tag",
        help="Release tag to package (default: the project's latest git tag).",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the formula instead of writing it into the tap.",
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--offline",
        action="store_true",
        help="Do not download the release tarball; leave a sha256 placeholder.",
    )
    source_group.add_argument(
        "--local",
        action="store_true",
        help="Build the tag's tarball locally with git archive and point the "
        "formula at it via a file:// url, so it can be tested before the tag "
        "is pushed to GitHub.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print debug output to stderr.",
    )
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    project_dir = args.project_dir
    pyproject_path = project_dir / "pyproject.toml"
    lock_path = project_dir / "uv.lock"
    for path in (pyproject_path, lock_path):
        if not path.is_file():
            sys.exit(f"error: {path} not found")

    info = project.load_project(pyproject_path)
    resources, lock_warnings = uvlock.read_resources(lock_path, info.name)
    for message in lock_warnings:
        warn(message)
    debug(f"Found {len(resources)} resources for '{info.name}'.")

    repo = project.github_repo(project_dir)
    if repo is None:
        sys.exit(
            f"error: could not determine a GitHub repository from the 'origin' "
            f"remote in {project_dir}"
        )
    owner, repo_name = repo

    tag = args.tag or project.latest_tag(project_dir)
    if tag is None:
        sys.exit(f"error: no git tag found in {project_dir}; pass one with --tag")
    debug(f"Using repository {owner}/{repo_name} at tag {tag}.")

    if args.local:
        version = tag.removeprefix("v")
        tarball_path = Path(tempfile.gettempdir()) / f"{info.name}-{version}.tar.gz"
        debug(f"Archiving tag {tag} to {tarball_path}.")
        if not project.archive_tag(
            project_dir, tag, f"{info.name}-{version}", tarball_path
        ):
            sys.exit(f"error: git archive failed for tag '{tag}' in {project_dir}")
        url = f"file://{tarball_path}"
        sha256 = tarball.sha256_of_file(tarball_path)
        warn("formula points at a local tarball; rerun without --local before publishing")
    else:
        url = f"https://github.com/{owner}/{repo_name}/archive/refs/tags/{tag}.tar.gz"
        if args.offline:
            sha256 = SHA_PLACEHOLDER
        else:
            debug(f"Downloading {url} to compute its sha256.")
            try:
                sha256 = tarball.sha256_of_url(url)
            except urllib.error.URLError as error:
                warn(f"could not download {url} ({error}); using a sha256 placeholder")
                sha256 = SHA_PLACEHOLDER

    if not info.description or info.description == project.PLACEHOLDER_DESCRIPTION:
        warn("pyproject.toml has no real description; fill in `desc` manually")
    if info.license is None:
        warn("pyproject.toml declares no license; fill in `license` manually")
    if tag.removeprefix("v") != info.version:
        warn(f"pyproject.toml version '{info.version}' does not match tag '{tag}'")

    tap = args.tap or find_tap(project_dir)
    formula_path = tap / "Formula" / f"{info.name}.rb" if tap else None

    if formula_path is not None and formula_path.is_file():
        debug(f"Updating existing formula {formula_path}.")
        text, update_warnings = formula.update_formula(
            formula_path.read_text(),
            url=url,
            sha256=sha256,
            python_dep=info.python_dep,
            resources=resources,
        )
        for message in update_warnings:
            warn(message)
        action = "Updated"
    else:
        debug("No existing formula found, generating a new one.")
        text = formula.render_formula(
            name=info.name,
            desc=info.description,
            homepage=info.homepage or f"https://github.com/{owner}/{repo_name}",
            url=url,
            sha256=sha256,
            license=info.license,
            python_dep=info.python_dep,
            resources=resources,
            script_name=info.script_name,
        )
        action = "Created"

    if args.stdout:
        print(text, end="")
    else:
        if formula_path is None or tap is None:
            sys.exit("error: no tap found; pass --tap or use --stdout")
        formula_path.write_text(text)
        print(f"{action} {formula_path}", file=sys.stderr)

    if sha256 == SHA_PLACEHOLDER:
        print(
            f"\nFill in the sha256 first:\n  curl -sL {url} | shasum -a 256",
            file=sys.stderr,
        )
    if not args.stdout and tap is not None and formula_path is not None:
        print_next_steps(tap, formula_path, info.name, tag, local=args.local)


if __name__ == "__main__":
    main()
