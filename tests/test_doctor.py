"""Tests the doctor preflight report: its checks, its output contract and its exit code."""

import os
import pty
import re
import select
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import steam_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]


# Composes the two renderers the way run_doctor does, so a test can assert on the whole transcript
def render_doctor_report(report):
    return monitor.render_doctor_sections(report) + "\n" + monitor.render_doctor_summary(report.checks)
SECRET_API_KEY = "0123456789ABCDEF0123456789ABCDEF"
SECRET_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/verysecrettokenvalue"
# Colour changes only, so the screen-clearing escape a startup always writes is not read as colour
SGR_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture
# Restores every module-level setting the doctor reads, since the whole suite shares one imported module
def doctor_globals(monkeypatch):
    snapshot = {name: value for name, value in vars(monitor).items() if name.isupper()}
    monkeypatch.setattr(monitor, "STEAM_API_KEY", SECRET_API_KEY)
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", True)
    monkeypatch.setattr(monitor, "CSV_FILE", "")
    monkeypatch.setattr(monitor, "PROFILE_CSV_FILE", "")
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "SMTP_HOST", "your_smtp_server_ssl")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "your_sender_email")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "your_receiver_email")
    for name in ("ACTIVE_INACTIVE_NOTIFICATION", "STATUS_NOTIFICATION", "GAME_CHANGE_NOTIFICATION",
                 "STEAM_LEVEL_XP_NOTIFICATION", "FRIENDS_NOTIFICATION", "GAMES_LIBRARY_NOTIFICATION",
                 "NAME_CHANGE_NOTIFICATION", "ERROR_NOTIFICATION"):
        monkeypatch.setattr(monitor, name, False)
    for name in ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_STATUS_NOTIFICATION",
                 "WEBHOOK_GAME_CHANGE_NOTIFICATION", "WEBHOOK_LEVEL_XP_NOTIFICATION", "WEBHOOK_FRIENDS_NOTIFICATION",
                 "WEBHOOK_GAMES_NOTIFICATION", "WEBHOOK_NAME_CHANGE_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION"):
        monkeypatch.setattr(monitor, name, False)
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)


class FakeSteamClient:
    # Answers the one profile lookup the target check makes
    def __init__(self, players=None, error=None):
        self.players = players
        self.error = error
        self.calls = 0

    def call(self, _endpoint, **_kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return {"response": {"players": self.players or []}}


# Runs the whole doctor offline with the Steam client and connectivity replaced
def run_doctor_offline(monkeypatch, target_value=None, client=None, connected=True, config_path=None, env_path=None):
    monkeypatch.setattr(monitor, "check_internet", lambda *_args, **_kwargs: connected)
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda *_args, **_kwargs: client or FakeSteamClient())
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: False, raising=False)
    return monitor.run_doctor(target_value=target_value, config_path=config_path, env_path=env_path)


# Returns the report the doctor would render for the given state
def build_report(monkeypatch, target_value=None, client=None, connected=True, config_path=None, env_path=None):
    report = monitor.DoctorReport()
    monkeypatch.setattr(monitor, "check_internet", lambda *_args, **_kwargs: connected)
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda *_args, **_kwargs: client or FakeSteamClient())
    report.checks.extend(monitor.doctor_check_environment())
    report.checks.extend(monitor.doctor_check_configuration(config_path, env_path, target_value))
    report.checks.extend(monitor.doctor_check_connectivity())
    report.checks.extend(monitor.doctor_check_authentication(report))
    report.checks.extend(monitor.doctor_check_target(report, target_value))
    report.checks.extend(monitor.doctor_check_email_notifications(report))
    report.checks.extend(monitor.doctor_check_webhook_notifications(report))
    return report


# Verifies only the four agreed status markers can appear, which is the biggest source of drift between tools
def test_only_four_status_markers_are_used(monkeypatch, doctor_globals):
    report = build_report(monkeypatch, target_value=76561197960435530, client=FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))

    rendered = render_doctor_report(report)

    markers = set(re.findall(r"^\[([A-Z -]+)\]", rendered, flags=re.MULTILINE))
    assert markers <= {"PASS", "WARN", "FAIL", "SKIP"}, markers
    assert "[ -- ]" not in rendered


# Verifies the sections render in the declared order rather than in the order checks happened to be appended
def test_sections_render_in_the_declared_order(monkeypatch, doctor_globals):
    report = build_report(monkeypatch, target_value=76561197960435530, client=FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))

    rendered = render_doctor_report(report)

    positions = [rendered.index(section) for section in monitor.DOCTOR_SECTIONS if section in rendered]
    assert positions == sorted(positions)


# Verifies the report opens with the heading alone, since the banner already printed the tool name and version
def test_the_report_starts_with_the_bare_heading(monkeypatch, doctor_globals):
    report = build_report(monkeypatch)

    rendered = render_doctor_report(report)

    assert rendered.startswith("Doctor")
    assert "steam_monitor" not in rendered.splitlines()[0]
    assert monitor.VERSION not in rendered.splitlines()[0]


# Verifies the Python version is actually checked rather than printed as bare information
def test_the_python_version_is_checked_not_just_printed():
    supported = monitor.doctor_check_environment(version_info=(3, 14, 0))
    unsupported = monitor.doctor_check_environment(version_info=(2, 7, 18))

    assert supported[0].status == "PASS"
    assert "is supported" in supported[0].label
    assert unsupported[0].status == "FAIL"
    assert unsupported[0].advice is not None
    assert monitor.MINIMUM_PYTHON_VERSION_TEXT in unsupported[0].advice.fix


# Verifies the install method is stated as context, not as a result row no marker can describe
def test_the_install_method_is_reported_without_a_status_marker(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "install_method", lambda: "manual")
    report = build_report(monkeypatch)

    assert not any("Install method" in check.label for check in monitor.doctor_check_environment())

    rendered = render_doctor_report(report)

    assert rendered.splitlines()[1] == "Detected install method: manual"
    assert "[PASS] Install method" not in rendered


# Verifies a missing required dependency fails while a missing optional one only warns
def test_required_and_optional_dependencies_are_separated(monkeypatch):
    # Pillow is reported from the module's own guarded-import flag, not from find_spec, so it is set here too
    monkeypatch.setattr(monitor, "NTFY_IMAGES_AVAILABLE", False)
    checks = monitor.doctor_check_environment(spec_finder=lambda _name: None)

    required = [check for check in checks if check.label.startswith("Required dependency")]
    optional = [check for check in checks if check.label.startswith("Optional dependency")]
    assert required and all(check.status == "FAIL" for check in required)
    assert optional and all(check.status == "WARN" for check in optional)
    assert all("install it with" in check.detail.casefold() for check in optional)


# Verifies a warning about a library that cannot affect this machine is not shown at all
@pytest.mark.parametrize("system, reported", [("Windows", True), ("Linux", False), ("Darwin", False)])
def test_a_platform_specific_dependency_is_only_reported_where_it_applies(monkeypatch, system, reported):
    monkeypatch.setattr(monitor.platform, "system", lambda: system)

    checks = monitor.doctor_check_environment(spec_finder=lambda _name: None)

    assert any("colorama" in check.label for check in checks) is reported


# Verifies the Windows colour library is reported there, so broken colours on that platform have a diagnostic
def test_missing_colorama_is_reported_on_windows(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")

    checks = monitor.doctor_check_environment(spec_finder=lambda name: None if name == "colorama" else object())

    missing = next(check for check in checks if "colorama" in check.label)
    assert missing.status == "WARN"
    assert "older Windows Command Prompt" in missing.detail
    assert "pip3 install colorama" in missing.detail


# Verifies each secret is attributed to the file or the environment, which is the question a user is actually asking
def test_secrets_are_attributed_to_their_source(tmp_path, monkeypatch, doctor_globals):
    env_file = tmp_path / ".env"
    env_file.write_text(f'STEAM_API_KEY="{SECRET_API_KEY}"\n', encoding="utf-8")
    monkeypatch.setenv("STEAM_API_KEY", SECRET_API_KEY)
    monkeypatch.setenv("SMTP_PASSWORD", "exported-only")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "exported-only")
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.delenv("NTFY_ACCESS_TOKEN", raising=False)

    checks = monitor.doctor_check_configuration(config_path="tool.conf", env_path=str(env_file))
    labels = {check.label: check.detail for check in checks}

    assert labels["Secrets loaded from the dotenv file"] == "STEAM_API_KEY"
    assert labels["Secrets loaded from the environment"] == "SMTP_PASSWORD"
    assert f"Path: {env_file}" in labels["Dotenv file loaded"]


# Verifies an explicitly selected missing dotenv file is reported as missing rather than loaded
def test_a_missing_dotenv_file_is_a_warning(tmp_path, doctor_globals):
    missing = tmp_path / "missing.env"

    checks = monitor.doctor_check_configuration(env_path=str(missing))
    missing_check = next(check for check in checks if check.label == "The requested dotenv file was not found")

    assert missing_check.status == "WARN"
    assert missing_check.advice is not None
    assert "--env-file" in missing_check.advice.fix
    assert not any(check.label == "Dotenv file loaded" for check in checks)


# Verifies a secret value never reaches the report, only its name
def test_no_secret_value_reaches_the_report(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_URL", SECRET_WEBHOOK_URL)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_STATUS_NOTIFICATION", True)

    report = build_report(monkeypatch, target_value=76561197960435530, client=FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))
    rendered = render_doctor_report(report)

    assert SECRET_API_KEY not in rendered
    assert SECRET_WEBHOOK_URL not in rendered
    assert "verysecrettokenvalue" not in rendered


# Verifies a deliberately configured setup reads as a pass, not as a shrug
def test_deliberate_configuration_is_a_pass(monkeypatch, doctor_globals):
    report = build_report(monkeypatch)
    labels = {check.label: check.status for check in report.checks}

    assert labels["Email notifications are disabled"] == "PASS"
    assert labels["Webhook alerts are disabled"] == "PASS"
    assert labels["Output logging is disabled"] == "PASS"
    # These labels say everything, so neither row carries a detail that only repeats them
    details = {check.label: check.detail for check in report.checks}
    assert details["Webhook alerts are disabled"] == ""
    assert details["Output logging is disabled"] == ""


# Verifies a webhook that is switched off is never validated or offered a delivery test
def test_a_disabled_webhook_is_not_validated(monkeypatch, doctor_globals):
    # A filled-in URL with the master switch off must not fall through into the validation chain
    monkeypatch.setattr(monitor, "WEBHOOK_URL", SECRET_WEBHOOK_URL)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_webhook_notifications(report)

    assert [check.status for check in checks] == ["PASS"]
    assert checks[0].label == "Webhook alerts are disabled"
    assert report.webhook_ready is False


# Verifies alert types selected while the master switch is off are reported as unable to fire
def test_selected_alerts_with_the_switch_off_are_a_warning(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_STATUS_NOTIFICATION", True)
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_webhook_notifications(report)

    assert checks[0].status == "WARN"
    assert report.webhook_ready is False


# Verifies a webhook that is on with nothing selected warns rather than claiming to be valid
def test_a_webhook_with_no_alert_types_warns(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", SECRET_WEBHOOK_URL)
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_webhook_notifications(report)

    assert checks[0].status == "WARN"
    assert "no alert types are selected" in checks[0].label
    assert report.webhook_ready is False


# Verifies a valid webhook names the service it validated, which matters after the URL is changed
def test_a_valid_webhook_names_its_service(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", SECRET_WEBHOOK_URL)
    monkeypatch.setattr(monitor, "WEBHOOK_STATUS_NOTIFICATION", True)
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_webhook_notifications(report)

    assert checks[0].status == "PASS"
    assert checks[0].label.startswith(monitor.WEBHOOK_READY_CHECK_LABEL)
    assert checks[0].label.endswith("for Discord")
    assert report.webhook_ready is True


# Verifies the display name uses each service's own spelling rather than the casefolded config value
def test_the_provider_display_name_uses_the_services_own_spelling():
    assert monitor.webhook_provider_display_name("discord") == "Discord"
    assert monitor.webhook_provider_display_name("ntfy") == "ntfy"


# Verifies the error alert alone does not make a channel count as enabled, or every fresh install would warn
def test_the_default_error_alert_alone_does_not_enable_a_channel(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_email_notifications(report)

    assert checks[0].status == "PASS"
    assert checks[0].label == "Email notifications are disabled"


# Applies a complete email setup so the ready path can be reached without touching a real server
def configure_email(monkeypatch):
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_SSL", True)
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.invalid")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "app-password-placeholder")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "monitor@example.invalid")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "owner@example.invalid")
    monkeypatch.setattr(monitor, "STATUS_NOTIFICATION", True)


# Verifies the ready row confirms a real sign-in and names the alerts that would fire, as the siblings do
def test_the_email_ready_row_reports_the_sign_in_and_the_alerts(monkeypatch, doctor_globals):
    configure_email(monkeypatch)
    closed = []
    monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda *_args, **_kwargs: SimpleNamespace(quit=lambda: closed.append(True)))
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_email_notifications(report)

    assert checks[0].status == "PASS"
    assert checks[0].label == "SMTP connection and login succeeded"
    assert checks[0].detail == "Alerts: status. No email was sent during this passive check"
    assert report.email_ready is True
    assert closed == [True]


# Verifies email alerts that cannot deliver are one WARN whose detail and action name the same settings
def test_unusable_email_settings_warn_and_name_the_same_settings(monkeypatch, doctor_globals):
    configure_email(monkeypatch)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "your_smtp_password")

    def refuse(*_args, **_kwargs):
        raise AssertionError("SMTP was contacted")

    monkeypatch.setattr(monitor, "smtp_connect_and_login", refuse)
    report = monitor.DoctorReport()

    check = monitor.doctor_check_email_notifications(report)[0]

    assert check.status == "WARN"
    assert check.label == monitor.EMAIL_UNUSABLE_CHECK_LABEL
    assert check.detail == "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder"
    assert check.advice is not None
    assert "Set SMTP_USER and SMTP_PASSWORD or turn the email alerts off" in check.advice.fix
    assert monitor.SMTP_GUIDE_URL in check.advice.fix
    assert report.email_ready is False


# Verifies the row names only the settings that are actually unset, not every setting it checked
def test_the_unusable_email_row_names_only_the_unset_settings(monkeypatch, doctor_globals):
    configure_email(monkeypatch)
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "your_receiver_email")

    def refuse(*_args, **_kwargs):
        raise AssertionError("SMTP was contacted")

    monkeypatch.setattr(monitor, "smtp_connect_and_login", refuse)

    check = monitor.doctor_check_email_notifications(monitor.DoctorReport())[0]

    assert check.status == "WARN"
    assert check.detail == "RECEIVER_EMAIL is empty or still set to its placeholder"
    assert check.advice is not None
    assert "Set RECEIVER_EMAIL or turn the email alerts off" in check.advice.fix


# Verifies a rejected sign-in fails the check, which a settings-only check would have passed
def test_a_rejected_smtp_sign_in_fails_the_check(monkeypatch, doctor_globals):
    configure_email(monkeypatch)

    def refuse(*_args, **_kwargs):
        raise monitor.smtplib.SMTPAuthenticationError(535, b"authentication failed")

    monkeypatch.setattr(monitor, "smtp_connect_and_login", refuse)
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_email_notifications(report)

    assert checks[0].status == "FAIL"
    assert checks[0].advice is not None
    assert report.email_ready is False


# Verifies the authentication check runs once and later checks reuse its client rather than reauthenticating
def test_the_steam_client_is_opened_once(monkeypatch, doctor_globals):
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}])
    opened = []
    monkeypatch.setattr(monitor, "check_internet", lambda *_args, **_kwargs: True)

    def open_client(*_args, **_kwargs):
        opened.append(True)
        return client

    monkeypatch.setattr(monitor, "steam_web_api_client", open_client)
    report = monitor.DoctorReport()
    report.checks.extend(monitor.doctor_check_authentication(report))
    report.checks.extend(monitor.doctor_check_target(report, 76561197960435530))

    assert len(opened) == 1
    assert report.player_summary is not None


# Verifies doctor accepts a vanity target and checks the resolved Steam64 ID
def test_doctor_resolves_a_vanity_target(monkeypatch, doctor_globals):
    resolved = 76561197960435530
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}])
    report = monitor.DoctorReport()
    report.steam_client = client
    monkeypatch.setattr(monitor, "resolve_steam_community_url", lambda _url, key: resolved if key == SECRET_API_KEY else pytest.fail("wrong API key"))

    checks = monitor.doctor_check_target(report, "misiektoja")

    assert checks[0].status == "PASS"
    assert report.steam_id == resolved


# Verifies a private profile warns rather than passing silently, since nothing can be detected while it is private
def test_a_private_profile_warns(monkeypatch, doctor_globals):
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 1}])
    report = build_report(monkeypatch, target_value=76561197960435530, client=client)

    visibility = [check for check in report.checks if check.section == "Target" and "visible" in check.label]
    assert visibility and visibility[0].status == "WARN"
    assert visibility[0].advice is not None


# Verifies the target lookup is skipped, not failed, when authentication never produced a client
def test_the_target_is_skipped_without_authentication(doctor_globals, monkeypatch):
    monkeypatch.setattr(monitor, "STEAM_API_KEY", "your_steam_web_api_key")
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_target(report, 76561197960435530)

    assert checks[0].status == "SKIP"


# Verifies each summary sentence states the conclusion rather than leaving the reader to count
def test_the_summary_states_a_conclusion():
    passing = monitor.DoctorReport()
    passing.checks.append(monitor.make_doctor_check("Environment", "PASS", "fine"))
    assert "All checks passed. You are good to go!" in render_doctor_report(passing)

    warned = monitor.DoctorReport()
    warned.checks.append(monitor.make_doctor_check("Environment", "WARN", "iffy"))
    assert "All critical checks passed with 1 warning(s). Review the warnings above." in render_doctor_report(warned)

    failed = monitor.DoctorReport()
    failed.checks.append(monitor.make_doctor_check("Environment", "FAIL", "broken"))
    assert "1 check(s) failed, 0 warning(s). Fix the failures above before relying on the tool." in render_doctor_report(failed)


# Verifies the log row names the file monitoring will actually open once a target is known
def test_the_log_destination_is_resolved_when_a_target_is_known(tmp_path, monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "ST_LOGFILE", str(tmp_path / "steam_monitor"))
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "")

    checks = monitor.doctor_output_destination_checks(76561197960435530)

    assert checks[0].status == "PASS"
    assert checks[0].label == "Log destination appears writable"
    assert checks[0].detail == f"Path: {tmp_path / 'steam_monitor_76561197960435530.log'}"
    # The reported path is the one monitoring opens, not a separately assembled name
    assert monitor.build_log_path(monitor.ST_LOGFILE, "76561197960435530") == tmp_path / "steam_monitor_76561197960435530.log"


# Verifies a configured suffix replaces the Steam ID in the reported log destination
def test_a_configured_file_suffix_names_the_log_destination(tmp_path, monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "ST_LOGFILE", str(tmp_path / "steam_monitor"))
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "mybox")

    checks = monitor.doctor_output_destination_checks(76561197960435530)

    assert checks[0].detail == f"Path: {tmp_path / 'steam_monitor_mybox.log'}"


# Verifies the log row defers instead of guessing when nothing names the file yet
def test_the_log_destination_is_deferred_without_a_target(tmp_path, monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "ST_LOGFILE", str(tmp_path / "steam_monitor"))
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "")

    checks = monitor.doctor_output_destination_checks()

    assert checks[0].status == "PASS"
    assert checks[0].label == "Log destination will be finalized after a target is selected"
    assert checks[0].detail == f"Base path: {tmp_path / 'steam_monitor'}"


# Verifies an unwritable output path fails preflight rather than passing and crashing at startup
@pytest.mark.parametrize("setting,label", [("ST_LOGFILE", "Log destination"), ("CSV_FILE", "CSV destination"), ("PROFILE_CSV_FILE", "Profile CSV destination")])
def test_an_unwritable_output_path_fails(monkeypatch, doctor_globals, setting, label):
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "ST_LOGFILE", "")
    monkeypatch.setattr(monitor, setting, "/nonexistent-root-dir/steam_monitor")
    monkeypatch.setattr(monitor.os, "access", lambda *_args, **_kwargs: False)

    failures = [check for check in monitor.doctor_output_destination_checks(76561197960435530) if check.status == "FAIL"]

    assert len(failures) == 1
    assert failures[0].label.startswith(f"{label} is not writable")
    assert failures[0].advice is not None


# Verifies a check whose detail only repeats its label renders that sentence once
def test_a_detail_repeating_the_label_is_not_printed_twice(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "not-a-url")
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    report = monitor.DoctorReport()
    report.checks.extend(monitor.doctor_check_webhook_notifications(report))

    rendered = render_doctor_report(report)

    assert "[FAIL] WEBHOOK_URL must contain a complete HTTPS link" in rendered
    assert rendered.count("WEBHOOK_URL must contain a complete HTTPS link") == 1


# Verifies every rendered result marker carries its status colour, not just the section headings
def test_every_marker_is_coloured_in_the_rendered_report(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)})
    report = build_report(monkeypatch, target_value=76561197960435530, client=FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))

    rendered = render_doctor_report(report)

    assert "[PASS]" in monitor.ANSI_ESCAPE_RE.sub("", rendered)
    assert not re.search(r"^\[(PASS|WARN|FAIL|SKIP)\]", rendered, flags=re.MULTILINE)
    for status in monitor.DOCTOR_MARK_STYLES:
        marker = monitor.render_doctor_marker(status)
        if f"[{status}]" in monitor.ANSI_ESCAPE_RE.sub("", rendered):
            assert marker in rendered, status


# Verifies there is exactly one conclusion, not a second per-channel summary before it
def test_there_is_only_one_summary(monkeypatch, doctor_globals):
    report = build_report(monkeypatch)

    rendered = render_doctor_report(report)

    assert rendered.count("Summary") == 1
    assert "Delivery test summary" not in rendered


# Verifies the report ends with the doctor guide link
def test_the_report_ends_with_its_guide_link(monkeypatch, doctor_globals):
    rendered = render_doctor_report(build_report(monkeypatch))

    assert rendered.rstrip().endswith(f"Guide: {monitor.DOCTOR_GUIDE_URL}")


# Verifies the exit code is usable as a container healthcheck or CI smoke test
def test_the_exit_code_reflects_the_result(monkeypatch, doctor_globals, capsys):
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}])
    assert run_doctor_offline(monkeypatch, target_value=76561197960435530, client=client) == 0

    assert run_doctor_offline(monkeypatch, connected=False) == 1
    capsys.readouterr()


# Verifies a warning alone does not fail the run, since a warning is not a blocker
def test_a_warning_alone_exits_zero(monkeypatch, doctor_globals, capsys):
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 1}])

    assert run_doctor_offline(monkeypatch, target_value=76561197960435530, client=client) == 0
    capsys.readouterr()


# Verifies no delivery test is offered without a terminal, so a scripted or containerized run stays message-free
def test_no_delivery_test_is_offered_without_a_terminal(monkeypatch, doctor_globals):
    report = monitor.DoctorReport()
    report.email_ready = True
    report.webhook_ready = True
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: False, raising=False)
    sent = []
    monkeypatch.setattr(monitor, "send_email", lambda *_a, **_k: sent.append("email") or 0)
    monkeypatch.setattr(monitor, "send_webhook", lambda *_a, **_k: sent.append("webhook") or 0)

    assert monitor._doctor_offer_notification_tests(report) == []
    assert sent == []


# Verifies a channel that only warned is never offered a delivery test
def test_a_warned_channel_is_not_offered_a_delivery_test(monkeypatch, doctor_globals, capsys):
    report = monitor.DoctorReport()
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", SECRET_WEBHOOK_URL)
    monitor.doctor_check_webhook_notifications(report)

    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor, "send_webhook", lambda *_a, **_k: pytest.fail("a warned channel was sent a delivery test"))

    assert monitor._doctor_offer_notification_tests(report) == []
    capsys.readouterr()


# Verifies declining a delivery test reports the skip on screen rather than sending anything
def test_declining_a_delivery_test_sends_nothing(monkeypatch, doctor_globals, capsys):
    report = monitor.DoctorReport()
    report.email_ready = True
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    monkeypatch.setattr(monitor, "send_email", lambda *_a, **_k: pytest.fail("an email was sent without approval"))

    checks = monitor._doctor_offer_notification_tests(report)

    assert [(check.status, check.label) for check in checks] == [("SKIP", "Test email was not sent")]
    assert "[SKIP] Test email was not sent" in capsys.readouterr().out


# Verifies an approved delivery test sends exactly one message and reports the outcome
def test_an_approved_delivery_test_sends_one_message(monkeypatch, doctor_globals, capsys):
    report = monitor.DoctorReport()
    report.email_ready = True
    sent = []
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    monkeypatch.setattr(monitor, "send_email", lambda *_a, **_k: (sent.append("email"), 0)[1])

    checks = monitor._doctor_offer_notification_tests(report)

    assert sent == ["email"]
    assert [check.status for check in checks] == ["PASS"]
    capsys.readouterr()


# Verifies the prompts use the wording shared with the sibling tools, since users learn them once
def test_the_delivery_prompts_use_the_shared_wording(monkeypatch, doctor_globals, capsys):
    report = monitor.DoctorReport()
    report.email_ready = True
    report.webhook_ready = True
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    asked = []
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "n")

    monitor._doctor_offer_notification_tests(report)

    assert "Send one test email now? This will deliver a real message [y/N]: " in asked
    assert "Send one test webhook through ntfy now? This will publish a real notification [y/N]: " in asked
    capsys.readouterr()


# Verifies the notice states what doctor will not do before any slow check runs, not afterwards
def test_the_preflight_notice_precedes_the_checks(monkeypatch, doctor_globals, capsys):
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}])
    run_doctor_offline(monkeypatch, target_value=76561197960435530, client=client)

    output = capsys.readouterr().out
    assert output.index("Running preflight checks. No files will be written.") < output.index("Doctor")


# Verifies the report leaves the monitoring command to the next steps block, so it is printed once
def test_a_passing_run_leaves_the_monitoring_command_to_the_next_steps(monkeypatch, doctor_globals, capsys):
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}])

    run_doctor_offline(monkeypatch, target_value=76561197960435530, client=client)

    output = capsys.readouterr().out
    assert "Start monitoring with: " not in output
    assert "76561197960435530" not in output.split("Summary", 1)[1]


# Returns the doctor transcript from a real pseudo-terminal, the way a user actually sees it
def capture_doctor_pty(config_path, env="none", extra_arguments=()):
    command = [
        sys.executable, str(REPO_ROOT / "steam_monitor.py"),
        "--config-file", str(config_path), "--env-file", env, "--doctor",
        *extra_arguments,
    ]
    controller, worker = pty.openpty()
    process = subprocess.Popen(command, stdin=worker, stdout=worker, stderr=worker, cwd=str(REPO_ROOT), env={**os.environ, "STEAM_API_KEY": "A" * 32, "TERM": "xterm"})
    os.close(worker)
    chunks = []
    try:
        while True:
            ready, _, _ = select.select([controller], [], [], 60)
            if not ready:
                break
            try:
                data = os.read(controller, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
    finally:
        os.close(controller)
        process.wait(timeout=60)
    return b"".join(chunks).decode("utf-8", errors="replace"), process.returncode


# Collapses a raw terminal transcript the way a terminal would, so transient progress is not read as content
def clean_transcript(raw):
    without_colour = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", raw)
    lines = []
    for line in without_colour.split("\n"):
        # Drop the CR of a CRLF line ending first, then keep only what survives the last overwrite
        if line.endswith("\r"):
            line = line[:-1]
        lines.append(line.split("\r")[-1])
    return lines


# Splits a raw transcript into the segments a terminal would treat as separate writes to a line
def transcript_segments(raw):
    without_colour = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", raw)
    return [segment for segment in re.split(r"[\r\n]", without_colour)]


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies the output contract holds on the path a user actually walks, which unit tests cannot see
def test_the_doctor_transcript_holds_the_output_contract(tmp_path):
    config = tmp_path / "doctor.conf"
    # An unroutable endpoint keeps the run offline and deterministic without changing the output shape
    config.write_text('CLEAR_SCREEN = False\nDISABLE_LOGGING = True\nCHECK_INTERNET_URL = "https://localhost:1/"\nCHECK_INTERNET_TIMEOUT = 1\n', encoding="utf-8")

    raw, exit_code = capture_doctor_pty(config)

    # Ordering is asserted on the raw stream, since the transient progress is erased before the report prints
    segments = transcript_segments(raw)
    notice_index = next(index for index, segment in enumerate(segments) if "Running preflight checks" in segment)
    progress_indexes = [index for index, segment in enumerate(segments) if segment.strip().startswith("* Checking ")]
    heading_index = next(index for index, segment in enumerate(segments) if segment.strip() == "Doctor")
    assert progress_indexes, "no transient progress was written to the terminal"
    assert notice_index < min(progress_indexes)
    assert max(progress_indexes) < heading_index

    # Nothing may share the progress line, which is what a check printing mid-progress looks like
    for index in progress_indexes:
        assert segments[index].strip().endswith("..."), f"output collided with the progress line: {segments[index]!r}"

    # Layout is asserted on the collapsed view, which is what the reader actually sees
    lines = clean_transcript(raw)
    text = "\n".join(lines)
    visible_heading = next(index for index, line in enumerate(lines) if line.strip() == "Doctor")
    doubles = [index for index in range(visible_heading, len(lines) - 1) if not lines[index].strip() and not lines[index + 1].strip()]
    assert not doubles, f"double blank lines at {doubles}:\n{text}"

    markers = set(re.findall(r"^\[([A-Z -]+)\]", text, flags=re.MULTILINE))
    assert markers <= {"PASS", "WARN", "FAIL", "SKIP"}, markers
    assert text.count("Summary") == 1
    assert f"Guide: {monitor.DOCTOR_GUIDE_URL}" in text
    assert exit_code in (0, 1)


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies doctor honours COLORED_OUTPUT from the config file, which it used to exit before ever reading
def test_the_configured_colour_reaches_the_doctor_screen(tmp_path):
    config = tmp_path / "doctor.conf"
    config.write_text('CLEAR_SCREEN = False\nDISABLE_LOGGING = True\nCOLORED_OUTPUT = True\nCHECK_INTERNET_URL = "https://localhost:1/"\nCHECK_INTERNET_TIMEOUT = 1\n', encoding="utf-8")

    raw, _exit_code = capture_doctor_pty(config)

    assert SGR_SEQUENCE_RE.search(raw), "the configured colour never reached the screen"
    # Every result marker carries a colour, which is the part the section headings never proved
    assert not re.search(r"(?<!m)\[(PASS|WARN|FAIL|SKIP)\]", raw), "an uncoloured status marker reached the screen"


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies --no-color still wins over a config file that turns colour on
def test_no_color_overrides_the_configured_colour(tmp_path):
    config = tmp_path / "doctor.conf"
    config.write_text('CLEAR_SCREEN = False\nDISABLE_LOGGING = True\nCOLORED_OUTPUT = True\nCHECK_INTERNET_URL = "https://localhost:1/"\nCHECK_INTERNET_TIMEOUT = 1\n', encoding="utf-8")

    raw, _exit_code = capture_doctor_pty(config, extra_arguments=["--no-color"])

    assert not SGR_SEQUENCE_RE.search(raw)


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies the transient progress is erased rather than left behind in the finished report
def test_the_transient_progress_is_cleared(tmp_path):
    config = tmp_path / "doctor.conf"
    config.write_text('CLEAR_SCREEN = False\nDISABLE_LOGGING = True\nCHECK_INTERNET_URL = "https://localhost:1/"\nCHECK_INTERNET_TIMEOUT = 1\n', encoding="utf-8")

    raw, _exit_code = capture_doctor_pty(config)

    # It was written to the terminal, and it survives nowhere in what the reader is left looking at
    assert any(segment.strip().startswith("* Checking ") for segment in transcript_segments(raw))
    assert not [line for line in clean_transcript(raw) if line.strip().startswith("* Checking ")]


# Verifies piped output carries no progress line at all, so logs and CI output stay clean
def test_piped_output_has_no_progress_line(monkeypatch, doctor_globals, capsys):
    monkeypatch.setattr(monitor, "check_internet", lambda *_a, **_k: True)
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda *_a, **_k: FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: False, raising=False)

    monitor.run_doctor(target_value=76561197960435530)

    output = capsys.readouterr().out
    assert "* Checking " not in output
    assert "\r" not in output


# Verifies the command-line API key is effective before doctor checks authentication
def test_doctor_consumes_the_command_line_api_key(monkeypatch, doctor_globals):
    observed = {}
    command_line_key = "B" * 32
    monkeypatch.setattr(monitor, "find_config_file", lambda _path=None: None)
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", False)
    monkeypatch.setattr(monitor, "stdout_bck", None)
    monkeypatch.setattr("sys.argv", ["steam_monitor.py", "--doctor", "--env-file", "none", "-u", command_line_key])

    # Records the key visible at the real doctor call boundary
    def record_doctor(**_kwargs):
        observed["key"] = monitor.STEAM_API_KEY
        return 0

    monkeypatch.setattr(monitor, "run_doctor", record_doctor)

    with pytest.raises(SystemExit) as exit_info:
        monitor.main()

    assert exit_info.value.code == 0
    assert observed["key"] == command_line_key


# The user-visible strings that must read identically across the sibling tools, since users learn them once
SHARED_CONTRACT = {
    "preflight_notice": "Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.",
    "all_passed": "All checks passed. You are good to go!",
    "with_warnings": "All critical checks passed with {count} warning(s). Review the warnings above.",
    "with_failures": "{failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool.",
    "doctor_prompt": "Run doctor now? It writes no files and offers real delivery tests only with separate approval.",
    "email_prompt": "Send one test email now? This will deliver a real message",
    "webhook_prompt": "Send one test webhook through {provider} now? This will publish a real notification",
    "delivery_heading": "Optional delivery tests",
    "delivery_notice": "Doctor will not write files. Each approved test sends one real message.",
}


# Verifies the shared wording is produced verbatim, so drift from the sibling tools fails here
def test_the_shared_output_contract_is_produced_verbatim(monkeypatch, doctor_globals, capsys):
    report = monitor.DoctorReport()
    report.email_ready = True
    report.webhook_ready = True
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "n")

    monitor.render_doctor_notice()
    monitor._doctor_offer_notification_tests(report)
    output = capsys.readouterr().out

    assert SHARED_CONTRACT["preflight_notice"] in output
    assert SHARED_CONTRACT["delivery_heading"] in output
    assert SHARED_CONTRACT["delivery_notice"] in output
    assert any(prompt.startswith(SHARED_CONTRACT["email_prompt"]) for prompt in asked)
    assert any(prompt.startswith(SHARED_CONTRACT["webhook_prompt"].format(provider="ntfy")) for prompt in asked)


# Verifies each summary sentence renders exactly as the contract states it, including its punctuation
def test_the_summary_sentences_render_verbatim():
    passing = monitor.DoctorReport()
    passing.checks.append(monitor.make_doctor_check("Environment", "PASS", "fine"))
    assert SHARED_CONTRACT["all_passed"] in render_doctor_report(passing)

    warned = monitor.DoctorReport()
    warned.checks.extend([monitor.make_doctor_check("Environment", "WARN", "a"), monitor.make_doctor_check("Environment", "WARN", "b")])
    assert SHARED_CONTRACT["with_warnings"].format(count=2) in render_doctor_report(warned)

    failed = monitor.DoctorReport()
    failed.checks.extend([monitor.make_doctor_check("Environment", "FAIL", "a"), monitor.make_doctor_check("Environment", "WARN", "b")])
    assert SHARED_CONTRACT["with_failures"].format(failures=1, warnings=1) in render_doctor_report(failed)


# Verifies the wizard prompt shared with the sibling tools is used verbatim
def test_the_wizard_doctor_prompt_is_shared():
    source = (REPO_ROOT / "steam_monitor.py").read_text(encoding="utf-8")

    assert SHARED_CONTRACT["doctor_prompt"] in source


# Verifies the Python row states the minimum it was judged against, whichever way the judgement went
def test_the_python_row_names_the_minimum_supported_version():
    supported = monitor.doctor_check_environment(version_info=(3, 14, 0))[0]
    unsupported = monitor.doctor_check_environment(version_info=(2, 7, 18))[0]

    assert supported.detail == f"Minimum supported version: {monitor.MINIMUM_PYTHON_VERSION_TEXT}"
    assert unsupported.detail == supported.detail


# Verifies every doctor detail keeps to the agreed shapes: it never repeats its label, gives an instruction or joins values with a pipe
def test_doctor_details_keep_to_the_agreed_shapes():
    import ast
    import inspect

    # Renders one detail argument as text, standing in {} for the parts an f-string fills at runtime
    def detail_text(node):
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            return "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in node.values)
        return None

    offenders = []
    for node in ast.walk(ast.parse(inspect.getsource(monitor))):
        if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"make_doctor_check", "report.add"} or len(node.args) < 4:
            continue
        label, text = node.args[2], detail_text(node.args[3])
        if text is None:
            continue
        if isinstance(label, ast.Constant) and text == label.value:
            offenders.append(f"{node.lineno}: the detail repeats its label")
        if text.startswith(("Use ", "Set ", "Run ")):
            offenders.append(f"{node.lineno}: the detail gives an instruction, which belongs in the fix line")
        if " | " in text:
            offenders.append(f"{node.lineno}: the detail joins two values with a pipe")
        if text.endswith("."):
            offenders.append(f"{node.lineno}: the detail ends with a full stop")

    assert not offenders, "doctor details outside the agreed shapes:\n" + "\n".join(offenders)


# Verifies the constructor drops a detail that only repeats its label, so no row says the same thing twice
def test_a_detail_that_repeats_its_label_is_dropped():
    check = monitor.make_doctor_check("Configuration", "PASS", "Output logging is disabled", "Output logging is disabled")

    assert check.detail == ""


# Verifies only the four shared markers can reach a report
def test_only_the_four_shared_markers_are_accepted():
    assert monitor.DOCTOR_STATUSES == ("PASS", "WARN", "FAIL", "SKIP")
    assert [monitor.make_doctor_check("Configuration", status, "a label").status for status in monitor.DOCTOR_STATUSES] == list(monitor.DOCTOR_STATUSES)

    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "INFO", "a label")


# Verifies one row reads as one block: the action lines sit under the marker at the detail indent while a pass row has none
def test_the_action_lines_sit_indented_under_their_marker(monkeypatch):
    monkeypatch.setattr(monitor, "colorize", lambda theme, text: text)
    advice = monitor.make_recovery_advice("unknown", "a summary", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), True)
    report = monitor.DoctorReport()
    report.checks = [
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice),
        monitor.make_doctor_check("Configuration", "PASS", "a passing row", "", advice),
    ]

    lines = render_doctor_report(report).splitlines()
    rows = lines[lines.index("[WARN] a warning row"):]

    assert rows[:5] == ["[WARN] a warning row", "  a detail worth keeping", "  To fix: do the thing", f"  Guide: {monitor.DOCTOR_GUIDE_URL}", "[PASS] a passing row"]


# Verifies an approved delivery test that failed reaches the summary, so a failing run cannot report a clean one
def test_a_failed_delivery_test_reaches_the_summary(monkeypatch, doctor_globals):
    report = monitor.DoctorReport()
    report.email_ready = True
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    monkeypatch.setattr(monitor, "send_email", lambda *_a, **_k: 1)

    monitor._doctor_offer_notification_tests(report)

    assert [(check.section, check.status, check.label) for check in report.checks] == [(monitor.DOCTOR_DELIVERY_SECTION, "FAIL", "Doctor test email delivery failed")]
    assert "1 check(s) failed, 0 warning(s)." in monitor.render_doctor_summary(report.checks)


# Verifies every doctor entry point renders its summary after the delivery tests, so the sentence and the exit code describe one run
def test_the_summary_is_rendered_after_the_delivery_tests():
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(monitor))
    checked = 0
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        calls = [(call.lineno, ast.unparse(call.func)) for call in ast.walk(function) if isinstance(call, ast.Call)]
        offers = [lineno for lineno, name in calls if name.endswith("_doctor_offer_notification_tests")]
        summaries = [lineno for lineno, name in calls if name.endswith("render_doctor_summary")]
        if not offers or not summaries:
            continue
        checked += 1
        assert max(offers) < min(summaries), f"{function.name} renders the summary before the delivery tests"

    assert checked, "no doctor entry point runs the delivery tests and then the summary"


# Verifies the Doctor target row reuses the startup gate's advice, so the two surfaces cannot word it differently
def test_a_missing_target_reuses_the_startup_gate_advice(doctor_globals):
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_target(report, None)

    assert checks[0].status == "WARN"
    assert checks[0].advice is not None
    assert checks[0].advice.code == "target.missing"
    assert checks[0].advice.fix == monitor.classify_recovery_error(context="target.missing").fix


# Verifies the connectivity row carries the label and the endpoint detail shared with the sibling monitors
def test_the_connectivity_row_names_the_shared_endpoint(monkeypatch):
    monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://probe.example/ping")
    monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: True)
    passing = monitor.doctor_check_connectivity()[0]
    monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: False)
    failing = monitor.doctor_check_connectivity()[0]

    assert (passing.status, passing.label, passing.detail) == ("PASS", "The connectivity endpoint is reachable", "Endpoint: https://probe.example/ping")
    assert (failing.status, failing.label, failing.detail) == ("FAIL", "The connectivity endpoint could not be reached", "Endpoint: https://probe.example/ping")


# Verifies a failed connectivity check gives network advice rather than the generic debug fallback
def test_the_connectivity_failure_names_the_network_and_the_setting(monkeypatch):
    monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://probe.example/ping")
    monkeypatch.setattr(monitor, "LAST_CONNECTIVITY_ERROR", None)

    # The check records the error the way the real one does, since doctor clears it before every run
    def fail_with(error):
        def failing_check(**kwargs):
            monitor.LAST_CONNECTIVITY_ERROR = error
            return False

        monkeypatch.setattr(monitor, "check_internet", failing_check)
        return monitor.doctor_check_connectivity()[0].advice

    refused = fail_with(monitor.req.ConnectionError("Failed to establish a new connection"))
    timed_out = fail_with(monitor.req.ConnectTimeout("Connection to probe.example timed out"))

    assert refused is not None and timed_out is not None
    assert (refused.code, timed_out.code) == ("network.unavailable", "network.timeout")
    assert refused.fix == timed_out.fix == "Check network, DNS, proxy and CHECK_INTERNET_URL settings"


# Verifies a report read on its own ends with the command that starts monitoring, carrying this run's files
def test_the_report_ends_with_the_command_that_starts_monitoring(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/steam.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/steam.env")

    monitor.print_doctor_next_steps(doctor_exit=0)

    transcript = capsys.readouterr().out
    assert "Next steps" in transcript
    assert "Start monitoring:" in transcript
    assert "--config-file /etc/steam.conf --env-file /etc/steam.env" in transcript
    assert transcript.rstrip().endswith(monitor.QUICK_START_GUIDE_URL)


# Verifies a failing report names the order to work in, rather than inviting a run that cannot succeed yet
def test_a_failing_report_asks_for_the_failures_first(capsys):
    monitor.print_doctor_next_steps(doctor_exit=1)

    assert "After Doctor passes, start monitoring:" in capsys.readouterr().out


# Verifies a target the command line named is carried, so the printed command watches the account just checked
def test_a_command_line_target_is_carried_into_the_command(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")

    monitor.print_doctor_next_steps("76561197960435530", doctor_exit=0)

    assert "76561197960435530" in capsys.readouterr().out


# Verifies the monitoring command carries a target only when the config file will not supply one
def test_the_monitoring_command_leaves_out_a_target_the_config_supplies(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")

    monitor.print_doctor_next_steps("76561197960435530", "76561197960435530", doctor_exit=0)
    saved_transcript = capsys.readouterr().out
    monitor.print_doctor_next_steps(None, "", doctor_exit=0)
    unsaved_transcript = capsys.readouterr().out

    assert "76561197960435530" not in saved_transcript
    assert "<steam_target>" not in saved_transcript
    assert "<steam_target>" in unsaved_transcript


# Verifies Ctrl+C at a delivery prompt ends the run instead of declining one test and asking the next
def test_a_delivery_prompt_interrupt_ends_the_run(monkeypatch):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    # The handler restores the saved stream, so it is pointed at the one this test captures
    monkeypatch.setattr(monitor, "stdout_bck", monitor.sys.stdout)
    monkeypatch.setattr("builtins.input", interrupt)

    with pytest.raises(SystemExit) as raised:
        monitor._doctor_ask_yes_no("Send one test")

    assert raised.value.code == 0


# Verifies every unusable timing or count setting is named in one row, so a fix does not need one run per setting
def test_invalid_numeric_settings_are_reported_in_one_row(monkeypatch):
    monkeypatch.setattr(monitor, "STEAM_CHECK_INTERVAL", 0)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", -1)
    monkeypatch.setattr(monitor, "SMTP_PORT", 70000)

    rows = [item for item in monitor.doctor_check_configuration() if item.label == "One or more numeric settings are invalid"]

    assert [item.status for item in rows] == ["FAIL"]
    assert all(name in rows[0].detail for name in ("STEAM_CHECK_INTERVAL", "LIVENESS_CHECK_INTERVAL", "SMTP_PORT"))
