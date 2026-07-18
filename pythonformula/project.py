import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_DESCRIPTION = "Add your description here"


@dataclass
class ProjectInfo:
    name: str
    version: str
    description: str
    license: str | None
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

    license_value = project.get("license")
    if isinstance(license_value, dict):
        license_value = license_value.get("text")

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
        homepage=homepage,
        python_dep=python_dep,
        script_name=script_name,
    )


def _git(project_dir: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            text=True,
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
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not match:
        return None
    return match.group(1), match.group(2)
