"""Contract tests for governance documents, issue templates, workflows and repository metadata."""

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIRECTORY = PROJECT_ROOT / ".github" / "workflows"
REPOSITORY_URL = "https://github.com/misiektoja/steam_monitor"


# Reads one repository file as text
def read_asset(relative_path):
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Reads one repository file as parsed YAML
def read_yaml_asset(relative_path):
    return yaml.safe_load(read_asset(relative_path))


class TestGovernanceDocuments:
    # Contributors are pointed to these documents from the README and templates, so a missing one is a broken promise
    def test_governance_documents_exist(self):
        for relative_path in ("SECURITY.md", "SUPPORT.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "THIRD_PARTY_NOTICES.md", "LICENSE", ".github/pull_request_template.md"):
            asset = PROJECT_ROOT / relative_path
            assert asset.is_file(), relative_path
            assert asset.stat().st_size > 200, relative_path

    # A CODEOWNERS entry is what actually requests review on every change
    def test_codeowners_covers_every_path(self):
        assert re.search(r"^\*\s+@\S+", read_asset(".github/CODEOWNERS"), re.M)

    # The policy must name the private reporting route, or reporters fall back to a public issue
    def test_security_policy_routes_reports_privately(self):
        policy = read_asset("SECURITY.md")
        assert "security/advisories/new" in policy
        assert "Do not open a public issue" in policy

    # Contributors need the setup, the checks and the branch to target
    def test_contributing_covers_setup_and_expectations(self):
        contributing = read_asset("CONTRIBUTING.md")
        for concept in ("pip install -e", "python -m pytest", "ruff check", "RELEASE_NOTES.md", "SECURITY.md", "GPL-3.0-or-later", "dev"):
            assert concept in contributing, concept

    # Every declared runtime dependency must carry a license attribution
    def test_third_party_notices_list_every_runtime_dependency(self):
        notices = read_asset("THIRD_PARTY_NOTICES.md").casefold()
        declared = re.search(r"^dependencies = \[(.*?)^\]", read_asset("pyproject.toml"), re.S | re.M)
        assert declared is not None
        for requirement in re.findall(r'"([A-Za-z0-9_.-]+)', declared.group(1)):
            assert requirement.casefold() in notices, requirement

    # Artwork support must stay optional, or every install carries an image library it may never use
    def test_artwork_support_ships_as_an_optional_extra(self):
        pyproject = read_asset("pyproject.toml")
        requirements = read_asset("requirements.txt")

        runtime = re.search(r"^dependencies = \[(.*?)^\]", pyproject, re.S | re.M)
        assert runtime is not None and "Pillow" not in runtime.group(1)
        extra = re.search(r"^ntfy-images = \[(.*?)^\]", pyproject, re.S | re.M)
        assert extra is not None
        assert re.findall(r'"(Pillow[^"]+)"', extra.group(1)) == ["Pillow>=8.0,<9.0; python_version < '3.7'", "Pillow>=9.0,<10.0; python_version == '3.7'", "Pillow>=10.0,<11.0; python_version == '3.8'", "Pillow>=11.3.0,<12; python_version == '3.9'", "Pillow>=12.0.0; python_version >= '3.10'"]
        assert not any(line.strip().startswith("Pillow") for line in requirements.splitlines())
        assert '# Pillow>=12.0.0; python_version >= "3.10"' in requirements

    # The support document must route each request type to a channel that exists
    def test_support_document_routes_every_request_type(self):
        support = read_asset("SUPPORT.md")
        for destination in (f"{REPOSITORY_URL}/discussions", f"{REPOSITORY_URL}/security/advisories/new"):
            assert destination in support, destination


class TestIssueTemplates:
    # Blank issues bypass the forms, and the contact links are what route vulnerabilities away from public issues
    def test_template_config_disables_blank_issues_and_links_reporting(self):
        config = read_yaml_asset(".github/ISSUE_TEMPLATE/config.yml")
        assert config["blank_issues_enabled"] is False
        urls = [link["url"] for link in config["contact_links"]]
        assert any("security/advisories/new" in url for url in urls)

    # A malformed form is silently ignored by GitHub, so every template must parse and declare its required parts
    def test_every_issue_template_is_well_formed(self):
        templates = sorted((PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
        assert [path.name for path in templates] == ["bug_report.yml", "config.yml", "feature_request.yml"]
        for path in templates:
            if path.name == "config.yml":
                continue
            form = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert form["name"] and form["description"]
            assert any(field.get("validations", {}).get("required") for field in form["body"]), path.name

    # The bug form is where a user is most likely to paste a secret, so it must warn first
    def test_bug_report_warns_before_collecting_output(self):
        bug_report = read_asset(".github/ISSUE_TEMPLATE/bug_report.yml")
        assert "SECURITY.md" in bug_report
        assert "Never paste" in bug_report


class TestWorkflowSupplyChain:
    # Every third-party action is pinned to a commit, so a moved tag cannot change what runs with our secrets
    def test_actions_are_pinned_to_commit_shas(self):
        unpinned = []
        for workflow in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
            for match in re.finditer(r"uses:\s*(\S+)", workflow.read_text(encoding="utf-8")):
                reference = match.group(1)
                if reference.startswith("./"):
                    continue
                _action, _, ref = reference.partition("@")
                if not re.fullmatch(r"[0-9a-f]{40}", ref):
                    unpinned.append(f"{workflow.name}: {reference}")
        assert unpinned == []

    # Each pin records the human-readable version so updates stay reviewable
    def test_pinned_actions_carry_a_version_comment(self):
        missing = []
        for workflow in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
            for line in workflow.read_text(encoding="utf-8").splitlines():
                if "uses:" in line and "@" in line and "./" not in line and not re.search(r"#\s*v?\d", line):
                    missing.append(f"{workflow.name}: {line.strip()}")
        assert missing == []

    # Event and input values never reach a shell directly, which would allow script injection
    def test_run_steps_do_not_interpolate_event_values(self):
        offenders = []
        for workflow in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
            for block in re.findall(r"run: \|(.*?)(?=\n      [-a-zA-Z]|\Z)", workflow.read_text(encoding="utf-8"), re.S):
                for line in block.splitlines():
                    if "${{" in line:
                        offenders.append(f"{workflow.name}: {line.strip()}")
        assert offenders == []

    # Publishing must run the suite first, or a broken build reaches PyPI under the project's name
    def test_pypi_publish_depends_on_the_test_suite(self):
        publish = read_yaml_asset(".github/workflows/publish.yml")
        assert publish["jobs"]["test"]["uses"] == "./.github/workflows/tests.yml"
        assert "test" in publish["jobs"]["build-n-publish"]["needs"]

    # The scanning workflows are the automated half of the security posture the policy describes
    def test_security_workflows_cover_code_and_supply_chain(self):
        for workflow_name in ("codeql.yml", "scorecard.yml", "supply-chain.yml", "tests.yml"):
            assert (WORKFLOW_DIRECTORY / workflow_name).is_file(), workflow_name

        codeql = read_yaml_asset(".github/workflows/codeql.yml")
        assert any("python" in str(job).casefold() for job in codeql["jobs"].values())

        supply_chain = read_yaml_asset(".github/workflows/supply-chain.yml")
        assert {"gitleaks", "pip-audit", "sbom"} <= set(supply_chain["jobs"])

    # The suite is worthless if CI never runs it, so the workflow must invoke pytest and the linter
    def test_ci_runs_the_suite_and_the_linter(self):
        workflow = read_yaml_asset(".github/workflows/tests.yml")
        steps = [step for job in workflow["jobs"].values() for step in job["steps"]]
        assert any("pytest" in step.get("run", "") for step in steps)
        assert any("ruff check" in step.get("run", "") for step in steps)

    # Dependabot must watch every ecosystem this repository actually declares
    def test_dependabot_watches_actions_and_python_dependencies(self):
        updates = read_yaml_asset(".github/dependabot.yml")["updates"]
        assert {"github-actions", "pip"} <= {entry["package-ecosystem"] for entry in updates}

