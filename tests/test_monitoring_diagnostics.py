"""Tests that one monitoring cycle explains the Steam calls it makes and the ones that quietly degraded."""

import pytest

import steam_monitor as monitor


STEAM_ID = 76561197960435530


PLAYER_SUMMARY = {
    "response": {
        "players": [
            {
                "steamid": str(STEAM_ID),
                "personaname": "TestPlayer",
                "personastate": 0,
                "communityvisibilitystate": 3,
                "profileurl": "https://steamcommunity.com/id/testplayer/",
                "avatarfull": "https://avatars.steamstatic.com/test_full.jpg",
                "timecreated": 1300000000,
                "lastlogoff": 1700000000,
            }
        ]
    }
}

RECENTLY_PLAYED = {"response": {"games": []}}


class StoppedAfterOneCycle(Exception):
    pass


class FakeSteamWebAPI:
    # Answers the Steam endpoints the monitoring cycle calls, failing the ones named in failing_endpoints
    def __init__(self, failing_endpoints=(), poll_error=None, healthy_polls=1, **_kwargs):
        self.failing_endpoints = set(failing_endpoints)
        # A poll error is raised only after the startup snapshot has succeeded, so the loop is actually reached
        self.poll_error = poll_error
        self.healthy_polls = healthy_polls
        self.polls = 0
        self.called = []

    def call(self, endpoint, **_kwargs):
        self.called.append(endpoint)
        if endpoint == "ISteamUser.GetPlayerSummaries" and self.poll_error is not None:
            self.polls += 1
            if self.polls > self.healthy_polls:
                raise self.poll_error
        if endpoint in self.failing_endpoints:
            raise RuntimeError(f"{endpoint} is unavailable")
        if endpoint == "ISteamUser.GetPlayerSummaries":
            return PLAYER_SUMMARY
        if endpoint == "IPlayerService.GetRecentlyPlayedGames":
            return RECENTLY_PLAYED
        if endpoint == "IPlayerService.GetSteamLevel":
            return {"response": {"player_level": 42}}
        if endpoint == "IPlayerService.GetBadges":
            return {"response": {"player_xp": 5000, "player_xp_needed_to_level_up": 100, "player_xp_needed_current_level": 4900, "badges": []}}
        if endpoint == "ISteamUser.GetFriendList":
            return {"friendslist": {"friends": [{"steamid": "1", "friend_since": 1600000000}]}}
        if endpoint == "IPlayerService.GetOwnedGames":
            return {"response": {"games": [{"appid": 440}]}}
        if endpoint == "ISteamUser.GetPlayerBans":
            return {"players": []}
        return {}


# Runs one monitoring cycle with every tracked feature on and the named endpoints failing
def run_one_cycle(tmp_path, monkeypatch, failing_endpoints=(), diagnostics=True, poll_error=None, stop_after_sleeps=2, error_notifications=False):
    monkeypatch.setattr(monitor, "DEBUG_MODE", diagnostics)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", diagnostics)
    monkeypatch.setattr(monitor, "STEAM_LEVEL_XP_CHECK", True)
    monkeypatch.setattr(monitor, "FRIENDS_CHECK", True)
    monkeypatch.setattr(monitor, "GAMES_LIBRARY_CHECK", True)
    monkeypatch.setattr(monitor, "STEAM_CHECK_INTERVAL", 60)
    monkeypatch.setattr(monitor, "STEAM_ACTIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_COUNTER", 0)
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", error_notifications)
    monkeypatch.setattr(monitor, "STEAM_LEVEL_XP_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "FRIENDS_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "GAMES_LIBRARY_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", error_notifications)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", error_notifications)
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "")
    # Keep every generated file inside the temporary directory
    monkeypatch.chdir(tmp_path)

    api = FakeSteamWebAPI(failing_endpoints, poll_error=poll_error)
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda *args, **kwargs: api)

    sleeps = []

    def stop_after_the_first_cycle(seconds):
        sleeps.append(seconds)
        # The first sleep is the one before the loop, the rest end each cycle
        if len(sleeps) >= stop_after_sleeps:
            raise StoppedAfterOneCycle()

    monkeypatch.setattr(monitor.time, "sleep", stop_after_the_first_cycle)

    with pytest.raises(StoppedAfterOneCycle):
        monitor.steam_monitor_user(STEAM_ID, "", None)
    return api, sleeps


# Verifies a healthy cycle names the Steam calls it makes and the interval it waits
def test_a_healthy_cycle_names_its_steam_calls(tmp_path, monkeypatch, capsys):
    api, sleeps = run_one_cycle(tmp_path, monkeypatch)

    output = capsys.readouterr().out
    assert "Opening the Steam Web API with key" in output
    assert "Polling Steam for 76561197960435530" in output
    assert "Next check in 1 minute (user is offline)" in output
    assert "IPlayerService.GetOwnedGames" in api.called
    assert sleeps[0] == 60


# Verifies a failing level lookup names the endpoint instead of degrading in silence
def test_a_failing_level_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetSteamLevel"})

    output = capsys.readouterr().out
    assert "Fetching the Steam level (IPlayerService.GetSteamLevel) failed with RuntimeError" in output
    assert "Steam level or total XP was unavailable this cycle" in output


# Verifies a failing friends lookup names the endpoint and says the alert cannot fire
def test_a_failing_friends_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"ISteamUser.GetFriendList"})

    output = capsys.readouterr().out
    assert "Fetching the friends list (ISteamUser.GetFriendList) failed with RuntimeError" in output
    assert "The friends list was unavailable this cycle, so friends alerts cannot fire" in output


# Verifies a failing games library lookup names the endpoint and says the alert cannot fire
def test_a_failing_games_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetOwnedGames"})

    output = capsys.readouterr().out
    assert "Fetching the games library (IPlayerService.GetOwnedGames) failed with RuntimeError" in output
    assert "The games library was unavailable this cycle, so games library alerts cannot fire" in output


# Verifies a failing badges lookup is reported, since total XP alerts depend on it alone
def test_a_failing_badges_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetBadges"})

    output = capsys.readouterr().out
    assert "Fetching total XP (IPlayerService.GetBadges) failed with RuntimeError" in output
    assert "Steam level or total XP was unavailable this cycle" in output


# Verifies a working tracked feature produces no degradation warning
def test_a_healthy_cycle_reports_no_degradation(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch)

    output = capsys.readouterr().out
    assert "was unavailable this cycle" not in output


# Verifies the same degraded cycle prints nothing extra when neither diagnostic mode is on
def test_a_degraded_cycle_stays_quiet_without_diagnostics(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetSteamLevel", "ISteamUser.GetFriendList"}, diagnostics=False)

    output = capsys.readouterr().out
    assert "[DEBUG" not in output
    assert "was unavailable this cycle" not in output
    assert "Polling Steam for" not in output


# Returns an HTTP error carrying the given status, the way requests raises one
def http_error(status_code, message="request failed"):
    import requests as req

    response = req.Response()
    response.status_code = status_code
    return req.exceptions.HTTPError(message, response=response)


# Verifies a transient failure gets one short retry rather than waiting a whole polling interval
def test_a_transient_failure_retries_once_quickly(tmp_path, monkeypatch, capsys):
    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=TimeoutError("request timed out"), stop_after_sleeps=4)

    # The first sleep precedes the loop, then one short retry, then the full interval once the retry is spent
    assert sleeps[0] == 60
    assert sleeps[1] == monitor.TRANSIENT_RETRY_SECONDS
    assert sleeps[2] == 60
    output = capsys.readouterr().out
    assert "The Steam Web API request timed out" in output
    assert f"Retrying once in {monitor.display_time(monitor.TRANSIENT_RETRY_SECONDS)}" in output


# Verifies a rate limit skips the short retry and waits the period Steam asked for
def test_a_rate_limit_waits_instead_of_retrying_quickly(tmp_path, monkeypatch, capsys):
    error = http_error(429)
    assert error.response is not None
    error.response.headers["Retry-After"] = "120"

    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=error, stop_after_sleeps=3)

    assert sleeps[0] == 60
    assert sleeps[1] == 120
    assert monitor.TRANSIENT_RETRY_SECONDS not in sleeps
    output = capsys.readouterr().out
    assert "Steam is rate limiting requests" in output


# Verifies a failure that cannot be retried goes straight to the polling interval
def test_a_rejected_api_key_does_not_get_a_quick_retry(tmp_path, monkeypatch, capsys):
    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(403), stop_after_sleeps=3)

    assert sleeps[0] == 60
    assert sleeps[1] == 60
    assert monitor.TRANSIENT_RETRY_SECONDS not in sleeps
    assert "Steam rejected the configured Web API key" in capsys.readouterr().out


# Verifies a continuing outage explains itself once rather than on every cycle
def test_a_continuing_outage_prints_one_hint(tmp_path, monkeypatch, capsys):
    _api, _sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(503), stop_after_sleeps=6)

    output = capsys.readouterr().out
    assert output.count("The Steam Web API is temporarily unavailable") >= 3
    assert output.count("To fix: ") == 1


# Verifies a delivered error channel stays suppressed while a failed channel retries during the same outage
def test_a_continuing_outage_retries_only_failed_notification_channels(tmp_path, monkeypatch):
    deliveries = []

    # Records which delivery channels each outage cycle requests
    def record_delivery(*_args, **kwargs):
        deliveries.append((kwargs["email_enabled"], kwargs["webhook_enabled"]))
        return True, False

    monkeypatch.setattr(monitor, "send_notification_channels", record_delivery)
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=4, error_notifications=True)

    assert deliveries == [(True, True), (False, True)]
