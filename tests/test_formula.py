from pythonformula.formula import (
    class_name,
    has_license,
    render_formula,
    render_license,
    update_formula,
)
from pythonformula.uvlock import Resource

RESOURCES = [
    Resource("alpha", "https://example.com/alpha-1.0.0.tar.gz", "aaa"),
    Resource("beta_lib", "https://example.com/beta_lib-2.0.0.tar.gz", "bbb"),
]

STALE_FORMULA = """\
class MyProj < Formula
  include Language::Python::Virtualenv

  desc "My hand-written description"
  homepage "https://github.com/infogrind/myproj"
  url "https://github.com/infogrind/myproj/archive/refs/tags/v0.9.tar.gz"
  sha256 "oldsha"
  license "MIT"

  depends_on "python@3.12"
  depends_on "maturin"

  resource "old_one" do
    url "https://example.com/old_one-1.0.tar.gz"
    sha256 "old1"
  end

  resource "old_two" do
    url "https://example.com/old_two-1.0.tar.gz"
    sha256 "old2"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Enter your OpenAI API key",
      shell_output("echo '123' | #{bin}/myproj 2>&1", 1)
  end
end
"""


def test_class_name():
    assert class_name("pythonformula") == "Pythonformula"
    assert class_name("gpt-epub-rename") == "GptEpubRename"


def test_render_formula():
    text = render_formula(
        name="my-proj",
        desc="A test project",
        homepage="https://github.com/infogrind/myproj",
        url="https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz",
        sha256="newsha",
        license="MIT",
        python_dep="python@3.13",
        resources=RESOURCES,
        script_name="myproj",
    )
    assert text == """\
class MyProj < Formula
  include Language::Python::Virtualenv

  desc "A test project"
  homepage "https://github.com/infogrind/myproj"
  url "https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz"
  sha256 "newsha"
  license "MIT"

  depends_on "python@3.13"

  resource "alpha" do
    url "https://example.com/alpha-1.0.0.tar.gz"
    sha256 "aaa"
  end

  resource "beta_lib" do
    url "https://example.com/beta_lib-2.0.0.tar.gz"
    sha256 "bbb"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_path_exists bin/"myproj"
  end
end
"""


def test_render_formula_without_license():
    text = render_formula(
        name="my-proj",
        desc="A test project",
        homepage="https://github.com/infogrind/myproj",
        url="https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz",
        sha256="newsha",
        license=None,
        python_dep="python@3.13",
        resources=[],
        script_name="myproj",
    )
    assert 'license' not in text
    assert 'resource "' not in text
    assert '  depends_on "python@3.13"\n\n  def install' in text


def test_update_formula():
    text, warnings = update_formula(
        STALE_FORMULA,
        url="https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz",
        sha256="newsha",
        python_dep="python@3.13",
        resources=RESOURCES,
    )
    assert text == """\
class MyProj < Formula
  include Language::Python::Virtualenv

  desc "My hand-written description"
  homepage "https://github.com/infogrind/myproj"
  url "https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz"
  sha256 "newsha"
  license "MIT"

  depends_on "python@3.13"
  depends_on "maturin"

  resource "alpha" do
    url "https://example.com/alpha-1.0.0.tar.gz"
    sha256 "aaa"
  end

  resource "beta_lib" do
    url "https://example.com/beta_lib-2.0.0.tar.gz"
    sha256 "bbb"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Enter your OpenAI API key",
      shell_output("echo '123' | #{bin}/myproj 2>&1", 1)
  end
end
"""
    assert warnings == [
        'existing depends_on "maturin" kept; remove it if no longer needed'
    ]


def test_render_license():
    assert render_license("MIT") == '"MIT"'
    assert render_license("MIT OR Apache-2.0") == 'any_of: ["MIT", "Apache-2.0"]'
    assert render_license("MIT AND ISC") == 'all_of: ["MIT", "ISC"]'


def test_render_formula_with_license_expression():
    text = render_formula(
        name="my-proj",
        desc="A test project",
        homepage="https://github.com/infogrind/myproj",
        url="https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz",
        sha256="newsha",
        license="MIT OR Apache-2.0",
        python_dep="python@3.13",
        resources=[],
        script_name="myproj",
    )
    assert '  sha256 "newsha"\n  license any_of: ["MIT", "Apache-2.0"]\n\n' in text


def _update(text, license):
    return update_formula(
        text,
        url="https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz",
        sha256="newsha",
        python_dep="python@3.13",
        resources=RESOURCES,
        license=license,
    )


UNLICENSED_FORMULA = STALE_FORMULA.replace('  license "MIT"\n', "")


def test_update_formula_adds_license_after_sha256():
    text, warnings = _update(UNLICENSED_FORMULA, "MIT")
    # Identical to updating the formula that already had the line.
    assert text == _update(STALE_FORMULA, "MIT")[0]
    assert '  sha256 "newsha"\n  license "MIT"\n\n  depends_on' in text
    assert not any("license" in w for w in warnings)


def test_update_formula_without_resources_adds_license():
    text, _ = update_formula(
        UNLICENSED_FORMULA,
        url="u",
        sha256="newsha",
        python_dep="python@3.13",
        resources=[],
        license="MIT",
    )
    assert '  sha256 "newsha"\n  license "MIT"\n' in text
    assert 'resource "' not in text


def test_update_formula_keeps_matching_license():
    text, warnings = _update(STALE_FORMULA, "MIT")
    assert text.count("license") == 1
    assert not any("license" in w for w in warnings)


def test_update_formula_keeps_license_when_none_declared():
    for formula_text in (STALE_FORMULA, STALE_FORMULA.replace('"MIT"', '"BSD-2-Clause"')):
        text, warnings = _update(formula_text, None)
        assert formula_text.split("\n")[7] in text.splitlines()
        assert not any("license" in w for w in warnings)


def test_update_formula_replaces_changed_license():
    text, warnings = _update(STALE_FORMULA, "Apache-2.0")
    assert '  license "Apache-2.0"' in text
    assert 'license "MIT"' not in text
    assert 'license changed from "MIT" to "Apache-2.0"' in warnings


def test_update_formula_keeps_multiline_license():
    multiline = STALE_FORMULA.replace(
        '  license "MIT"\n', '  license any_of: [\n    "MIT",\n    "Apache-2.0",\n  ]\n'
    )
    text, warnings = _update(multiline, "ISC")
    assert '  license any_of: [\n    "MIT",\n    "Apache-2.0",\n  ]\n' in text
    assert 'existing multi-line license kept; check it matches "ISC"' in warnings


def test_has_license():
    assert has_license(STALE_FORMULA)
    assert not has_license(UNLICENSED_FORMULA)
