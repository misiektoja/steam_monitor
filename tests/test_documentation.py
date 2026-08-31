"""Tests that the documentation site describes what the tool actually does, so stale claims fail here."""

import re
from pathlib import Path

import pytest

import steam_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
README = REPO_ROOT / "README.md"
RELEASE_NOTES = REPO_ROOT / "RELEASE_NOTES.md"
MKDOCS = REPO_ROOT / "mkdocs.yml"


# Returns the text of every documentation page joined together
def all_docs_text():
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(DOCS_DIR.glob("*.md")))


# Returns the anchors one documentation page defines, from headings and from explicit anchor tags
def page_anchors(path):
    text = path.read_text(encoding="utf-8")
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


# Verifies every guide constant resolves to a page that exists, and to an anchor that page defines
def test_every_guide_link_resolves_to_a_real_page_and_anchor():
    base = monitor.DOCS_BASE_URL

    for name in sorted(name for name in vars(monitor) if name.endswith("_GUIDE_URL")) + ["GUIDE_URL"]:
        url = getattr(monitor, name)
        assert url.startswith(base), f"{name} does not point at the documentation site"
        remainder = url[len(base):].lstrip("/")
        path_part, _, anchor = remainder.partition("#")
        slug = path_part.strip("/")
        page = DOCS_DIR / "index.md" if not slug else DOCS_DIR / f"{slug}.md"
        assert page.exists(), f"{name} points at a missing page: {page.name}"
        if anchor:
            assert anchor in page_anchors(page), f"{name} points at a missing anchor on {page.name}: #{anchor}"


# Verifies every page the navigation lists exists, so a renamed file fails here rather than in the built site
def test_every_navigation_entry_exists():
    navigation = MKDOCS.read_text(encoding="utf-8").split("nav:", 1)[1]

    for filename in re.findall(r":\s*([a-z0-9-]+\.md)\s*$", navigation, flags=re.MULTILINE):
        assert (DOCS_DIR / filename).exists(), f"the navigation lists a missing page: {filename}"


# Verifies every page on disk is reachable from the navigation, so a new page cannot be orphaned
def test_every_page_is_reachable_from_the_navigation():
    navigation = MKDOCS.read_text(encoding="utf-8").split("nav:", 1)[1]
    listed = set(re.findall(r":\s*([a-z0-9-]+\.md)\s*$", navigation, flags=re.MULTILINE))

    orphans = sorted(path.name for path in DOCS_DIR.glob("*.md") if path.name not in listed)

    assert not orphans, f"pages not listed in the navigation: {orphans}"


# Verifies every internal documentation link points at a page and anchor that exist
def test_every_internal_documentation_link_resolves():
    broken = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?:)([^)]+)\)", text):
            page_part, _, anchor = target.partition("#")
            target_page = path if not page_part else (DOCS_DIR / page_part)
            if page_part and not target_page.exists():
                broken.append(f"{path.name} -> {target}")
                continue
            if anchor and anchor not in page_anchors(target_page):
                broken.append(f"{path.name} -> {target}")

    assert not broken, f"broken documentation links: {broken}"


# Verifies the README landing page links only at pages the site really publishes
def test_the_readme_links_resolve():
    text = README.read_text(encoding="utf-8")
    base = monitor.DOCS_BASE_URL
    broken = []

    for url in re.findall(rf"{re.escape(base)}([^\s)]*)", text):
        slug = url.split("#")[0].strip("/")
        page = DOCS_DIR / "index.md" if not slug else DOCS_DIR / f"{slug}.md"
        if not page.exists():
            broken.append(url or "/")

    assert not broken, f"the README links at missing documentation pages: {broken}"


# Verifies each user-facing command is documented, since an undocumented one may as well not exist
@pytest.mark.parametrize("flag", ["--setup", "--doctor", "--verbose", "--debug", "--generate-config", "--set-steam-api-key", "--set-webhook-url", "--send-test-email", "--send-test-webhook", "--env-file", "--config-file"])
def test_user_facing_flags_are_documented(flag):
    assert flag in all_docs_text(), f"{flag} is not documented on the site"


# Verifies the flags the documentation shows all actually exist, so a removed one cannot linger
def test_the_documentation_does_not_promise_removed_flags():
    documented = set(re.findall(r"`(--[a-z0-9-]+)`", all_docs_text()))
    accepted = declared_flags()
    # Flags belonging to pip or to another tool are quoted in passing and are not this parser's to accept
    external = {"--version", "--help", "--upgrade", "--user", "--break-system-packages", "--no-color", "--strict", "--force"}

    missing = sorted(documented - accepted - external)

    assert not missing, f"the documentation promises flags the tool does not accept: {missing}"


# Verifies every configuration setting the documentation names is one the parser accepts
def test_the_documentation_does_not_promise_removed_settings():
    documented = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", all_docs_text()))
    allowed = set(monitor._config_allowed_names()) | set(monitor.SECRET_KEYS)
    # Signal names, environment variables, file names and prose emphasis are not configuration settings
    external = {"STEAM64_ID", "PATH", "HOME", "TERM", "NO_COLOR", "SHA256SUMS", "README", "SUPPORT", "SECURITY", "CONTRIBUTING", "LICENSE", "IMPORTANT", "NOTE", "GRC", "SIGHUP"}

    missing = sorted(documented - allowed - external)

    assert not missing, f"the documentation promises settings the tool does not accept: {missing}"


# Verifies every setting the wizard writes is one the parser will accept back
def test_every_wizard_setting_is_a_real_setting():
    allowed = monitor._config_allowed_names()

    for _name, _label, _description, config_keys, _secret_keys in monitor.WIZARD_SECTIONS:
        for key in config_keys:
            assert key in allowed, f"the wizard writes {key}, which is not a configuration setting"


# Verifies every secret the wizard collects is one the dotenv writer will accept
def test_every_wizard_secret_is_a_real_secret():
    for _name, _label, _description, _config_keys, secret_keys in monitor.WIZARD_SECTIONS:
        for key in secret_keys:
            assert key in monitor.SECRET_KEYS, f"the wizard collects {key}, which is not a known secret"


# Verifies the documented status markers are the ones the doctor actually prints
def test_the_documented_doctor_markers_match_the_code():
    text = (DOCS_DIR / "troubleshooting.md").read_text(encoding="utf-8")

    for marker in ("[PASS]", "[WARN]", "[FAIL]", "[SKIP]"):
        assert f"`{marker}`" in text, f"{marker} is not documented"
    # A fifth marker in the docs would mean the page and the code disagree
    assert "[ -- ]" not in text


# Verifies the documented doctor sections are exactly the ones the report renders
def test_the_documented_doctor_sections_match_the_code():
    text = (DOCS_DIR / "troubleshooting.md").read_text(encoding="utf-8")

    for section in monitor.DOCTOR_SECTIONS:
        assert f"**{section}**" in text, f"the {section} doctor section is not documented"


# Verifies the release notes lead with the version the module declares
def test_the_release_notes_lead_with_the_declared_version():
    first_heading = next(line for line in RELEASE_NOTES.read_text(encoding="utf-8").splitlines() if line.startswith("# Changes in "))

    assert first_heading.startswith(f"# Changes in {monitor.VERSION} "), first_heading


# Verifies the documented Python minimum matches the one constant the code holds
def test_the_documented_python_minimum_matches_the_code():
    assert f"Python {monitor.MINIMUM_PYTHON_VERSION_TEXT}" in all_docs_text(), "the documentation states a different Python minimum"


# Verifies the site configuration and the code agree on where the documentation lives
def test_the_site_url_matches_the_code():
    site_url = re.search(r"^site_url:\s*(\S+)\s*$", MKDOCS.read_text(encoding="utf-8"), flags=re.MULTILINE)

    assert site_url is not None
    assert site_url.group(1).rstrip("/") == monitor.DOCS_BASE_URL.rstrip("/")


# Verifies the README stayed a landing page rather than growing back into the full documentation
def test_the_readme_is_a_landing_page():
    text = README.read_text(encoding="utf-8")

    assert len(text) < 8000, "the README has grown back into full documentation"
    assert monitor.DOCS_BASE_URL in text, "the README does not link to the documentation site"


# Verifies the documentation build is a gate CI runs, not something only checked by hand
def test_the_documentation_build_is_a_ci_gate():
    workflow = (REPO_ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    assert "mkdocs build --strict" in workflow, "CI does not build the documentation site"
    assert "docs/requirements.txt" in workflow, "CI does not install the documentation dependencies"


# Verifies a published site can actually be built, since the workflow that deploys it must have somewhere to deploy from
def test_the_site_has_a_publishing_workflow():
    workflow = REPO_ROOT / ".github" / "workflows" / "docs.yml"

    assert workflow.exists(), "there is no workflow to publish the documentation"
    assert "mkdocs gh-deploy" in workflow.read_text(encoding="utf-8")


# Verifies the bug report asks for doctor output, which closes the loop between the diagnostic and the support channel
def test_the_bug_report_asks_for_doctor_output():
    template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text(encoding="utf-8")

    assert "--doctor" in template, "the bug report template does not ask for doctor output"


# Returns one page's markdown with fenced code blocks removed, so shell comments are not read as headings
def prose_lines(path):
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    return text.splitlines()


# Verifies each page has exactly one title, which a mechanical split silently breaks
def test_each_page_has_exactly_one_title():
    for path in sorted(DOCS_DIR.glob("*.md")):
        titles = [line for line in prose_lines(path) if line.startswith("# ")]
        assert len(titles) == 1, f"{path.name} has {len(titles)} titles: {titles}"


# Verifies no section is documented on two pages, since a reader who finds one will not know the other exists
def test_no_section_is_duplicated_across_pages():
    seen = {}
    duplicates = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        for line in prose_lines(path):
            if not line.startswith("## "):
                continue
            title = line[3:].strip()
            if title in seen:
                duplicates.append(f"'{title}' in both {seen[title]} and {path.name}")
            seen[title] = path.name

    assert not duplicates, f"sections documented twice: {duplicates}"


# Verifies the set of pages is what the project intends, so a page cannot appear or vanish unnoticed
def test_the_page_set_is_deliberate():
    expected = {"index.md", "installation.md", "setup-and-first-run.md", "configuration.md", "usage.md", "troubleshooting.md", "testing.md", "about.md"}

    assert {path.name for path in DOCS_DIR.glob("*.md")} == expected


# Verifies a page is never named after something this project does not have
def test_no_page_promises_tooling_that_does_not_exist():
    # The sibling tools have a Debugging Tools page because they ship standalone utilities in a debug directory
    if not (REPO_ROOT / "debug").is_dir():
        assert not (DOCS_DIR / "debugging.md").exists(), "there is a Debugging Tools page but no debug utilities to document"


# Verifies each section sits on the page a reader would look for it on, matching the sibling tools
@pytest.mark.parametrize("section,page", [
    ("Requirements", "installation.md"),
    ("Doctor Preflight", "troubleshooting.md"),
    ("Verbose and Debug Output", "troubleshooting.md"),
    ("Coloring Log Output with GRC", "usage.md"),
    ("Storing Secrets", "configuration.md"),
    ("Guided Setup", "setup-and-first-run.md"),
])
def test_sections_sit_on_the_page_a_reader_expects(section, page):
    located = [path.name for path in sorted(DOCS_DIR.glob("*.md")) if f"## {section}" in "\n".join(prose_lines(path))]

    assert located == [page], f"'{section}' is on {located}, expected {page}"
