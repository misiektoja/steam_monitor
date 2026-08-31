"""Tests that the documentation describes what the tool actually does, so stale claims fail here."""

import re
from pathlib import Path

import pytest

import steam_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
RELEASE_NOTES = REPO_ROOT / "RELEASE_NOTES.md"


# Returns the anchors the README defines, both from headings and from explicit anchor tags
def readme_anchors():
    text = README.read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a id="([^"]+)"></a>', text))
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        title = line.lstrip("#").strip()
        anchors.add("".join(character for character in title.casefold().replace(" ", "-") if character.isalnum() or character in "-_"))
    return anchors


# Returns every command-line flag the parser accepts
def declared_flags():
    source = (REPO_ROOT / "steam_monitor.py").read_text(encoding="utf-8")
    declaration_lines = re.findall(r'^\s*(?:"-[a-zA-Z]",\s*)?"--[a-z0-9-]+",\s*$', source, flags=re.MULTILINE)
    return {flag for line in declaration_lines for flag in re.findall(r'"(--[a-z0-9-]+)"', line)}


# Verifies every guide constant points at an anchor the README really defines
def test_every_guide_link_resolves():
    anchors = readme_anchors()

    for name in sorted(name for name in vars(monitor) if name.endswith("_GUIDE_URL")):
        url = getattr(monitor, name)
        assert url.startswith(monitor.DOCS_BASE_URL), name
        if "#" in url:
            assert url.rsplit("#", 1)[1] in anchors, f"{name} points at a missing anchor"


# Verifies every table-of-contents link resolves, so a renamed section fails here rather than in front of a reader
def test_every_table_of_contents_link_resolves():
    text = README.read_text(encoding="utf-8")
    anchors = readme_anchors()

    missing = [target for target in re.findall(r"\]\(#([^)]+)\)", text) if target not in anchors]

    assert not missing, f"README links to missing anchors: {missing}"


# Verifies each user-facing command is documented, since an undocumented one may as well not exist
@pytest.mark.parametrize("flag", ["--setup", "--doctor", "--verbose", "--debug", "--generate-config", "--set-steam-api-key", "--set-webhook-url", "--send-test-email", "--send-test-webhook", "--env-file", "--config-file"])
def test_user_facing_flags_are_documented(flag):
    assert flag in README.read_text(encoding="utf-8"), f"{flag} is not mentioned in the README"


# Verifies the flags the README shows all actually exist, so a removed one cannot linger in the docs
def test_the_readme_does_not_promise_removed_flags():
    documented = set(re.findall(r"`(--[a-z0-9-]+)`", README.read_text(encoding="utf-8")))
    accepted = declared_flags()
    # Flags belonging to other tools or to pip are quoted in passing and are not this parser's to accept
    external = {"--version", "--help", "--upgrade", "--user", "--break-system-packages"}

    missing = sorted(flag for flag in documented - accepted - external if flag not in ("--no-color",))

    assert not missing, f"the README documents flags the tool does not accept: {missing}"


# Verifies every setting the wizard writes is one the parser will accept back
def test_every_wizard_setting_is_a_real_setting():
    allowed = monitor._config_allowed_names()

    for _name, config_keys, _secret_keys in monitor.WIZARD_SECTIONS:
        for key in config_keys:
            assert key in allowed, f"the wizard writes {key}, which is not a configuration setting"


# Verifies every secret the wizard collects is one the dotenv writer will accept
def test_every_wizard_secret_is_a_real_secret():
    for _name, _config_keys, secret_keys in monitor.WIZARD_SECTIONS:
        for key in secret_keys:
            assert key in monitor.SECRET_KEYS, f"the wizard collects {key}, which is not a known secret"


# Verifies the documented status markers are the ones the doctor actually prints
def test_the_documented_doctor_markers_match_the_code():
    text = README.read_text(encoding="utf-8")

    for marker in ("[PASS]", "[WARN]", "[FAIL]", "[SKIP]"):
        assert f"`{marker}`" in text, f"{marker} is not documented"
    # A fifth marker in the docs would mean the page and the code disagree
    assert "[ -- ]" not in text


# Verifies the documented doctor sections are exactly the ones the report renders
def test_the_documented_doctor_sections_match_the_code():
    text = README.read_text(encoding="utf-8")

    for section in monitor.DOCTOR_SECTIONS:
        assert f"**{section}**" in text, f"the {section} doctor section is not documented"


# Verifies the release notes lead with the version the module declares
def test_the_release_notes_lead_with_the_declared_version():
    first_heading = next(line for line in RELEASE_NOTES.read_text(encoding="utf-8").splitlines() if line.startswith("# Changes in "))

    assert first_heading.startswith(f"# Changes in {monitor.VERSION} "), first_heading


# Verifies the documented Python minimum matches the one constant the code holds
def test_the_documented_python_minimum_matches_the_code():
    text = README.read_text(encoding="utf-8")

    assert f"Python {monitor.MINIMUM_PYTHON_VERSION_TEXT}" in text, "the README states a different Python minimum"


# Verifies every configuration setting the README names in backticks is one the parser accepts
def test_the_readme_does_not_promise_removed_settings():
    documented = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", README.read_text(encoding="utf-8")))
    allowed = set(monitor._config_allowed_names()) | set(monitor.SECRET_KEYS)
    # Signal names, environment variables, file names and prose emphasis are not configuration settings
    external = {"STEAM64_ID", "PATH", "HOME", "TERM", "NO_COLOR", "SHA256SUMS", "README", "SUPPORT", "SECURITY", "CONTRIBUTING", "LICENSE", "IMPORTANT", "NOTE", "GRC", "SIGHUP"}

    missing = sorted(documented - allowed - external)

    assert not missing, f"the README documents settings the tool does not accept: {missing}"
