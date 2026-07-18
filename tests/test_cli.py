import sys
from pathlib import Path

import pytest

from pythonformula import cli, project
from tests.test_uvlock import LOCKFILE

PYPROJECT = """\
[project]
name = "myproj"
version = "1.0"
description = "A test project"
license = "MIT"
requires-python = ">=3.13"
dependencies = ["alpha>=1.0"]

[project.scripts]
myproj = "myproj:main"
"""


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    directory = tmp_path / "myproj"
    directory.mkdir()
    (directory / "pyproject.toml").write_text(PYPROJECT)
    (directory / "uv.lock").write_text(LOCKFILE)
    monkeypatch.setattr(project, "latest_tag", lambda d: "v1.0")
    monkeypatch.setattr(
        project,
        "github_repo",
        lambda d: ("infogrind", "myproj") if Path(d) == directory else None,
    )
    return directory


def run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["pythonformula", *args])
    cli.main()


def test_generate_to_stdout(project_dir, monkeypatch, capsys):
    run_cli(monkeypatch, str(project_dir), "--stdout", "--offline")
    captured = capsys.readouterr()
    assert captured.out == """\
class Myproj < Formula
  include Language::Python::Virtualenv

  desc "A test project"
  homepage "https://github.com/infogrind/myproj"
  url "https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz"
  sha256 "PLACEHOLDER"
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
    assert "gamma" in captured.err  # no-sdist warning
    assert "curl -sL" in captured.err  # placeholder instructions


def test_update_in_tap(project_dir, tmp_path, monkeypatch, capsys):
    tap = tmp_path / "homebrew-tap"
    (tap / "Formula").mkdir(parents=True)
    formula_path = tap / "Formula" / "myproj.rb"
    formula_path.write_text("""\
class Myproj < Formula
  include Language::Python::Virtualenv

  desc "My hand-written description"
  homepage "https://github.com/infogrind/myproj"
  url "https://github.com/infogrind/myproj/archive/refs/tags/v0.9.tar.gz"
  sha256 "oldsha"
  license "MIT"

  depends_on "python@3.13"

  resource "old_one" do
    url "https://example.com/old_one-1.0.tar.gz"
    sha256 "old1"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_path_exists bin/"myproj"
  end
end
""")

    run_cli(monkeypatch, str(project_dir), "--tap", str(tap), "--offline")
    captured = capsys.readouterr()

    text = formula_path.read_text()
    assert 'desc "My hand-written description"' in text
    assert 'url "https://github.com/infogrind/myproj/archive/refs/tags/v1.0.tar.gz"' in text
    assert 'sha256 "PLACEHOLDER"' in text
    assert "old_one" not in text
    assert 'resource "alpha"' in text
    assert 'resource "beta_lib"' in text

    assert f"Updated {formula_path}" in captured.err
    assert "Next steps:" in captured.err
    assert "brew audit --strict <owner>/<tap>/myproj" in captured.err
    assert "brew install --build-from-source <owner>/<tap>/myproj" in captured.err


def test_next_steps_use_tap_name(project_dir, tmp_path, monkeypatch, capsys):
    tap = tmp_path / "homebrew-tap"
    (tap / "Formula").mkdir(parents=True)
    monkeypatch.setattr(project, "tap_name", lambda d: "infogrind/tap")

    run_cli(monkeypatch, str(project_dir), "--tap", str(tap), "--offline")
    captured = capsys.readouterr()

    assert "brew install --build-from-source infogrind/tap/myproj" in captured.err
    assert 'cp' in captured.err and '"$(brew --repository infogrind/tap)"/Formula/' in captured.err


def test_no_staging_steps_when_tap_is_brew_clone(project_dir, tmp_path, monkeypatch, capsys):
    tap = tmp_path / "Library" / "Taps" / "infogrind" / "homebrew-tap"
    (tap / "Formula").mkdir(parents=True)
    monkeypatch.setattr(project, "tap_name", lambda d: "infogrind/tap")

    run_cli(monkeypatch, str(project_dir), "--tap", str(tap), "--offline")
    captured = capsys.readouterr()

    assert "brew install --build-from-source infogrind/tap/myproj" in captured.err
    assert "Stage:" not in captured.err
    assert "Clean:" not in captured.err


def test_tap_auto_detection_next_to_project(project_dir, tmp_path, monkeypatch, capsys):
    tap = tmp_path / "homebrew-tap"
    (tap / "Formula").mkdir(parents=True)

    run_cli(monkeypatch, str(project_dir), "--offline")
    captured = capsys.readouterr()

    formula_path = tap / "Formula" / "myproj.rb"
    assert formula_path.is_file()
    assert f"Created {formula_path}" in captured.err


def test_version_mismatch_warning(project_dir, monkeypatch, capsys):
    run_cli(monkeypatch, str(project_dir), "--stdout", "--offline", "--tag", "v2.0")
    captured = capsys.readouterr()
    assert "does not match tag 'v2.0'" in captured.err


def test_missing_project_dir(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="pyproject.toml not found"):
        run_cli(monkeypatch, str(tmp_path / "nonexistent"), "--stdout", "--offline")
