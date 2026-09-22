"""Transport-level checks for long-lived Steam rate limits."""

import json
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
import requests
from requests.adapters import HTTPAdapter

import steam_monitor as monitor


# Stops the monitoring loop without being mistaken for an API failure
class PollingFinished(BaseException):
    pass


# Keeps the real Steam client and notification renderer while returning HTTP responses at the adapter
@pytest.mark.parametrize("failure", ["rate_limit", "descriptor"])
def test_persistent_rate_limit_delivers_one_error_alert(tmp_path, monkeypatch, failure):
    monkeypatch.chdir(tmp_path)
    for name in ("STEAM_LEVEL_XP_CHECK", "FRIENDS_CHECK", "GAMES_LIBRARY_CHECK", "ERROR_NOTIFICATION", "COLORED_OUTPUT", "VERBOSE_MODE", "DEBUG_MODE"):
        monkeypatch.setattr(monitor, name, False)
    monkeypatch.setattr(monitor, "STEAM_API_KEY", "test-api-key")
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123456789/test-value")
    monkeypatch.setattr(monitor, "STEAM_CHECK_INTERVAL", 150)
    state = {"profiles": 0, "deliveries": [], "waits": [], "now": 1767226800}
    interfaces = {"apilist": {"interfaces": [
        {"name": "ISteamUser", "methods": [{"name": "GetPlayerSummaries", "version": 2, "httpmethod": "GET", "parameters": [{"name": "steamids", "type": "string", "optional": False}]}]},
        {"name": "IPlayerService", "methods": [{"name": "GetRecentlyPlayedGames", "version": 1, "httpmethod": "GET", "parameters": [{"name": "steamid", "type": "uint64", "optional": False}, {"name": "count", "type": "uint32", "optional": True}]}]},
    ]}}

    # Supplies realistic interface discovery and provider responses without replacing the Steam client
    def respond(adapter, request, **kwargs):
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        path = urlsplit(request.url).path
        if request.method == "POST":
            state["deliveries"].append(json.loads(request.body))
            response.status_code = 204
            payload = {}
        elif "GetSupportedAPIList" in path:
            payload = interfaces
        elif "GetPlayerSummaries" in path:
            state["profiles"] += 1
            payload = {"response": {"players": [{"steamid": "76561201960435530", "personaname": "TestPlayer", "personastate": 0, "communityvisibilitystate": 3}]}}
            if state["profiles"] > 1:
                if failure == "descriptor":
                    raise OSError(24, "Too many open files")
                response.status_code = 429
                response.headers["Retry-After"] = "150"
                payload = {"error": "Too Many Requests"}
        elif "GetRecentlyPlayedGames" in path:
            payload = {"response": {"games": []}}
        else:
            raise AssertionError(path)
        response._content = json.dumps(payload).encode()
        return response

    # Advances only the monitor's timing while preserving real third-party request handling
    def sleep(seconds):
        state["waits"].append(seconds)
        state["now"] += seconds
        if len(state["waits"]) >= 6:
            raise PollingFinished

    clock = dict(vars(monitor.time))
    clock.update(time=lambda: state["now"], sleep=sleep)
    monkeypatch.setattr(monitor, "time", SimpleNamespace(**clock))
    monkeypatch.setattr(HTTPAdapter, "send", respond)
    with requests.Session() as session:
        monkeypatch.setattr(monitor, "WEBHOOK_SESSION", session)
        if failure == "descriptor":
            with pytest.raises(SystemExit) as stopped:
                monitor.steam_monitor_user(76561201960435530, None)
            assert stopped.value.code == 1
            assert state["deliveries"] == []
            return
        with pytest.raises(PollingFinished):
            monitor.steam_monitor_user(76561201960435530, None)
    assert state["waits"] == [150] * 6
    assert len(state["deliveries"]) == 1
    assert state["deliveries"][0]["embeds"][0]["title"] == "Steam Monitor error: Steam is rate limiting requests (user: TestPlayer)"
