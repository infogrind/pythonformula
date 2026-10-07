import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_DESCRIPTION = "Add your description here"

# SPDX identifiers accepted from the free-form `license = { text = ... }`
# table, keyed by lowercase for case-insensitive matching. The text field can
# hold anything (even a whole license text), so only known identifiers count.
_KNOWN_SPDX = {
    spdx.lower(): spdx
    for spdx in (
        "0BSD", "AGPL-3.0-only", "AGPL-3.0-or-later", "Apache-2.0",
        "Artistic-2.0", "BSD-2-Clause", "BSD-3-Clause", "BSL-1.0", "CC0-1.0",
        "EPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only",
        "GPL-3.0-or-later", "ISC", "LGPL-2.1-only", "LGPL-2.1-or-later",
        "LGPL-3.0-only", "LGPL-3.0-or-later", "MIT", "MIT-0", "MPL-2.0",
        "PSF-2.0", "Unlicense", "WTFPL", "Zlib",
    )
}  # fmt: skip

# Trove classifiers that name exactly one SPDX license. Classifiers such as
# "BSD License" or "GNU General Public License v3 (GPLv3)" are deliberately
# absent: they leave the clause count or the "-only"/"-or-later" choice open.
_CLASSIFIER_SPDX = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: MIT No Attribution License (MIT-0)": "MIT-0",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
    "License :: OSI Approved :: Boost Software License 1.0 (BSL-1.0)": "BSL-1.0",
    "License :: OSI Approved :: Eclipse Public License 2.0 (EPL-2.0)": "EPL-2.0",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)": "GPL-2.0-or-later",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)": "GPL-3.0-or-later",
    "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)": "LGPL-3.0-or-later",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)": "AGPL-3.0-or-later",
    "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication": "CC0-1.0",
}

_SPDX_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")


@dataclass
class ProjectInfo:
    name: str
    version: str
    description: str
    license: str | None
    license_warning: str | None
    homepage: str | None
    python_dep: str
    script_name: str


def load_project(pyproject_path: Path) -> ProjectInfo:
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project")
    if project is None or "name" not in project:
        raise ValueError(f"No [project] table with a name in {pyproject_path}.")
    name = project["name"]

    license_value, license_warning = resolve_license(project)

    urls = project.get("urls", {})
    homepage = next((urls[k] for k in urls if k.lower() == "homepage"), None)

    match = re.search(r"3\.\d+", project.get("requires-python", ""))
    python_dep = f"python@{match.group(0)}" if match else "python@3.13"

    scripts = project.get("scripts", {})
    script_name = next(iter(scripts), name)

    return ProjectInfo(
        name=name,
        version=project.get("version", ""),
        description=project.get("description", ""),
        license=license_value,
        license_warning=license_warning,
        homepage=homepage,
        python_dep=python_dep,
        script_name=script_name,
    )


# Splits an SPDX expression into its identifiers and the single operator
# joining them ("OR"/"AND"; None for a lone identifier). Returns None for
# anything Homebrew's `license` DSL can't express as a flat list: mixed
# operators, parentheses, WITH exceptions, or LicenseRef- identifiers.
def split_spdx(expression: str) -> tuple[list[str], str | None] | None:
    tokens = expression.split()
    ids, operators = tokens[::2], set(tokens[1::2])
    if not ids or len(tokens) % 2 == 0 or len(operators) > 1:
        return None
    if not operators <= {"OR", "AND"}:
        return None
    if not all(_SPDX_ID.fullmatch(i) and not i.startswith("LicenseRef-") for i in ids):
        return None
    return ids, operators.pop() if operators else None


def _known_spdx(text: str) -> str | None:
    parts = split_spdx(text.strip())
    if parts is None:
        return None
    ids, operator = parts
    if not all(i.lower() in _KNOWN_SPDX for i in ids):
        return None
    return f" {operator} ".join(_KNOWN_SPDX[i.lower()] for i in ids)


# Determines the SPDX license expression to write into the formula, from the
# PEP 639 `license` string, the older `license = { text/file }` table, or, as
# a fallback, "License ::" classifiers. Returns (expression, None) when the
# license is clear, or (None, warning) when it has to be filled in by hand.
def resolve_license(project: dict) -> tuple[str | None, str | None]:
    value = project.get("license")
    if isinstance(value, str):
        # PEP 639: an expression rules out classifier fallback.
        if split_spdx(value) is None:
            return None, (
                f"license expression '{value}' cannot be written automatically; "
                "fill in `license` manually"
            )
        return " ".join(value.split()), None

    if isinstance(value, dict) and "text" in value:
        spdx = _known_spdx(value["text"])
        if spdx is not None:
            return spdx, None
        reason = "license text is not a recognized SPDX identifier"
    elif isinstance(value, dict) and "file" in value:
        reason = f"license is only given as a file ({value['file']})"
    else:
        reason = "pyproject.toml declares no license"

    classifiers = [
        c for c in project.get("classifiers", []) if c.startswith("License ::")
    ]
    mapped = {_CLASSIFIER_SPDX.get(c) for c in classifiers}
    if len(classifiers) == 1 and None not in mapped:
        return mapped.pop(), None
    if len(classifiers) > 1:
        reason += f" and {len(classifiers)} license classifiers leave it ambiguous"
    elif classifiers:
        reason += f" and classifier '{classifiers[0]}' names no specific SPDX license"
    return None, f"{reason}; fill in `license` manually"


def _git(project_dir: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def latest_tag(project_dir: Path) -> str | None:
    return _git(project_dir, "describe", "--tags", "--abbrev=0")


def github_repo(project_dir: Path) -> tuple[str, str] | None:
    url = _git(project_dir, "remote", "get-url", "origin")
    if not url:
        return None
    match = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not match:
        return None
    return match.group(1), match.group(2)


# Creates a gzipped tarball of the given tag, laid out like a GitHub archive
# (single top-level directory named `prefix`). Returns False on failure.
def archive_tag(project_dir: Path, tag: str, prefix: str, output: Path) -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(project_dir),
            "archive",
            "--format=tar.gz",
            f"--prefix={prefix}/",
            "-o",
            str(output),
            tag,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


# Returns the short tap name brew uses (e.g. "infogrind/tap" for a clone of
# github.com/infogrind/homebrew-tap), or None if it cannot be determined.
def tap_name(tap_dir: Path) -> str | None:
    repo = github_repo(tap_dir)
    if repo is None:
        return None
    owner, name = repo
    return f"{owner}/{name.removeprefix('homebrew-')}"
