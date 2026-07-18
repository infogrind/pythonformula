import re

from pythonformula.uvlock import Resource

_RESOURCE_START = re.compile(r'^(\s*)resource "[^"]+" do\s*$')
_URL_LINE = re.compile(r'^(\s*)url "[^"]*"$')
_SHA_LINE = re.compile(r'^(\s*)sha256 "[^"]*"$')
_PYTHON_DEP = re.compile(r'^(\s*)depends_on "python@[\d.]+"$')
_OTHER_DEP = re.compile(r'^\s*depends_on "([^"]+)"$')


def class_name(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[-_.]", name))


def render_resources(resources: list[Resource]) -> str:
    return "\n\n".join(
        f'''  resource "{r.name}" do
    url "{r.url}"
    sha256 "{r.sha256}"
  end'''
        for r in resources
    )


def render_formula(
    *,
    name: str,
    desc: str,
    homepage: str,
    url: str,
    sha256: str,
    license: str | None,
    python_dep: str,
    resources: list[Resource],
    script_name: str,
) -> str:
    license_line = f'\n  license "{license}"' if license else ""
    resource_section = f"\n{render_resources(resources)}\n" if resources else ""
    return f'''class {class_name(name)} < Formula
  include Language::Python::Virtualenv

  desc "{desc}"
  homepage "{homepage}"
  url "{url}"
  sha256 "{sha256}"{license_line}

  depends_on "{python_dep}"
{resource_section}
  def install
    virtualenv_install_with_resources
  end

  test do
    assert_path_exists bin/"{script_name}"
  end
end
'''


# Surgically updates an existing formula: replaces the top-level url and
# sha256, the python depends_on, and all resource blocks, while leaving
# everything else (desc, homepage, license, test block, ...) untouched.
def update_formula(
    text: str,
    *,
    url: str,
    sha256: str,
    python_dep: str,
    resources: list[Resource],
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    lines = text.splitlines()
    kept: list[str] = []
    insert_at: int | None = None
    replaced_url = replaced_sha = False

    i = 0
    while i < len(lines):
        line = lines[i]
        match = _RESOURCE_START.match(line)
        if match:
            # Drop the whole resource block plus one trailing blank line; the
            # new blocks are inserted where the first old one started.
            if insert_at is None:
                insert_at = len(kept)
            end_line = f"{match.group(1)}end"
            while i < len(lines) and lines[i] != end_line:
                i += 1
            i += 1
            if i < len(lines) and not lines[i].strip():
                i += 1
            continue
        match = _URL_LINE.match(line)
        if match and not replaced_url:
            kept.append(f'{match.group(1)}url "{url}"')
            replaced_url = True
            i += 1
            continue
        match = _SHA_LINE.match(line)
        if match and replaced_url and not replaced_sha:
            kept.append(f'{match.group(1)}sha256 "{sha256}"')
            replaced_sha = True
            i += 1
            continue
        match = _PYTHON_DEP.match(line)
        if match:
            kept.append(f'{match.group(1)}depends_on "{python_dep}"')
            i += 1
            continue
        match = _OTHER_DEP.match(line)
        if match:
            warnings.append(
                f'existing depends_on "{match.group(1)}" kept; remove it if no longer needed'
            )
        kept.append(line)
        i += 1

    if not replaced_url:
        warnings.append("no url line found in existing formula; url not updated")
    if not replaced_sha:
        warnings.append("no sha256 line found in existing formula; sha256 not updated")

    if resources:
        block_lines = render_resources(resources).splitlines()
        block_lines.append("")
        if insert_at is None:
            insert_at = next(
                (n for n, l in enumerate(kept) if l.lstrip().startswith("def install")),
                len(kept),
            )
        kept[insert_at:insert_at] = block_lines

    return "\n".join(kept) + "\n", warnings
