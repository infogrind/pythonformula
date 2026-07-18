from pythonformula.uvlock import Resource, read_resources

LOCKFILE = """\
version = 1
revision = 1
requires-python = ">=3.13"

[[package]]
name = "myproj"
version = "1.0"
source = { virtual = "." }
dependencies = [
    { name = "alpha" },
    { name = "gamma" },
]

[package.dev-dependencies]
dev = [
    { name = "pytest" },
]

[[package]]
name = "alpha"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "beta-lib" },
]
sdist = { url = "https://example.com/alpha-1.0.0.tar.gz", hash = "sha256:aaa", size = 1 }

[[package]]
name = "beta-lib"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://example.com/beta_lib-2.0.0.tar.gz", hash = "sha256:bbb", size = 1 }

[[package]]
name = "gamma"
version = "3.0.0"
source = { registry = "https://pypi.org/simple" }
wheels = [
    { url = "https://example.com/gamma-3.0.0-py3-none-any.whl", hash = "sha256:ccc", size = 1 },
]

[[package]]
name = "pytest"
version = "8.3.5"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://example.com/pytest-8.3.5.tar.gz", hash = "sha256:ddd", size = 1 }
"""


def write_lock(tmp_path):
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text(LOCKFILE)
    return lock_path


def test_runtime_closure_excludes_dev_dependencies(tmp_path):
    resources, _ = read_resources(write_lock(tmp_path), "myproj")
    assert resources == [
        Resource("alpha", "https://example.com/alpha-1.0.0.tar.gz", "aaa"),
        Resource("beta_lib", "https://example.com/beta_lib-2.0.0.tar.gz", "bbb"),
    ]


def test_missing_sdist_is_warned_and_skipped(tmp_path):
    resources, warnings = read_resources(write_lock(tmp_path), "myproj")
    assert not any(r.name == "gamma" for r in resources)
    assert warnings == ["package 'gamma' has no sdist entry; skipped"]


def test_root_name_is_normalized(tmp_path):
    resources, _ = read_resources(write_lock(tmp_path), "MyProj")
    assert len(resources) == 2
