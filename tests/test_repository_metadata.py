"""Tests for repository metadata: governance files, citation, funding, whitespace rules and release integrity."""

import configparser
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Reads one repository asset as UTF-8
def read_asset(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Reads and parses one repository YAML asset
def read_yaml_asset(relative_path: str):
    return yaml.safe_load(read_asset(relative_path))


# Verifies the documents contributors are pointed to are present and not placeholders
def test_repository_governance_documents_exist():
    for relative_path in ("SUPPORT.md", "LICENSE", "README.md", "RELEASE_NOTES.md"):
        asset = PROJECT_ROOT / relative_path
        assert asset.is_file(), relative_path
        assert asset.stat().st_size > 200, relative_path


# Verifies the citation metadata GitHub renders stays parseable and describes this project
def test_citation_metadata_describes_this_project():
    citation = read_yaml_asset("CITATION.cff")
    assert citation["cff-version"] == "1.2.0"
    assert citation["type"] == "software"
    assert citation["title"] == "steam_monitor"
    assert citation["message"]
    assert citation["license"] == "GPL-3.0-or-later"
    assert citation["repository-code"] == "https://github.com/misiektoja/steam_monitor"
    assert citation["date-released"].isoformat() == str(citation["date-released"])

    author = citation["authors"][0]
    assert author["given-names"] and author["family-names"] and author["alias"] == "misiektoja"


# Verifies the citation names a version somebody can cite, so it tracks the newest dated release notes section
def test_citation_tracks_the_newest_released_version():
    released = re.search(r"^# Changes in ([\d.]+) \((\d{1,2} \w{3} \d{4})\)", read_asset("RELEASE_NOTES.md"), re.M)
    citation = read_asset("CITATION.cff")
    cited_version = re.search(r'^version: "([^"]+)"', citation, re.M)
    cited_date = re.search(r"^date-released: (\d{4}-\d{2}-\d{2})", citation, re.M)

    assert released is not None and cited_version is not None and cited_date is not None
    assert cited_version.group(1) == released.group(1)
    assert cited_date.group(1) == datetime.strptime(released.group(2), "%d %b %Y").strftime("%Y-%m-%d")


# Verifies the sponsor button keeps a target, since an empty file hides it without failing any check
def test_funding_configuration_declares_a_sponsor_target():
    funding = read_yaml_asset(".github/FUNDING.yml")
    assert funding["github"] == "misiektoja"
    assert funding["buy_me_a_coffee"] == "misiektoja"


# Verifies the shared editor settings still declare the style the repository is written in
def test_editor_configuration_declares_the_repository_style():
    settings = configparser.ConfigParser()
    settings.read_string("[editorconfig]\n" + read_asset(".editorconfig"))

    assert settings["editorconfig"]["root"] == "true"
    assert settings["*"]["charset"] == "utf-8"
    assert settings["*"]["end_of_line"] == "lf"
    assert settings["*"]["indent_style"] == "space"
    assert settings["*"]["indent_size"] == "4"
    assert settings["*"]["insert_final_newline"] == "true"
    assert settings["*"]["trim_trailing_whitespace"] == "true"
    assert settings["*.py"]["indent_size"] == "4"
    assert settings["*.{yml,yaml}"]["indent_size"] == "2"
    assert settings["*.toml"]["indent_size"] == "2"
    # Two trailing spaces are a Markdown line break, so they must stay exempt from trimming
    assert settings["*.md"]["trim_trailing_whitespace"] == "false"


# Verifies tracked text files obey those rules, since an editor setting only warns on the machine that has it
def test_tracked_text_files_obey_the_declared_whitespace_rules():
    listing = subprocess.run(["git", "ls-files"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    if listing.returncode != 0:
        pytest.skip("not a git checkout")

    offenders = []
    for name in listing.stdout.split():
        asset = PROJECT_ROOT / name
        if not asset.is_file() or asset.suffix.casefold() in {".png", ".jpg", ".gif"}:
            continue
        content = asset.read_bytes()
        if b"\r\n" in content:
            offenders.append(f"{name}: CRLF line ending")
        if content and not content.endswith(b"\n"):
            offenders.append(f"{name}: missing final newline")
        # LICENSE is verbatim upstream text and Markdown keeps meaningful trailing spaces
        if name != "LICENSE" and asset.suffix.casefold() != ".md" and re.search(rb"[ \t]+\n", content):
            offenders.append(f"{name}: trailing whitespace")
    assert offenders == []


# Verifies Git normalizes line endings, since one CRLF commit from a Windows contributor rewrites whole files
def test_line_ending_policy_is_declared():
    attributes = read_asset(".gitattributes")
    assert "* text=auto eol=lf" in attributes
    for pattern in ("*.png binary", "*.jpg binary", "*.gif binary"):
        assert pattern in attributes


# Verifies the support document routes each request to a channel that exists
def test_support_document_routes_every_request_type():
    support = read_asset("SUPPORT.md")
    for destination in ("https://github.com/misiektoja/steam_monitor/discussions", "https://github.com/misiektoja/steam_monitor/security/advisories/new", "https://github.com/misiektoja/steam_monitor/issues/new"):
        assert destination in support
    assert "steam_monitor --version" in support
    for concept in ("Steam Web API key", "SMTP passwords", "webhook URLs",):
        assert concept in support


# Verifies the optional local hooks run the same linter version CI installs, or a clean commit still fails CI
def test_local_hooks_match_the_pinned_linter():
    pinned = re.search(r'lint = \["ruff==([^"]+)"\]', read_asset("pyproject.toml"))
    assert pinned is not None

    hooks = read_yaml_asset(".pre-commit-config.yaml")["repos"]
    ruff_hook = next(entry for entry in hooks if "ruff-pre-commit" in entry["repo"])
    assert ruff_hook["rev"] == f"v{pinned.group(1)}"

    lint_steps = read_yaml_asset(".github/workflows/tests.yml")["jobs"]["lint"]["steps"]
    assert any("ruff check" in step.get("run", "") for step in lint_steps)


# Verifies published archives stay verifiable, since an unsigned download cannot be told apart from a tampered one
def test_release_archives_ship_checksums_and_provenance():
    job = read_yaml_asset(".github/workflows/release-assets.yml")["jobs"]["build-and-upload-assets"]
    assert job["permissions"]["attestations"] == "write"
    assert job["permissions"]["id-token"] == "write"

    assert any("sha256sum" in step.get("run", "") for step in job["steps"])
    assert any("attest-build-provenance" in step.get("uses", "") for step in job["steps"])

    upload = next(step for step in job["steps"] if "action-gh-release" in step.get("uses", ""))
    assert "_SHA256SUMS.txt" in upload["with"]["files"]
