import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Resource:
    name: str
    url: str
    sha256: str


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# Returns the resources for the transitive closure of the root package's
# runtime dependencies, plus warnings for entries that had to be skipped.
# Dev dependency groups are not followed, so test-only packages are excluded.
def read_resources(lock_path: Path, root_name: str) -> tuple[list[Resource], list[str]]:
    with open(lock_path, "rb") as f:
        data = tomllib.load(f)

    packages = {normalize(p["name"]): p for p in data.get("package", [])}
    root = packages.get(normalize(root_name))
    if root is None:
        raise ValueError(f"Package '{root_name}' not found in {lock_path}.")

    warnings: list[str] = []
    resources: list[Resource] = []
    seen: set[str] = set()
    queue = [d["name"] for d in root.get("dependencies", [])]
    while queue:
        name = normalize(queue.pop())
        if name in seen:
            continue
        seen.add(name)
        package = packages.get(name)
        if package is None:
            warnings.append(f"dependency '{name}' not found in lock file; skipped")
            continue
        queue.extend(d["name"] for d in package.get("dependencies", []))
        sdist = package.get("sdist")
        if sdist is None:
            warnings.append(f"package '{name}' has no sdist entry; skipped")
            continue
        resources.append(
            Resource(
                name=package["name"].replace("-", "_"),
                url=sdist["url"],
                sha256=sdist["hash"].removeprefix("sha256:"),
            )
        )

    resources.sort(key=lambda r: r.name)
    return resources, warnings
