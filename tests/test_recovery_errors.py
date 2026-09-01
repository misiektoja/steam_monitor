"""Tests that every failure carries a stable code, an actionable fix, and no secrets."""

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


# Verifies a repeated failure prints its hint once rather than on every cycle of a long outage
def test_a_repeated_failure_prints_one_hint(capsys, restored_globals):
    monitor.DEBUG_MODE = False
    tracker = monitor.RecoveryHintTracker()

    for _ in range(50):
        monitor.print_monitor_recovery(http_error(503), "runtime", tracker, "retrying in 5 minutes")

    output = capsys.readouterr().out
    assert output.count("To fix: ") == 1
    assert output.count("* Error: The Steam Web API is temporarily unavailable (retrying in 5 minutes)") == 50


# Verifies a changed failure category prints its own hint, since the fix is now a different one
def test_a_changed_failure_category_prints_its_hint(capsys, restored_globals):
    monitor.DEBUG_MODE = False
    tracker = monitor.RecoveryHintTracker()

    monitor.print_monitor_recovery(http_error(503), "runtime", tracker, "retrying in 5 minutes")
    monitor.print_monitor_recovery(http_error(503), "runtime", tracker, "retrying in 5 minutes")
    monitor.print_monitor_recovery(http_error(403), "runtime", tracker, "retrying in 5 minutes")

    assert capsys.readouterr().out.count("To fix: ") == 2


# Verifies a successful cycle clears suppression, so a recurrence is explained again
def test_a_successful_cycle_clears_suppression(capsys, restored_globals):
    monitor.DEBUG_MODE = False
    tracker = monitor.RecoveryHintTracker()

    monitor.print_monitor_recovery(http_error(503), "runtime", tracker, "retrying in 5 minutes")
    tracker.reset()
    monitor.print_monitor_recovery(http_error(503), "runtime", tracker, "retrying in 5 minutes")

    assert capsys.readouterr().out.count("To fix: ") == 2


# Verifies no user-facing error is printed outside the classifier, which a runtime test cannot prove
def test_no_error_is_printed_outside_the_classifier():
    from pathlib import Path

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
        if 'print(f"* Error' in stripped or 'print("* Error' in stripped:
            if not any(marker in stripped for marker in allowed_line_markers):
                offenders.append(f"{number}: {stripped}")

    assert not offenders, "errors printed without recovery advice:\n" + "\n".join(offenders)


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
