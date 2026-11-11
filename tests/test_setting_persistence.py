"""Checks saved-setting guidance and reusable Doctor monitoring commands."""

import argparse
import importlib
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

monitor = importlib.import_module("steam_monitor")


@pytest.fixture(autouse=True)
# Keeps command rendering independent of the active installation and files
def clean_command_context(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["steam_monitor.py"])
    for name, value in (("CLI_CONFIG_PATH", "none"), ("DOTENV_FILE", "none"), ("CONFIG_DISCOVERY_DISABLED", True), ("COLOR_ENABLED", False), ("WEB_DASHBOARD_ENABLED", False)):
        monkeypatch.setattr(monitor, name, value, raising=False)
    if hasattr(monitor, "INSTALL_METHOD_ENV_VAR"):
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "manual")


# Preserves explicit values and disabled switches without disclosing command-line credentials
def test_doctor_command_preserves_monitoring_settings(capsys):
    args = argparse.Namespace(check_interval=321, csv_file="output with spaces.csv", truncate=0, notify_errors=False, webhook_enabled=False, steam_api_key="private-command-value", webhook_url="private-command-value")
    monitor.print_doctor_next_steps("76561198000000000", cli_args=args)
    output = capsys.readouterr().out
    command = next(line.strip() for line in output.splitlines() if line.startswith("    "))
    tokens = shlex.split(command)
    assert tokens[tokens.index("--check-interval") + 1] == "321"
    assert tokens[tokens.index("--csv-file") + 1] == "output with spaces.csv"
    assert tokens[tokens.index("--truncate") + 1] == "0"
    assert "--no-error-notify" in tokens
    assert "--no-webhook" in tokens
    assert tokens[tokens.index("--steam-api-key") + 1] == "STEAM_API_KEY"
    assert tokens[tokens.index("--webhook-url") + 1] == "WEBHOOK_URL"
    assert "private-command-value" not in output
    assert "Replace the uppercase credential placeholders" in output


# Prevents a monitoring command from repeating setup, delivery tests or listing actions
def test_monitoring_command_omits_other_actions():
    args = argparse.Namespace(doctor=True, setup=True, generate_config="new.conf", force=True, send_test_email=True, send_test_webhook=True, set_smtp_password=True, info_mode=True, list_recent=True, list_recent_matches=True, list_repos=True, import_browser_cookie=True, import_browser_session=True, export_all_playlists=True, achievements_count=5, games_count=10)
    assert monitor.doctor_monitoring_overrides(args) == ([], False)


# Keeps leading dashes inside values from becoming options when the command is reused
def test_leading_dash_value_is_attached_to_option():
    tokens, private = monitor.doctor_monitoring_overrides(argparse.Namespace(csv_file="-output.csv"))
    assert tokens == ["--csv-file=-output.csv"]
    assert private is False


# Leaves a command with no explicit monitoring overrides compact
def test_no_overrides_adds_no_options_or_credential_notice(capsys):
    args = argparse.Namespace()
    monitor.print_doctor_next_steps("76561198000000000", cli_args=args)
    output = capsys.readouterr().out
    assert "--check-interval" not in output
    assert "credential placeholders" not in output


# Exercises the real Doctor entry point while preventing network access
def test_cli_doctor_next_step_retains_selected_options():
    program = """import importlib, socket, sys
monitor = importlib.import_module("steam_monitor")
socket.socket.connect = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Unexpected network access"))
monitor.run_doctor = lambda *args, **kwargs: 0
sys.argv = ["steam_monitor.py", "--doctor", "--config-file", "none", "--env-file", "none", "--no-color", "--check-interval", "321"] + ["76561198000000000"]
monitor.main()
"""
    result = subprocess.run([sys.executable, "-c", program], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, env=dict(os.environ, NO_COLOR="1"), timeout=30)
    assert result.returncode == 0, result.stderr + result.stdout
    output = result.stdout.split("Next steps", 1)[1]
    assert "--check-interval 321" in output
    assert "76561198000000000" in output
    assert "--doctor" not in output


# Confirms the real help explains that setting flags need to be repeated
def test_help_explains_setting_lifetime():
    assert monitor.__file__ is not None
    result = subprocess.run([sys.executable, str(Path(monitor.__file__).resolve()), "--help"], capture_output=True, text=True, env=dict(os.environ, NO_COLOR="1"), timeout=30)
    assert result.returncode == 0
    assert "Setting options apply to the current run" in result.stdout
    assert "Include them on each run" in result.stdout


# Exercises the actual parser, configuration layers, override mapping and reusable Doctor command without network.
@pytest.mark.parametrize("configured,disable,expected", [(None, False, True), (None, True, False), (True, False, True), (True, True, False), (False, False, False), (False, True, False)])
def test_restart_reporting_cli_and_config_reach_doctor(tmp_path, configured, disable, expected):
    config = tmp_path / "monitor.conf"
    text = "" if configured is None else "REPORT_CHANGES_AFTER_RESTART = {!r}\n".format(configured)
    config.write_text(text, encoding="utf-8")
    arguments = ["steam_monitor.py", "--doctor", "--config-file", str(config), "--env-file", "none", "--no-color"]
    if disable:
        arguments.append("--no-restart-changes")
    arguments.append("76561198000000000")
    program = '''import socket, sys
import steam_monitor as monitor
socket.socket.connect = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Unexpected network access"))
monitor.run_doctor = lambda *args, **kwargs: print("REPORT_RESTART=" + str(monitor.REPORT_CHANGES_AFTER_RESTART)) or 0
sys.argv = ''' + repr(arguments) + '''
monitor.main()
'''
    result = subprocess.run([sys.executable, "-c", program], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, env=dict(os.environ, NO_COLOR="1"), timeout=30)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "REPORT_RESTART=" + str(expected) in result.stdout
    next_command = result.stdout.split("Next steps", 1)[1]
    assert ("--no-restart-changes" in next_command) is disable


# Loading and regenerating the setting preserves both explicit false and the documented default-on value.
@pytest.mark.parametrize("selected", [False, True])
def test_restart_reporting_setting_round_trips_through_saved_config(tmp_path, selected):
    defaults = monitor.parse_config_content(monitor.CONFIG_BLOCK)
    assert defaults["REPORT_CHANGES_AFTER_RESTART"] is True
    config = tmp_path / "monitor.conf"
    config.write_text(monitor.generate_config_with_current_values({"REPORT_CHANGES_AFTER_RESTART": selected}), encoding="utf-8")
    namespace = {}
    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert namespace["REPORT_CHANGES_AFTER_RESTART"] is selected


# The documented boolean participates in the existing runtime validation, rather than silently accepting a string.
@pytest.mark.parametrize("invalid", ["False", None, [], 2])
def test_restart_reporting_uses_existing_boolean_validation(monkeypatch, invalid):
    monkeypatch.setattr(monitor, "REPORT_CHANGES_AFTER_RESTART", invalid)
    assert any("REPORT_CHANGES_AFTER_RESTART must be True or False" in error for error in monitor.runtime_boolean_errors())


# Startup exposes the effective switch immediately beside the feature whose stopped-period changes it controls.
@pytest.mark.parametrize("selected", [False, True])
def test_restart_reporting_summary_row_follows_games_tracking(monkeypatch, selected):
    monkeypatch.setattr(monitor, "REPORT_CHANGES_AFTER_RESTART", selected)
    monkeypatch.setattr(monitor, "GAMES_LIBRARY_CHECK", True)
    rows = monitor.build_startup_summary(target="76561198000000000")
    labels = [row.label for row in rows]
    index = labels.index("Games tracking") + 1
    assert rows[index].label == "Restart change reporting"
    assert rows[index].value == str(selected)
    assert rows[index].concise
