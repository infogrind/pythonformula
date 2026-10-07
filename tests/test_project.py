import pytest

from pythonformula.project import load_project, resolve_license

MIT_CLASSIFIER = "License :: OSI Approved :: MIT License"


@pytest.mark.parametrize(
    "license_value, expected",
    [
        ("MIT", "MIT"),
        ("Apache-2.0", "Apache-2.0"),
        ("MIT OR Apache-2.0", "MIT OR Apache-2.0"),
        ("GPL-3.0-or-later AND MIT", "GPL-3.0-or-later AND MIT"),
        ({"text": "MIT"}, "MIT"),
        ({"text": " mit "}, "MIT"),
        ({"text": "bsd-3-clause OR mit"}, "BSD-3-Clause OR MIT"),
    ],
)
def test_clear_license(license_value, expected):
    assert resolve_license({"license": license_value}) == (expected, None)


@pytest.mark.parametrize(
    "expression",
    [
        "MIT OR Apache-2.0 AND BSD-3-Clause",
        "(MIT OR Apache-2.0)",
        "GPL-2.0-or-later WITH Classpath-exception-2.0",
        "LicenseRef-Proprietary",
        "",
    ],
)
def test_unsupported_spdx_expression_warns(expression):
    # PEP 639: a license expression rules out falling back to classifiers.
    license, warning = resolve_license(
        {"license": expression, "classifiers": [MIT_CLASSIFIER]}
    )
    assert license is None
    assert "cannot be written automatically" in warning


def test_license_file_warns_instead_of_guessing():
    license, warning = resolve_license({"license": {"file": "LICENSE"}})
    assert license is None
    assert warning == (
        "license is only given as a file (LICENSE); fill in `license` manually"
    )


def test_unrecognized_license_text_warns():
    license, warning = resolve_license(
        {"license": {"text": "Permission is hereby granted, free of charge..."}}
    )
    assert license is None
    assert "not a recognized SPDX identifier" in warning


def test_no_license_warns():
    assert resolve_license({}) == (
        None,
        "pyproject.toml declares no license; fill in `license` manually",
    )


@pytest.mark.parametrize(
    "project",
    [
        {"classifiers": [MIT_CLASSIFIER]},
        {"license": {"file": "LICENSE"}, "classifiers": [MIT_CLASSIFIER]},
        {"license": {"text": "see LICENSE"}, "classifiers": [MIT_CLASSIFIER]},
    ],
)
def test_classifier_fallback(project):
    project["classifiers"] = ["Programming Language :: Python", *project["classifiers"]]
    assert resolve_license(project) == ("MIT", None)


def test_ambiguous_classifier_warns():
    license, warning = resolve_license(
        {"classifiers": ["License :: OSI Approved :: BSD License"]}
    )
    assert license is None
    assert (
        "'License :: OSI Approved :: BSD License' names no specific SPDX license"
        in warning
    )


def test_multiple_classifiers_warn():
    license, warning = resolve_license(
        {
            "classifiers": [
                MIT_CLASSIFIER,
                "License :: OSI Approved :: ISC License (ISCL)",
            ]
        }
    )
    assert license is None
    assert "2 license classifiers leave it ambiguous" in warning


def test_load_project_license(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "p"\nlicense = { text = "MIT" }\n')
    info = load_project(path)
    assert (info.license, info.license_warning) == ("MIT", None)
