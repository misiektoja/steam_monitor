"""Tests for VERIFY_SSL: which requests honor it, what is reported while it is off and its shipped default."""

import ast
import ssl
from pathlib import Path
from types import SimpleNamespace

import pytest

import steam_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "steam_monitor.py").read_text(encoding="utf-8")
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"
API_KEY = "0123456789ABCDEF0123456789ABCDEF"


# Records the keyword arguments of every request made through it and answers with a success the caller accepts
class RecordingRequests:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = {"response": {"players": []}} if payload is None else payload

    # Stands in for both requests.get and Session.post, which the tool calls with keyword arguments only
    def __call__(self, url=None, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return SimpleNamespace(status_code=200, headers={}, text="", reason="OK", json=lambda: self.payload)

    # Returns the TLS setting the single recorded request carried
    def verified(self):
        assert len(self.calls) == 1, f"expected one request, recorded {len(self.calls)}"
        return self.calls[0].get("verify")


@pytest.fixture
# Returns a recorder installed over every outbound request the tool can make
def outbound(monkeypatch):
    recorder = RecordingRequests()
    monkeypatch.setattr(monitor.req, "get", recorder)
    monkeypatch.setattr(monitor, "WEBHOOK_SESSION", SimpleNamespace(post=recorder))
    monkeypatch.setattr(monitor, "WEBHOOK_URL", WEBHOOK_URL)
    return recorder


@pytest.fixture
# Restores the setting after each test, since it is a module global the whole tool reads
def tls_setting(monkeypatch):
    monkeypatch.setattr(monitor, "VERIFY_SSL", monitor.VERIFY_SSL)
    return monkeypatch


@pytest.mark.parametrize("verify", [True, False])
# Verifies the connectivity check carries the configured setting rather than the requests library default
def test_the_connectivity_check_honors_the_setting(tls_setting, outbound, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)

    assert monitor.check_internet("https://steam.example/probe", 5, quiet=True) is True
    assert outbound.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies the key check carries the setting, since it reaches Steam outside the Web API client session
def test_the_api_key_check_honors_the_setting(tls_setting, outbound, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)

    assert monitor.validate_steam_api_key(API_KEY) is True
    assert outbound.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies the vanity name resolver carries the setting, which is the other request made before monitoring starts
def test_the_vanity_resolver_honors_the_setting(tls_setting, monkeypatch, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)
    recorder = RecordingRequests({"response": {"success": 1, "steamid": "76561197960435530"}})
    monkeypatch.setattr(monitor.req, "get", recorder)

    assert monitor.resolve_steam_community_url("https://steamcommunity.com/id/example/", API_KEY) == 76561197960435530
    assert recorder.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies webhook deliveries carry the setting, so one channel cannot skip a check the others make
def test_the_webhook_delivery_honors_the_setting(tls_setting, outbound, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)

    monitor.post_webhook_request(json={"content": "hello"})

    assert outbound.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies the Web API session is configured before the interfaces are fetched, which is its first request
def test_the_steam_web_api_session_honors_the_setting(tls_setting, monkeypatch, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)
    order = []

    class FakeWebAPI:
        def __init__(self, key=None, auto_load_interfaces=True):
            self.session = SimpleNamespace(verify=True)

        def fetch_interfaces(self):
            order.append(self.session.verify)
            return []

        def load_interfaces(self, interfaces):
            pass

    monkeypatch.setattr(monitor.steam.webapi, "WebAPI", FakeWebAPI)

    assert monitor.steam_web_api_client(API_KEY).session.verify is verify
    assert order == [verify], "the interfaces were fetched before the session was configured"


# Verifies a steam release that moves its session still returns a usable client instead of failing to start
def test_a_client_without_the_expected_session_still_starts(tls_setting, monkeypatch):
    tls_setting.setattr(monitor, "VERIFY_SSL", False)

    class SessionlessWebAPI:
        def __init__(self, key=None, auto_load_interfaces=True):
            self.key = key

        def fetch_interfaces(self):
            return []

        def load_interfaces(self, interfaces):
            pass

    monkeypatch.setattr(monitor.steam.webapi, "WebAPI", SessionlessWebAPI)

    assert monitor.steam_web_api_client(API_KEY).key == API_KEY


@pytest.mark.parametrize("verify", [True, False])
# Verifies the SMTP handshake follows the setting, so email is not the one channel that keeps checking certificates
def test_the_smtp_context_honors_the_setting(tls_setting, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)

    context = monitor.smtp_ssl_context()

    assert context.check_hostname is verify
    assert (context.verify_mode == ssl.CERT_REQUIRED) is verify


# Verifies no SMTP call site builds its own context, which would keep that one connection verifying while the setting is off
def test_only_the_shared_helper_builds_an_smtp_context():
    assert SOURCE.count("ssl.create_default_context()") == 1


@pytest.mark.parametrize("verify, silenced", [(True, False), (False, True)])
# Verifies the certificate warning is silenced only once the reader has chosen to switch verification off
def test_the_certificate_warning_is_silenced_only_while_verification_is_off(tls_setting, monkeypatch, verify, silenced):
    disabled = []
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)
    monkeypatch.setattr(monitor.urllib3, "disable_warnings", lambda category: disabled.append(category))

    monitor.apply_tls_verification_setting()

    assert bool(disabled) is silenced


# Verifies the doctor passes the setting silently while it is on
def test_the_doctor_passes_while_verification_is_on(tls_setting):
    tls_setting.setattr(monitor, "VERIFY_SSL", True)

    check = next(item for item in monitor.doctor_check_configuration() if "TLS" in item.label)

    assert (check.status, check.advice) == ("PASS", None)


# Verifies the doctor warns while verification is off and names the setting to change and where it is documented
def test_the_doctor_warns_while_verification_is_off(tls_setting):
    tls_setting.setattr(monitor, "VERIFY_SSL", False)

    check = next(item for item in monitor.doctor_check_configuration() if "TLS" in item.label)

    assert check.status == "WARN"
    assert "VERIFY_SSL" in check.detail
    assert "VERIFY_SSL" in check.advice.fix
    assert monitor.TLS_GUIDE_URL in check.advice.fix


@pytest.mark.parametrize("verify, concise", [(True, False), (False, True)])
# Verifies the summary always records the setting and puts it in front of the reader only when it is off
def test_the_summary_promotes_the_row_only_while_verification_is_off(tls_setting, verify, concise):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)

    row = next(item for item in monitor.build_startup_summary() if item.label == "TLS verification")

    assert (row.full, row.concise) == (True, concise)
    assert row.value.startswith("On" if verify else "Off")


# Verifies certificates are verified unless the reader turns that off, in the shipped config and the fallback alike
def test_certificates_are_verified_by_default():
    shipped = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")

    assert shipped["VERIFY_SSL"] is True
    assert monitor.VERIFY_SSL is True


# Verifies the discovered configuration reaches private API key entry, which checks the key over the network before
# the normal configuration load and would otherwise verify certificates against the default rather than the setting
def test_private_key_entry_applies_the_configured_setting(tls_setting, tmp_path, monkeypatch):
    (tmp_path / "steam_monitor.conf").write_text("VERIFY_SSL = False\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    tls_setting.setattr(monitor, "VERIFY_SSL", True)
    observed = {}
    monkeypatch.setattr(monitor, "run_set_steam_api_key", lambda **kwargs: observed.setdefault("verify", monitor.VERIFY_SSL))
    monkeypatch.setattr(monitor.sys, "argv", ["steam_monitor", "--set-steam-api-key"])

    with pytest.raises(SystemExit):
        monitor.main()

    assert observed["verify"] is False


HTTP_METHODS = frozenset(("get", "post", "put", "patch", "delete", "head", "options", "request"))
# The expressions that carry the TLS decision, so a call passing anything else is a second opinion
VERIFY_ARGUMENTS = frozenset(("VERIFY_SSL",))
# A guard against the sweep silently matching nothing after a rename: the tool has 6 call sites today
MINIMUM_HTTP_CALL_SITES = 6


# Returns every name the module binds to a requests session, so a session added later is swept without editing this
def session_receivers():
    return {node.targets[0].id for node in ast.walk(ast.parse(SOURCE)) if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func).endswith("Session")}


# Returns every outbound HTTP call in the module as a line number paired with its keyword arguments
def http_call_sites():
    receivers = {"req", "requests"} | session_receivers()
    for node in ast.walk(ast.parse(SOURCE)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = node.func.value
        if node.func.attr in HTTP_METHODS and isinstance(receiver, ast.Name) and receiver.id in receivers:
            yield node.lineno, {keyword.arg: keyword.value for keyword in node.keywords}


# Verifies every outbound request passes the setting, so a call site added later cannot keep verifying while it is off
def test_every_outbound_request_passes_the_setting():
    calls = list(http_call_sites())

    assert len(calls) >= MINIMUM_HTTP_CALL_SITES, f"the sweep found {len(calls)} HTTP calls, so it no longer matches how requests are made"
    missing = [line for line, keywords in calls if "verify" not in keywords or ast.unparse(keywords["verify"]) not in VERIFY_ARGUMENTS]
    assert not missing, f"steam_monitor.py lines {missing} make an HTTP call that does not pass the TLS setting"


# Verifies every outbound request carries a deadline, since a call without one hangs the monitoring loop indefinitely
def test_every_outbound_request_carries_a_deadline():
    # A call forwarding **kwargs takes its deadline from the helper that fills them in, which is not readable here
    missing = [line for line, keywords in http_call_sites() if "timeout" not in keywords and None not in keywords]

    assert not missing, f"steam_monitor.py lines {missing} make an HTTP call without a timeout"
