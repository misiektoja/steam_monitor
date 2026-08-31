"""Tests that verbose and debug modes explain the runtime paths without disclosing secrets."""

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

    monitor.print_debug("hidden debug line")
    monitor.print_verbose("hidden verbose line")
    monitor.print_debug_exception("hidden context", ValueError("hidden cause"))

    assert capsys.readouterr().out == ""


# Verifies debug mode implies verbose, so a single flag is enough to see everything
def test_debug_mode_implies_verbose(capsys, restored_globals):
    monitor.DEBUG_MODE = True
    monitor.VERBOSE_MODE = False

    monitor.print_verbose("visible verbose line")

    assert "visible verbose line" in capsys.readouterr().out
    assert monitor.verbose_enabled() is True


# Verifies a swallowed exception is named together with the operation it broke
def test_a_swallowed_exception_names_its_operation(capsys, diagnostics_on):
    monitor.print_debug_exception("Fetching the Steam level (IPlayerService.GetSteamLevel)", TimeoutError("timed out"))

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
    assert "smtp.example.com:587" in output
    assert "Sending email failed with OSError" in output


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
    assert "Webhook attempt 1/2" in output
    assert "Webhook attempt 2/2" in output
    assert "HTTP 500 (retryable: True)" in output
    assert "Retrying the webhook in" in output


# Verifies a rejected webhook that cannot be retried says so instead of implying another attempt
def test_a_non_retryable_webhook_status_is_reported_as_such(capsys, monkeypatch, diagnostics_on):
    configure_webhook()
    monkeypatch.setattr(monitor, "post_webhook_request", lambda **_kwargs: webhook_response(404))

    assert monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None) == 1

    output = capsys.readouterr().out
    assert "HTTP 404 (retryable: False)" in output
    assert "Webhook attempt 2/2" not in output


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
    assert "Webhook request failed with ConnectTimeout" in capsys.readouterr().out


# Verifies each channel's outcome is reported separately, which the dispatcher previously discarded
def test_each_notification_channel_reports_its_own_outcome(capsys, monkeypatch, diagnostics_on):
    configure_smtp()
    configure_webhook()
    monkeypatch.setattr(monitor, "send_email", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(monitor, "send_webhook", lambda *_args, **_kwargs: 0)

    assert monitor.send_notification_channels("error", "subject", "body", email_enabled=True, webhook_enabled=True) == (True, True)

    output = capsys.readouterr().out
    assert "Email channel for the error alert failed" in output
    assert "Webhook channel for the error alert succeeded" in output


# Verifies a persona name history that could not be fetched is distinguishable from a user who never renamed
def test_a_failed_name_history_fetch_is_named(capsys, monkeypatch, diagnostics_on):
    def refuse_request(*_args, **_kwargs):
        raise req.exceptions.HTTPError("403 Forbidden")

    monkeypatch.setattr(monitor.req, "get", refuse_request)

    assert monitor.fetch_persona_name_history(76561197960435530) == []
    assert "Fetching the persona name history failed with HTTPError" in capsys.readouterr().out


# Verifies the webhook destination is traced by host alone, never by the private URL
def test_the_webhook_destination_is_traced_by_host_only(capsys, monkeypatch, diagnostics_on):
    configure_webhook()
    monkeypatch.setattr(monitor, "post_webhook_request", lambda **_kwargs: webhook_response(204))

    monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None)

    output = capsys.readouterr().out
    assert monitor.webhook_destination_host() == "discord.com"
    assert "to discord.com" in output
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


# Verifies the connectivity check explains what it probed and why it failed
def test_the_connectivity_check_is_explained(capsys, monkeypatch, diagnostics_on):
    def refuse_request(*_args, **_kwargs):
        raise req.exceptions.ConnectionError("name resolution failed")

    monkeypatch.setattr(monitor.req, "get", refuse_request)

    assert monitor.check_internet("https://example.invalid/probe", 3) is False

    output = capsys.readouterr().out
    assert "Checking connectivity against https://example.invalid/probe with a 3s timeout" in output
    assert "Connectivity check failed with ConnectionError" in output
