from pythonformula.formula import (
    class_name,
    render_formula,
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
