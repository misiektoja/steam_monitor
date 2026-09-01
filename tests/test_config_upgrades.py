"""Tests that a configuration written by an older release still loads, so upgrading cannot strand anyone."""

import re
from pathlib import Path

import pytest

import steam_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = Path(__file__).resolve().parent / "fixtures" / "config_templates"
SHIPPED_TEMPLATES = sorted(TEMPLATE_DIR.glob("*.conf"))


# Reads a block the template ships commented out, as the parser would see it once uncommented
def uncomment_block(first_line):
    lines = monitor.CONFIG_BLOCK.split("\n")
    start = next(index for index, line in enumerate(lines) if line.startswith(first_line))
    end = next(index for index in range(start, len(lines)) if lines[index].rstrip() == "# }")
    return "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in lines[start:end + 1])


# Verifies a generated configuration no longer pins the colours, so the tool's own defaults apply
def test_the_template_leaves_the_theme_to_the_defaults():
    assert "COLOR_THEME" not in monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")
    assert "\n# COLOR_THEME = {\n" in monitor.CONFIG_BLOCK


# Verifies the commented theme in the template still describes exactly what the tool actually uses
def test_the_commented_template_theme_matches_the_built_in_theme():
    values = monitor.parse_config_content(uncomment_block("# COLOR_THEME = {"), "<built-in-config>")

    assert values["COLOR_THEME"] == monitor.DEFAULT_COLOR_THEME


# Verifies a configuration that sets the commented-out theme is still accepted, since older files all set it
def test_a_config_setting_the_theme_is_still_accepted(tmp_path):
    config = tmp_path / "monitor.conf"
    config.write_text('COLOR_THEME = { "username": "green" }\nCLEAR_SCREEN = False\n', encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert namespace["COLOR_THEME"] == {"username": "green"}


# Verifies the fixtures are actually present, so a missing directory cannot silently skip every replay
def test_the_shipped_templates_are_available():
    assert SHIPPED_TEMPLATES, "no shipped configuration templates to replay"
    assert len(SHIPPED_TEMPLATES) >= 6


@pytest.mark.parametrize("template", SHIPPED_TEMPLATES, ids=lambda path: path.stem)
# Verifies the exact configuration each released version generated still parses with the current parser
def test_a_shipped_template_still_parses(template):
    monitor.validate_config_content(template.read_text(encoding="utf-8"), f"<{template.stem}>")


@pytest.mark.parametrize("template", SHIPPED_TEMPLATES, ids=lambda path: path.stem)
# Verifies every setting a released version wrote is either still supported or explicitly retired
def test_no_setting_disappeared_without_being_retired(template):
    old_names = set(re.findall(r"^([A-Z][A-Z0-9_]*)\s*=", template.read_text(encoding="utf-8"), flags=re.MULTILINE))
    known = set(monitor._config_allowed_names()) | set(monitor.RETIRED_CONFIG_SETTINGS)

    vanished = sorted(old_names - known)

    assert not vanished, f"{template.stem} wrote settings this version neither supports nor retires: {vanished}"


@pytest.mark.parametrize("template", SHIPPED_TEMPLATES, ids=lambda path: path.stem)
# Verifies an older configuration applies its values rather than parsing and then being ignored
def test_a_shipped_template_applies_its_values(template):
    namespace = {}

    assert monitor.load_config_file(template, namespace=namespace, report_errors=False) is True
    assert len(namespace) >= 30, f"{template.stem} applied only {len(namespace)} settings"


# Verifies a retired setting is reported and skipped rather than rejecting the whole file
def test_a_retired_setting_is_ignored_with_a_note(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "RETIRED_CONFIG_SETTINGS", frozenset({"SOME_OLD_SETTING"}))
    config = tmp_path / "old.conf"
    config.write_text('SOME_OLD_SETTING = 1\nCLEAR_SCREEN = False\n', encoding="utf-8")
    namespace = {}
    retired = []

    assert monitor.parse_config_content(config.read_text(encoding="utf-8"), str(config), retired) == {"CLEAR_SCREEN": False}
    assert retired == ["SOME_OLD_SETTING"]
    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert namespace == {"CLEAR_SCREEN": False}


# Verifies a customization the literal-only parser cannot accept explains itself instead of just failing
def test_a_helper_variable_is_rejected_with_an_explanation(tmp_path, capsys):
    config = tmp_path / "custom.conf"
    config.write_text('MY_DIR = "/tmp"\nCSV_FILE = MY_DIR + "/out.csv"\n', encoding="utf-8")

    assert monitor.load_config_file(config, namespace={}, report_errors=True) is False

    output = capsys.readouterr().out
    assert "MY_DIR" in output
    assert "Only documented SETTING = value lines" in output
    assert "To fix: " in output


# Verifies every generated file has a configurable destination, so an upgrade cannot scatter new files
@pytest.mark.parametrize("setting", ["CSV_FILE", "PROFILE_CSV_FILE", "ST_LOGFILE", "FILE_SUFFIX"])
def test_every_generated_file_has_a_destination_setting(setting):
    assert setting in monitor._config_allowed_names(), f"{setting} is not a configurable destination"


# Verifies the startup summary names the effective path of every generated file it is writing
def test_the_startup_summary_names_every_destination(monkeypatch):
    monkeypatch.setattr(monitor, "CSV_FILE", "/tmp/activity.csv")
    monkeypatch.setattr(monitor, "PROFILE_CSV_FILE", "/tmp/profile.csv")
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)

    rows = monitor.build_startup_summary("76561198000000000", "tool.conf", "/tmp/.env", "/tmp/tool.log")
    rendered = "\n".join(f"{row.label}: {row.value}" for row in rows)

    for expected in ("/tmp/activity.csv", "/tmp/profile.csv", "/tmp/tool.log", "tool.conf", "/tmp/.env"):
        assert expected in rendered, f"{expected} is missing from the startup summary"
