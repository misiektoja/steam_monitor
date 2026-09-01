"""Tests that verbose and debug modes explain the runtime paths without disclosing secrets."""

import re

import pytest
import requests as req

import steam_monitor as monitor


SECRET_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/verysecrettokenvalue"
SECRET_SMTP_PASSWORD = "super-secret-smtp-password"


@pytest.fixture
# Restores the module-level settings each test writes, since the whole suite shares one imported module
def restored_globals():
    names = (
        "DEBUG_MODE", "VERBOSE_MODE", "WEBHOOK_URL", "WEBHOOK_PROVIDER", "WEBHOOK_ENABLED",
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_SSL", "SENDER_EMAIL", "RECEIVER_EMAIL",
        "WEBHOOK_TEMPLATE", "WEBHOOK_HEADERS", "WEBHOOK_TRANSFORMS", "NTFY_IMAGES",
    )
    snapshot = {name: getattr(monitor, name) for name in names}
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)


@pytest.fixture
# Turns both diagnostic modes on for the duration of one test
def diagnostics_on(restored_globals):
    monitor.DEBUG_MODE = True
    monitor.VERBOSE_MODE = True


# Points the webhook settings at a destination that never gets contacted
def configure_webhook():
    monitor.WEBHOOK_URL = SECRET_WEBHOOK_URL
    monitor.WEBHOOK_PROVIDER = "discord"
    monitor.WEBHOOK_ENABLED = True
    monitor.WEBHOOK_TEMPLATE = {}
    monitor.WEBHOOK_HEADERS = {}
    monitor.WEBHOOK_TRANSFORMS = []
    monitor.NTFY_IMAGES = False


# Points the SMTP settings at a host that never gets contacted
def configure_smtp():
    monitor.SMTP_HOST = "smtp.example.com"
    monitor.SMTP_PORT = 587
    monitor.SMTP_USER = "sender"
    monitor.SMTP_PASSWORD = SECRET_SMTP_PASSWORD
    monitor.SMTP_SSL = True
    monitor.SENDER_EMAIL = "sender@example.com"
    monitor.RECEIVER_EMAIL = "receiver@example.com"


# Returns a fake webhook response with the given status code
def webhook_response(status_code, headers=None):
    class Response:
        def __init__(self):
            self.status_code = status_code
            self.headers = headers or {}

        def json(self):
            return {}

    return Response()


# Verifies neither printer emits anything while both modes are off
def test_diagnostic_printers_stay_silent_when_disabled(capsys, restored_globals):
    monitor.DEBUG_MODE = False
    monitor.VERBOSE_MODE = False

    monitor.debug_print("hidden debug line")
    monitor.verbose_print("hidden verbose line")
    monitor.debug_swallowed_exception("hidden context", ValueError("hidden cause"))

    assert capsys.readouterr().out == ""


# Verifies the two modes stay independent, matching the sibling tools so a user reads one behaviour everywhere
def test_debug_and_verbose_are_independent(capsys, restored_globals):
    monitor.DEBUG_MODE = True
    monitor.VERBOSE_MODE = False
    monitor.verbose_print("verbose line")
    monitor.debug_print("debug line")

    output = capsys.readouterr().out
    assert "verbose line" not in output
    assert "debug line" in output

    monitor.DEBUG_MODE = False
    monitor.VERBOSE_MODE = True
    monitor.verbose_print("verbose line")
    monitor.debug_print("debug line")

    output = capsys.readouterr().out
    assert "verbose line" in output
    assert "debug line" not in output


# Verifies the full startup summary still appears under either mode, which is where the two do overlap
def test_the_full_startup_summary_appears_under_either_mode(restored_globals):
    monitor.DEBUG_MODE = True
    monitor.VERBOSE_MODE = False
    assert monitor.full_startup_summary_enabled() is True

    monitor.DEBUG_MODE = False
    monitor.VERBOSE_MODE = True
    assert monitor.full_startup_summary_enabled() is True

    monitor.DEBUG_MODE = False
    monitor.VERBOSE_MODE = False
    assert monitor.full_startup_summary_enabled() is False


# Verifies every debug line carries a timestamp and the shared prefix used by the sibling tools
def test_debug_lines_are_timestamped(capsys, diagnostics_on):
    monitor.debug_print("a traced step")

    output = capsys.readouterr().out
    assert re.match(r"^\[DEBUG \d{2}:\d{2}:\d{2}\] a traced step\n$", output), output


# Verifies a secret interpolated by any caller is redacted inside the printer rather than at the call site
def test_a_secret_interpolated_into_a_debug_line_is_redacted(capsys, restored_globals):
    monitor.DEBUG_MODE = True
    monitor.SMTP_PASSWORD = SECRET_SMTP_PASSWORD

    monitor.debug_print(f"careless caller leaked {SECRET_SMTP_PASSWORD}")

    output = capsys.readouterr().out
    assert SECRET_SMTP_PASSWORD not in output
    assert "<redacted>" in output


# Verifies the same protection covers the verbose printer, which callers reach just as easily
def test_a_secret_interpolated_into_a_verbose_line_is_redacted(capsys, restored_globals):
    monitor.VERBOSE_MODE = True
    monitor.WEBHOOK_URL = SECRET_WEBHOOK_URL

    monitor.verbose_print(f"careless caller leaked {SECRET_WEBHOOK_URL}")

    output = capsys.readouterr().out
    assert SECRET_WEBHOOK_URL not in output
    assert "<redacted>" in output


# Verifies debug output is silenced while a raw secret is handled, then restored afterwards
def test_debug_output_is_suppressed_around_a_raw_secret(capsys, restored_globals):
    monitor.DEBUG_MODE = True

    with monitor.debug_output_suppressed():
        monitor.debug_print("must not appear")
        assert monitor.DEBUG_MODE is False

    monitor.debug_print("must appear again")

    output = capsys.readouterr().out
    assert "must not appear" not in output
    assert "must appear again" in output
    assert monitor.DEBUG_MODE is True


# Verifies the suppression is restored even when the guarded operation raises
def test_debug_suppression_survives_an_exception(restored_globals):
    monitor.DEBUG_MODE = True

    with pytest.raises(ValueError):
        with monitor.debug_output_suppressed():
            raise ValueError("cancelled")

    assert monitor.DEBUG_MODE is True


# Verifies the Steam API key entry path cannot emit debug output while the pasted value is in hand
def test_the_api_key_entry_path_emits_no_debug_output(capsys, monkeypatch, restored_globals):
    monitor.DEBUG_MODE = True
    observed = {}

    def record_and_reject(api_key, timeout=10):
        observed["debug_during_entry"] = monitor.DEBUG_MODE
        monitor.debug_print(f"validating {api_key}")
        return False

    with pytest.raises(monitor.SecretConfigurationError):
        monitor.run_set_steam_api_key(
            env_file="/dev/null",
            interactive=True,
            input_func=lambda _prompt: "y",
            getpass_func=lambda _prompt: "PASTED-SECRET-KEY",
            validator=record_and_reject,
        )

    assert observed["debug_during_entry"] is False
    assert "PASTED-SECRET-KEY" not in capsys.readouterr().out
    assert monitor.DEBUG_MODE is True


# Verifies a swallowed exception is named together with the operation it broke
def test_a_swallowed_exception_names_its_operation(capsys, diagnostics_on):
    monitor.debug_swallowed_exception("Fetching the Steam level (IPlayerService.GetSteamLevel)", TimeoutError("timed out"))

    output = capsys.readouterr().out
    assert "Fetching the Steam level (IPlayerService.GetSteamLevel)" in output
    assert "TimeoutError" in output
    assert "timed out" in output


# Verifies the failing email path names the SMTP target and the technical cause
def test_email_failure_is_explained_in_debug(capsys, monkeypatch, diagnostics_on):
    configure_smtp()

    def refuse_connection(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(monitor.smtplib, "SMTP", refuse_connection)

    assert monitor.send_email("subject", "body", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert "host=smtp.example.com, port=587" in output
    assert "Sending email: outcome=failed, error=OSError" in output


# Verifies a delivered email is confirmed rather than only announced before the attempt
def test_a_delivered_email_is_confirmed_in_verbose(capsys, monkeypatch, diagnostics_on):
    configure_smtp()

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs):
            pass

        def starttls(self, **_kwargs):
            pass

        def login(self, *_args):
            pass

        def sendmail(self, *_args):
            pass

        def quit(self):
            pass

    monkeypatch.setattr(monitor.smtplib, "SMTP", FakeSMTP)

    assert monitor.send_email("subject", "body", "", True, smtp_timeout=1) == 0
    assert "Email delivered to receiver@example.com" in capsys.readouterr().out


# Verifies every webhook attempt, status code and retry delay is visible in debug
def test_webhook_retries_are_explained_in_debug(capsys, monkeypatch, diagnostics_on):
    configure_webhook()
    monkeypatch.setattr(monitor, "post_webhook_request", lambda **_kwargs: webhook_response(500))

    assert monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None) == 1

    output = capsys.readouterr().out
    assert "Webhook delivery: channel=discord, attempt=1/2" in output
    assert "Webhook delivery: channel=discord, attempt=2/2" in output
    assert "status=500, retryable=True" in output
    assert "Webhook delivery: channel=discord, retry_in=" in output


# Verifies a rejected webhook that cannot be retried says so instead of implying another attempt
def test_a_non_retryable_webhook_status_is_reported_as_such(capsys, monkeypatch, diagnostics_on):
    configure_webhook()
    monkeypatch.setattr(monitor, "post_webhook_request", lambda **_kwargs: webhook_response(404))

    assert monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None) == 1

    output = capsys.readouterr().out
    assert "status=404, retryable=False" in output
    assert "attempt=2/2" not in output


# Verifies a delivered webhook is confirmed with the provider that accepted it
def test_a_delivered_webhook_is_confirmed_in_verbose(capsys, monkeypatch, diagnostics_on):
    configure_webhook()
    monkeypatch.setattr(monitor, "post_webhook_request", lambda **_kwargs: webhook_response(204))

    assert monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None) == 0
    assert "Webhook delivered through discord (HTTP 204)" in capsys.readouterr().out


# Verifies an unreachable webhook service names the transport failure
def test_an_unreachable_webhook_service_is_explained(capsys, monkeypatch, diagnostics_on):
    configure_webhook()

    def refuse_request(**_kwargs):
        raise req.exceptions.ConnectTimeout("connect timed out")

    monkeypatch.setattr(monitor, "post_webhook_request", refuse_request)

    assert monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None) == 1
    assert "Webhook request: outcome=failed, error=ConnectTimeout" in capsys.readouterr().out


# Verifies each channel's outcome is reported separately, which the dispatcher previously discarded
def test_each_notification_channel_reports_its_own_outcome(capsys, monkeypatch, diagnostics_on):
    configure_smtp()
    configure_webhook()
    monkeypatch.setattr(monitor, "send_email", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(monitor, "send_webhook", lambda *_args, **_kwargs: 0)

    # The return is per-channel delivery, so the failed email reports False while the webhook reports True
    assert monitor.send_notification_channels("error", "subject", "body", email_enabled=True, webhook_enabled=True) == (False, True)

    output = capsys.readouterr().out
    assert "Email channel: event=error, outcome=failed" in output
    assert "Webhook channel: event=error, outcome=OK" in output


# Verifies a persona name history that could not be fetched is distinguishable from a user who never renamed
def test_a_failed_name_history_fetch_is_named(capsys, monkeypatch, diagnostics_on):
    def refuse_request(*_args, **_kwargs):
        raise req.exceptions.HTTPError("403 Forbidden")

    monkeypatch.setattr(monitor.req, "get", refuse_request)

    assert monitor.fetch_persona_name_history(76561197960435530) == []
    assert "Fetching the persona name history: outcome=failed, error=HTTPError" in capsys.readouterr().out


# Verifies the webhook destination is traced by host alone, never by the private URL
def test_the_webhook_destination_is_traced_by_host_only(capsys, monkeypatch, diagnostics_on):
    configure_webhook()
    monkeypatch.setattr(monitor, "post_webhook_request", lambda **_kwargs: webhook_response(204))

    monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None)

    output = capsys.readouterr().out
    assert monitor.webhook_destination_host() == "discord.com"
    assert "host=discord.com" in output
    assert "verysecrettokenvalue" not in output
    assert SECRET_WEBHOOK_URL not in output


# Verifies an unset or malformed webhook destination is described rather than raising
def test_an_unusable_webhook_destination_is_described(restored_globals):
    monitor.WEBHOOK_URL = ""

    assert monitor.webhook_destination_host() == "unknown host"


# Verifies a secret that reaches an error message is redacted before it is printed
def test_a_secret_in_an_error_message_is_redacted(capsys, monkeypatch, diagnostics_on):
    configure_smtp()

    def leak_the_password(*_args, **_kwargs):
        raise OSError(f"auth failed for password {SECRET_SMTP_PASSWORD}")

    monkeypatch.setattr(monitor.smtplib, "SMTP", leak_the_password)

    assert monitor.send_email("subject", "body", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert SECRET_SMTP_PASSWORD not in output
    assert "<redacted>" in output


# Verifies the configured TLS setting reaches every outbound request rather than only some of them
def test_tls_verification_reaches_every_outbound_request(monkeypatch, restored_globals):
    monkeypatch.setattr(monitor, "VERIFY_SSL", False)
    configure_webhook()
    observed = []

    def record_get(*_args, **kwargs):
        observed.append(("get", kwargs.get("verify")))
        raise req.exceptions.ConnectionError("stopped")

    def record_post(*_args, **kwargs):
        observed.append(("post", kwargs.get("verify")))
        raise req.exceptions.ConnectionError("stopped")

    monkeypatch.setattr(monitor.req, "get", record_get)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "get", record_get)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", record_post)

    # Each call is expected to fail, since the point is only to capture the verify argument it sent
    for outbound_call in (
        lambda: monitor.check_internet("https://example.invalid/probe", 1),
        lambda: monitor.fetch_persona_name_history(76561197960435530),
        lambda: monitor.validate_steam_api_key("A" * 32),
        lambda: monitor.resolve_steam_community_url("https://steamcommunity.com/id/someone/", "A" * 32),
        lambda: monitor.send_webhook("t", "b", "status", force=True, sleeper=lambda _seconds: None),
    ):
        try:
            outbound_call()
        except Exception:
            pass

    # Pinned so the test cannot quietly degrade to proving one call site instead of all of them
    assert len(observed) >= 5, observed
    assert all(verify is False for _kind, verify in observed), observed


# Verifies the Steam Web API client applies the TLS setting before it issues its first request
def test_the_steam_client_applies_tls_before_its_first_request(monkeypatch, restored_globals):
    monkeypatch.setattr(monitor, "VERIFY_SSL", False)
    order = []

    class FakeSession:
        def __init__(self):
            self._verify = True

        @property
        def verify(self):
            return self._verify

        @verify.setter
        def verify(self, value):
            order.append(("verify_set", value))
            self._verify = value

    class FakeWebAPI:
        def __init__(self, key, auto_load_interfaces=True):
            order.append(("constructed", auto_load_interfaces))
            self.session = FakeSession()

        def fetch_interfaces(self):
            order.append(("fetch_interfaces", self.session.verify))
            return {}

        def load_interfaces(self, _interfaces):
            order.append(("load_interfaces", None))

    monkeypatch.setattr(monitor.steam.webapi, "WebAPI", FakeWebAPI)

    monitor.steam_web_api_client("A" * 32)

    assert order[0] == ("constructed", False)
    assert order[1] == ("verify_set", False)
    # The interface fetch is the client's first network call, so it must already be running with the setting applied
    assert order[2] == ("fetch_interfaces", False)


# Verifies a channel that failed is reported as undelivered so the caller can retry only that one
def test_a_failed_channel_is_reported_as_undelivered(monkeypatch, diagnostics_on):
    configure_smtp()
    configure_webhook()
    monkeypatch.setattr(monitor, "send_email", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(monitor, "send_webhook", lambda *_args, **_kwargs: 0)

    assert monitor.send_notification_channels("error", "s", "b", email_enabled=True, webhook_enabled=True) == (False, True)


# Verifies a channel that was never enabled is reported as undelivered rather than as a success
def test_a_disabled_channel_is_not_reported_as_delivered(monkeypatch, restored_globals):
    monkeypatch.setattr(monitor, "send_email", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(monitor, "send_webhook", lambda *_args, **_kwargs: 0)

    assert monitor.send_notification_channels("error", "s", "b", email_enabled=False, webhook_enabled=False) == (False, False)


# Verifies the connectivity check explains what it probed and why it failed
def test_the_connectivity_check_is_explained(capsys, monkeypatch, diagnostics_on):
    def refuse_request(*_args, **_kwargs):
        raise req.exceptions.ConnectionError("name resolution failed")

    monkeypatch.setattr(monitor.req, "get", refuse_request)

    assert monitor.check_internet("https://example.invalid/probe", 3) is False

    output = capsys.readouterr().out
    assert "Connectivity check: url=https://example.invalid/probe, timeout=3s" in output
    # The failure itself is now reported as structured recovery advice rather than a raw exception
    assert "* Error: Steam could not be reached" in output
    assert "To fix: Check connectivity, DNS and any proxy" in output
    assert "Technical detail: " in output


# Verifies a successful connectivity check reports its outcome rather than only its intent
def test_a_successful_connectivity_check_reports_its_outcome(capsys, monkeypatch, diagnostics_on):
    monkeypatch.setattr(monitor.req, "get", lambda *_args, **_kwargs: None)

    assert monitor.check_internet("https://example.test/probe", 3) is True

    output = capsys.readouterr().out
    assert "Connectivity check: url=https://example.test/probe, timeout=3s" in output
    assert "Connectivity check: url=https://example.test/probe, outcome=OK" in output


# Verifies a failing connectivity check names the transport failure in debug, which quiet callers otherwise swallow
def test_a_failing_connectivity_check_reports_its_outcome_even_when_quiet(capsys, monkeypatch, diagnostics_on):
    def refuse_request(*_args, **_kwargs):
        raise req.exceptions.ConnectionError("name resolution failed")

    monkeypatch.setattr(monitor.req, "get", refuse_request)

    assert monitor.check_internet("https://example.invalid/probe", 3, quiet=True) is False

    output = capsys.readouterr().out
    assert "Connectivity check: url=https://example.invalid/probe, outcome=failed, error=ConnectionError" in output
    # A quiet caller renders the failure itself, so the structured advice must stay off the progress line
    assert "* Error: Steam could not be reached" not in output


# Verifies a delivered email confirms the SMTP outcome in debug, not only in verbose
def test_a_delivered_email_reports_its_smtp_outcome_in_debug(capsys, monkeypatch, restored_globals):
    monitor.DEBUG_MODE = True
    monitor.VERBOSE_MODE = False
    configure_smtp()

    class AcceptingSMTP:
        def sendmail(self, *_args, **_kwargs):
            return {}

        def quit(self):
            return None

    monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda *_args, **_kwargs: AcceptingSMTP())

    assert monitor.send_email("subject", "body", "", True) == 0

    output = capsys.readouterr().out
    assert "SMTP delivery: host=smtp.example.com, port=587" in output
    assert "SMTP delivery: host=smtp.example.com, port=587, recipient=receiver@example.com, outcome=OK" in output
    assert SECRET_SMTP_PASSWORD not in output

