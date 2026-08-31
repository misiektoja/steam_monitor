"""Tests the doctor preflight report: its checks, its output contract and its exit code."""

import os
import pty
import re
import select
import subprocess
import sys
from pathlib import Path

import pytest

import steam_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_API_KEY = "0123456789ABCDEF0123456789ABCDEF"
SECRET_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/verysecrettokenvalue"


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
    report.checks.extend(monitor.doctor_check_configuration(config_path, env_path))
    report.checks.extend(monitor.doctor_check_connectivity())
    report.checks.extend(monitor.doctor_check_authentication(report))
    report.checks.extend(monitor.doctor_check_target(report, target_value))
    report.checks.extend(monitor.doctor_check_email_notifications(report))
    report.checks.extend(monitor.doctor_check_webhook_notifications(report))
    return report


# Verifies only the four agreed status markers can appear, which is the biggest source of drift between tools
def test_only_four_status_markers_are_used(monkeypatch, doctor_globals):
    report = build_report(monkeypatch, target_value=76561197960435530, client=FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))

    rendered = monitor.render_doctor_report(report)

    markers = set(re.findall(r"^\[([A-Z -]+)\]", rendered, flags=re.MULTILINE))
    assert markers <= {"PASS", "WARN", "FAIL", "SKIP"}, markers
    assert "[ -- ]" not in rendered


# Verifies the sections render in the declared order rather than in the order checks happened to be appended
def test_sections_render_in_the_declared_order(monkeypatch, doctor_globals):
    report = build_report(monkeypatch, target_value=76561197960435530, client=FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))

    rendered = monitor.render_doctor_report(report)

    positions = [rendered.index(section) for section in monitor.DOCTOR_SECTIONS if section in rendered]
    assert positions == sorted(positions)


# Verifies the report opens with the heading alone, since the banner already printed the tool name and version
def test_the_report_starts_with_the_bare_heading(monkeypatch, doctor_globals):
    report = build_report(monkeypatch)

    rendered = monitor.render_doctor_report(report)

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


# Verifies a secret value never reaches the report, only its name
def test_no_secret_value_reaches_the_report(monkeypatch, doctor_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_URL", SECRET_WEBHOOK_URL)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_STATUS_NOTIFICATION", True)

    report = build_report(monkeypatch, target_value=76561197960435530, client=FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}]))
    rendered = monitor.render_doctor_report(report)

    assert SECRET_API_KEY not in rendered
    assert SECRET_WEBHOOK_URL not in rendered
    assert "verysecrettokenvalue" not in rendered


# Verifies a deliberately configured setup reads as a pass, not as a shrug
def test_deliberate_configuration_is_a_pass(monkeypatch, doctor_globals):
    report = build_report(monkeypatch)
    labels = {check.label: check.status for check in report.checks}

    assert labels["Email alerts are disabled"] == "PASS"
    assert labels["Webhook alerts are disabled"] == "PASS"
    assert labels["Output logging is disabled"] == "PASS"


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
    assert checks[0].label == "Email alerts are disabled"


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
    assert "All checks passed. You are good to go!" in monitor.render_doctor_report(passing)

    warned = monitor.DoctorReport()
    warned.checks.append(monitor.make_doctor_check("Environment", "WARN", "iffy"))
    assert "All critical checks passed with 1 warning(s). Review the warnings above." in monitor.render_doctor_report(warned)

    failed = monitor.DoctorReport()
    failed.checks.append(monitor.make_doctor_check("Environment", "FAIL", "broken"))
    assert "1 check(s) failed, 0 warning(s). Fix the failures above before relying on the tool." in monitor.render_doctor_report(failed)


# Verifies there is exactly one conclusion, not a second per-channel summary before it
def test_there_is_only_one_summary(monkeypatch, doctor_globals):
    report = build_report(monkeypatch)

    rendered = monitor.render_doctor_report(report)

    assert rendered.count("Summary") == 1
    assert "Delivery test summary" not in rendered


# Verifies the report ends with the doctor guide link
def test_the_report_ends_with_its_guide_link(monkeypatch, doctor_globals):
    rendered = monitor.render_doctor_report(build_report(monkeypatch))

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


# Verifies declining a delivery test records a skip rather than sending anything
def test_declining_a_delivery_test_sends_nothing(monkeypatch, doctor_globals, capsys):
    report = monitor.DoctorReport()
    report.email_ready = True
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    monkeypatch.setattr(monitor, "send_email", lambda *_a, **_k: pytest.fail("an email was sent without approval"))

    checks = monitor._doctor_offer_notification_tests(report)

    assert [check.status for check in checks] == ["SKIP"]
    capsys.readouterr()


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


# Verifies a passing run ends by printing the command that starts monitoring, for this install
def test_a_passing_run_prints_the_monitoring_command(monkeypatch, doctor_globals, capsys):
    client = FakeSteamClient(players=[{"personaname": "P", "communityvisibilitystate": 3}])

    run_doctor_offline(monkeypatch, target_value=76561197960435530, client=client)

    assert "Start monitoring with: " in capsys.readouterr().out


# Returns the doctor transcript from a real pseudo-terminal, the way a user actually sees it
def capture_doctor_pty(config_path, env="none"):
    command = [
        sys.executable, str(REPO_ROOT / "steam_monitor.py"),
        "--config-file", str(config_path), "--env-file", env, "--doctor",
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
    assert SHARED_CONTRACT["all_passed"] in monitor.render_doctor_report(passing)

    warned = monitor.DoctorReport()
    warned.checks.extend([monitor.make_doctor_check("Environment", "WARN", "a"), monitor.make_doctor_check("Environment", "WARN", "b")])
    assert SHARED_CONTRACT["with_warnings"].format(count=2) in monitor.render_doctor_report(warned)

    failed = monitor.DoctorReport()
    failed.checks.extend([monitor.make_doctor_check("Environment", "FAIL", "a"), monitor.make_doctor_check("Environment", "WARN", "b")])
    assert SHARED_CONTRACT["with_failures"].format(failures=1, warnings=1) in monitor.render_doctor_report(failed)


# Verifies the wizard prompt shared with the sibling tools is used verbatim
def test_the_wizard_doctor_prompt_is_shared():
    source = (REPO_ROOT / "steam_monitor.py").read_text(encoding="utf-8")

    assert SHARED_CONTRACT["doctor_prompt"] in source
