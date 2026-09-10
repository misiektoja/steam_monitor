"""Tests that every failure carries a stable code, an actionable fix, and no secrets."""

import ast
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests as req

import steam_monitor as monitor


SECRET_API_KEY = "0123456789ABCDEF0123456789ABCDEF"


@pytest.fixture
# Restores the settings the recovery paths read, since the whole suite shares one imported module
def restored_globals():
    names = ("DEBUG_MODE", "VERBOSE_MODE", "STEAM_API_KEY", "WEBHOOK_URL", "SMTP_PASSWORD", "CLI_CONFIG_PATH", "DOTENV_FILE")
    snapshot = {name: getattr(monitor, name) for name in names}
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)


# Returns an HTTP error carrying the given status, the way requests raises one
def http_error(status_code, message="request failed"):
    response = req.Response()
    response.status_code = status_code
    return req.exceptions.HTTPError(message, response=response)


# Verifies the code set is closed, so a message cannot be invented outside the taxonomy
def test_an_unknown_recovery_code_is_refused():
    with pytest.raises(ValueError, match="Unsupported recovery code"):
        monitor.make_recovery_advice("steam.made_up", "summary", "fix", True)


# Verifies every code the classifier can produce is inside the declared set
@pytest.mark.parametrize("context", ["runtime", "config", "target", "email", "webhook", "file", "set_steam_api_key", "set_webhook_url"])
def test_the_classifier_only_produces_declared_codes(context):
    samples = [
        None, "", "timed out", "connection refused", "rate limit exceeded", "forbidden",
        "not found", "service unavailable", "private profile", "could not save",
        "interactive terminal", "cancelled", "does not exist", "must be discord",
        http_error(401), http_error(403), http_error(404), http_error(429), http_error(500), http_error(503),
        ValueError("Invalid Steam community URL"), TimeoutError("timed out"),
    ]
    for sample in samples:
        advice = monitor.classify_recovery_error(sample, context=context)
        assert advice.code in monitor.RECOVERY_CODES, (context, sample, advice.code)
        assert advice.summary, (context, sample)
        assert advice.fix, (context, sample)
        assert isinstance(advice.retryable, bool)


# Verifies a rate limit is classified as retryable so the loop waits rather than giving up
def test_a_rate_limit_is_retryable():
    advice = monitor.classify_recovery_error(http_error(429), context="runtime")

    assert advice.code == "steam.rate_limited"
    assert advice.retryable is True


# Verifies a rejected API key is not retryable, since retrying it can only fail again
def test_a_rejected_api_key_is_not_retryable():
    for error in (http_error(401), http_error(403)):
        advice = monitor.classify_recovery_error(error, context="runtime")

        assert advice.code == "auth.api_key_invalid"
        assert advice.retryable is False
        assert "--set-steam-api-key" in advice.fix


# Verifies a Steam outage is retryable, since it resolves without the user doing anything
def test_a_steam_outage_is_retryable():
    advice = monitor.classify_recovery_error(http_error(503), context="runtime")

    assert advice.code == "steam.unavailable"
    assert advice.retryable is True


# Verifies a timeout and a connection failure are separated, since they suggest different checks
def test_transport_failures_are_separated():
    assert monitor.classify_recovery_error(TimeoutError("request timed out"), context="runtime").code == "network.timeout"
    assert monitor.classify_recovery_error(req.exceptions.ConnectionError("name resolution failed"), context="runtime").code == "network.unavailable"


# Verifies a deleted account is reported as a target problem rather than as a transport failure
def test_a_missing_profile_is_a_target_problem():
    advice = monitor.classify_recovery_error(http_error(404), context="runtime")

    assert advice.code == "target.not_found"
    assert advice.retryable is False


# Verifies each context reaches its own family of codes rather than falling through to one generic answer
def test_each_context_reaches_its_own_codes():
    assert monitor.classify_recovery_error("syntax error", context="config").code == "config.invalid"
    assert monitor.classify_recovery_error("file does not exist", context="config").code == "config.missing"
    assert monitor.classify_recovery_error("authentication failed", context="email").code == "smtp.authentication"
    assert monitor.classify_recovery_error("could not be reached", context="webhook").code == "webhook.connection"
    assert monitor.classify_recovery_error("cannot load", context="file").code == "file.unreadable"
    assert monitor.classify_recovery_error("Invalid Steam community URL", context="target").code == "target.invalid"


# Verifies a fix line points at documentation the reader can open
def test_a_fix_carries_its_guide_link():
    advice = monitor.classify_recovery_error(http_error(403), context="runtime")

    assert "Guide: " in advice.fix
    assert monitor.DOCS_BASE_URL in advice.fix


# Verifies advice already classified is carried across an exception boundary unchanged
def test_advice_survives_an_exception_boundary():
    original = monitor.make_recovery_advice("network.timeout", "summary", "fix", True, "detail")
    cause = TimeoutError("underlying")

    error = monitor.RecoveryError(original, cause=cause)

    assert monitor.classify_recovery_error(error) is original
    assert error.__cause__ is cause
    assert str(error) == "summary"


# Verifies the rendered block is the shared Error and To fix shape, with technical detail held back
def test_the_rendered_block_hides_technical_detail_by_default(restored_globals):
    monitor.DEBUG_MODE = False

    rendered = monitor.render_recovery_error(http_error(403, "403 Client Error: Forbidden"), context="runtime")

    lines = rendered.splitlines()
    assert lines[0].startswith("* Error: ")
    assert any(line.startswith("To fix: ") for line in lines)
    assert "Technical detail:" not in rendered


# Verifies debug mode is what reveals the technical cause, and only that
def test_debug_mode_reveals_the_technical_detail(restored_globals):
    monitor.DEBUG_MODE = True

    rendered = monitor.render_recovery_error(http_error(403, "403 Client Error: Forbidden"), context="runtime")

    assert "Technical detail: " in rendered
    assert "403 Client Error" in rendered


# Verifies a secret reaching a failure message is redacted in every field of the advice
def test_a_secret_never_reaches_the_advice(restored_globals):
    monitor.STEAM_API_KEY = SECRET_API_KEY
    error = http_error(403, f"403 Forbidden for url: https://api.steampowered.com/x?key={SECRET_API_KEY}")

    advice = monitor.classify_recovery_error(error, context="runtime")
    rendered = monitor.render_recovery_error(error, context="runtime", debug=True)

    assert SECRET_API_KEY not in advice.summary
    assert SECRET_API_KEY not in advice.fix
    assert SECRET_API_KEY not in advice.detail
    assert SECRET_API_KEY not in rendered
    assert "<redacted>" in rendered


# Verifies malformed secret assignments cannot expose a value tail after whitespace
def test_malformed_config_redacts_the_complete_secret_value(tmp_path, capsys, restored_globals):
    config = tmp_path / "broken.conf"
    config.write_text('SMTP_PASSWORD = "top secret value\n', encoding="utf-8")

    assert monitor.load_config_file(config, namespace={}, report_errors=True) is False

    output = capsys.readouterr().out
    assert "top" not in output
    assert "secret value" not in output
    assert "SMTP_PASSWORD = <redacted>" in output


# Verifies the fix is rendered whenever this printer runs, since its caller only reaches it on a new failure
# category and the throttling of a lasting outage is the outage reporter's job rather than a second guard's
def test_the_printed_failure_carries_its_fix(capsys, restored_globals):
    monitor.DEBUG_MODE = False

    monitor.print_monitor_recovery(http_error(503), "runtime", "retrying in 5 minutes")

    output = capsys.readouterr().out
    assert output.startswith("* Error: The Steam Web API is temporarily unavailable (retrying in 5 minutes)\n")
    assert output.count("To fix: ") == 1


# Verifies no user-facing error is printed outside the classifier, which a runtime test cannot prove
def test_no_error_is_printed_outside_the_classifier():
    source = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
    allowed_line_markers = (
        "MINIMUM_PYTHON_VERSION_TEXT",  # Runs before the classifier and its dependencies are importable
        "Could not back up the existing config file",  # Runs before argument parsing, inside --generate-config
        "Error writing profile CSV",  # Per-row CSV warning that must not abort the monitoring cycle
        "Config files are read as data",  # The explanatory line printed above the classified config error
    )
    offenders = []
    for number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or "print_recovery_error" in stripped or "print_monitor_recovery" in stripped:
            continue
        if any(marker in stripped for marker in ('print(f"* Error', 'print("* Error', 'print(f"Error', 'print("Error')):
            if not any(marker in stripped for marker in allowed_line_markers):
                offenders.append(f"{number}: {stripped}")

    assert not offenders, "errors printed without recovery advice:\n" + "\n".join(offenders)


# Applies a usable mail server, so a test that breaks one setting is not also broken by the others
def configure_smtp(monkeypatch):
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_USER", "sender")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "not-a-real-password")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.com")


@pytest.mark.parametrize("setting, value", [
    ("SMTP_HOST", "not a host"),
    ("SMTP_PORT", "not a port"),
    ("SENDER_EMAIL", "not-an-email"),
    ("SMTP_PASSWORD", ""),
])
# Verifies a refused setting names the fix and the guide, so no delivery path reports without saying what to do
def test_a_refused_smtp_setting_carries_the_shared_error_block(capsys, monkeypatch, setting, value):
    configure_smtp(monkeypatch)
    monkeypatch.setattr(monitor, setting, value)

    assert monitor.send_email("subject", "body", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert "* Error: The SMTP settings are incorrect (" in output
    assert "To fix: Check SMTP_HOST, SMTP_PORT, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file" in output
    assert f"Guide: {monitor.SMTP_GUIDE_URL}" in output


# Verifies a message the tool cannot send carries the same block as an unusable setting
def test_an_unsendable_message_carries_the_shared_error_block(capsys, monkeypatch):
    configure_smtp(monkeypatch)

    assert monitor.send_email("", "body", "", True, smtp_timeout=1) == 1
    assert monitor.send_email("subject", "", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert output.count("* Error: The SMTP settings are incorrect (") == 2
    assert output.count(f"Guide: {monitor.SMTP_GUIDE_URL}") == 2


# Verifies a mail server that refuses the session is reported with the fix rather than as a bare line
def test_a_refused_smtp_session_carries_the_shared_error_block(capsys, monkeypatch):
    configure_smtp(monkeypatch)
    monkeypatch.setattr(monitor.smtplib, "SMTP", Mock(side_effect=OSError("connection refused")))

    assert monitor.send_email("subject", "body", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert "* Error: The SMTP server could not be reached" in output
    assert f"Guide: {monitor.SMTP_GUIDE_URL}" in output


# Verifies a refused webhook delivery carries the fix and the guide the email failures carry
def test_a_refused_webhook_delivery_carries_the_shared_error_block(capsys, monkeypatch, restored_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")
    monkeypatch.setattr(monitor, "post_webhook_request", Mock(return_value=http_error(404).response))

    assert monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None) == 1

    output = capsys.readouterr().out
    assert "* Error: The webhook service returned HTTP 404" in output
    assert "To fix: " in output
    assert f"Guide: {monitor.WEBHOOK_GUIDE_URL}" in output


# Verifies an unusable webhook setting is refused with the same block, so configuration and delivery read alike
def test_an_unusable_webhook_setting_carries_the_shared_error_block(capsys, monkeypatch, restored_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "carrier pigeon")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")

    assert monitor.send_webhook("title", "body", "status", force=True) == 1

    output = capsys.readouterr().out
    assert "* Error: WEBHOOK_PROVIDER must be discord or ntfy" in output
    assert f"Guide: {monitor.WEBHOOK_GUIDE_URL}" in output


# Verifies no delivery path prints at all, since a print there is an error line that skipped the recovery block
def test_no_delivery_path_prints_outside_the_recovery_block():
    source = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
    delivery = {"send_email", "send_webhook", "print_webhook_error", "smtp_connect_and_login", "post_webhook_request"}
    offenders = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef) or node.name not in delivery:
            continue
        offenders.extend(f"{node.name}:{call.lineno}" for call in ast.walk(node) if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "print")

    assert not offenders, "delivery paths printing outside the recovery block: " + ", ".join(offenders)


# Verifies the refusal to replace an existing file points at the section describing that file
def test_the_existing_file_refusal_points_at_the_configuration_file_section():
    advice = monitor.classify_recovery_error(context="file.exists")

    assert advice.code == "file.exists"
    assert f"Guide: {monitor.CONFIG_FILE_GUIDE_URL}" in advice.fix
    assert advice.fix.rstrip().endswith("#configuration-file")


# Verifies the missing-target advice names the accepted forms and a command carrying the paths this run was given
def test_a_missing_target_advises_the_accepted_forms(restored_globals):
    monitor.CLI_CONFIG_PATH = "/tmp/steam_monitor.conf"
    monitor.DOTENV_FILE = "/tmp/steam_monitor.env"

    advice = monitor.classify_recovery_error(context="target.missing")

    assert advice.code == "target.missing"
    # The summary follows the shape every sibling uses for a target it was never given
    assert advice.summary == "No Steam profile was provided"
    assert monitor.STEAM_TARGET_FORMS in advice.fix
    assert "--config-file /tmp/steam_monitor.conf" in advice.fix
    assert "--env-file /tmp/steam_monitor.env" in advice.fix
    assert f"Guide: {monitor.QUICK_START_GUIDE_URL}" in advice.fix


# Verifies the startup gate can restate the missing target in its own words without losing the shared fix
def test_a_missing_target_keeps_the_shared_fix_under_its_own_summary(restored_globals):
    monitor.CLI_CONFIG_PATH = ""
    monitor.DOTENV_FILE = ""

    advice = monitor.classify_recovery_error(context="target.missing", detail="A Steam profile target needs to be defined")

    assert advice.code == "target.missing"
    assert advice.summary == "A Steam profile target needs to be defined"
    assert advice.fix == monitor.classify_recovery_error(context="target.missing").fix


# Verifies a write the tool reports as a file problem is classified as unwritable rather than left unknown
def test_a_failed_file_write_is_classified_as_unwritable(restored_globals):
    advice = monitor.classify_recovery_error(PermissionError(13, "Permission denied"), context="file", detail="Cannot save games library to '/x/games.json'")

    assert advice.code == "file.unwritable"
    assert advice.fix == "Check that the directory exists and is writable, or choose another path"


# Verifies a profile CSV row that cannot be written carries the same fix as every other unwritable file
def test_a_failed_profile_csv_write_carries_the_shared_fix(restored_globals, capsys):
    monitor.print_recovery_error(RuntimeError("Failed to write to profile CSV file '/x/p.csv': [Errno 2] No such file or directory"), context="file.unwritable")

    printed = capsys.readouterr().out
    assert printed.startswith("* Error: Failed to write to profile CSV file '/x/p.csv'")
    assert "To fix: Check that the directory exists and is writable, or choose another path" in printed


# Verifies a failed CSV write reports through the recovery block, since the monitoring loop carries on past it
def test_no_csv_write_failure_prints_its_own_line():
    csv_writers = {"init_csv_file", "init_profile_csv_file", "write_csv_entry", "write_profile_csv_entry"}
    offenders = []
    guarded = 0
    for node in ast.walk(ast.parse(Path(monitor.__file__).read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Try) or (node.body[-1].end_lineno or node.body[0].lineno) - node.body[0].lineno > 6:
            continue
        if not any(isinstance(inner, ast.Call) and getattr(inner.func, "id", "") in csv_writers for statement in node.body for inner in ast.walk(statement)):
            continue
        guarded += 1
        offenders.extend(f"line {statement.lineno}" for handler in node.handlers for statement in handler.body if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and getattr(statement.value.func, "id", "") == "print")

    assert guarded >= 11, f"only {guarded} CSV writes are guarded, so this no longer covers them"
    assert not offenders, "CSV write failures reported outside the recovery block:\n" + "\n".join(offenders)
