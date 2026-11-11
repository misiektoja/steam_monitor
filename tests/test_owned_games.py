"""Real Steam client parameter validation with synthetic metadata and an offline HTTP transport."""

import copy
import json
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from requests.adapters import HTTPAdapter

import steam_monitor as monitor


STEAM_ID = 76561201960435530
PARAMETERS = {"steamid": "uint64", "include_appinfo": "bool", "include_played_free_games": "bool", "appids_filter[0]": "uint32", "include_free_sub": "bool", "language": "string", "include_extended_appinfo": "bool", "include_family_licenses": "bool", "include_all_free_games": "bool", "key": "string"}


# Models required parameters before the real provider normalizes the array suffix
def method_schema(name, parameters, extra=()):
    return {"name": name, "version": 1, "httpmethod": "GET", "parameters": [{"name": key, "type": kind, "optional": False, "description": ""} for key, kind in parameters.items()] + copy.deepcopy(list(extra))}


# Reads the live parameter metadata the argument builder uses, from an interface the provider builds at runtime
def owned_games_parameters(api: Any):
    return api.IPlayerService.GetOwnedGames.parameters


# Keeps the provider intact while replacing HTTP with endpoint-shaped synthetic responses
def make_client(monkeypatch, extra=(), owned_error=None, owned_payload=None):
    methods = {"IPlayerService": [method_schema("GetOwnedGames", PARAMETERS, extra), method_schema("GetRecentlyPlayedGames", {"steamid": "uint64", "count": "uint32"}), method_schema("GetSteamLevel", {"steamid": "uint64"}), method_schema("GetBadges", {"steamid": "uint64"})], "ISteamUser": [method_schema("GetPlayerSummaries", {"steamids": "string"}), method_schema("GetPlayerBans", {"steamids": "string"}), method_schema("GetFriendList", {"steamid": "uint64", "relationship": "string"})], "ISteamUserStats": [method_schema("GetPlayerAchievements", {"steamid": "uint64", "appid": "uint32"})]}
    calls = []

    # Records wire arguments and returns local JSON, never contacting Steam
    def send(adapter, request, **kwargs):
        path = urlsplit(request.url).path
        query = parse_qs(urlsplit(request.url).query)
        calls.append((path, query))
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        if "GetOwnedGames" in path:
            if owned_error is not None:
                response.status_code = owned_error
            wanted = {int(value[0]) for key, value in query.items() if key.startswith("appids_filter[")}
            games = [{"appid": appid, "name": name, "playtime_forever": 120} for appid, name in [(10, "First game"), (20, "Second game")] if not wanted or appid in wanted]
            payload = owned_payload if owned_payload is not None else {"response": {"game_count": len(games), "games": games}}
        elif "GetPlayerSummaries" in path:
            payload = {"response": {"players": [{"steamid": str(STEAM_ID), "personaname": "Synthetic player", "personastate": 0, "communityvisibilitystate": 3, "lastlogoff": 1700000000}]}}
        elif "GetPlayerBans" in path:
            payload = {"players": []}
        elif "GetFriendList" in path:
            payload = {"friendslist": {"friends": []}}
        elif "GetPlayerAchievements" in path:
            payload = {"playerstats": {"achievements": []}}
        else:
            payload = {"response": {"games": [], "player_level": 1, "player_xp": 0}}
        response._content = json.dumps(payload).encode("utf-8")
        return response

    monkeypatch.setattr(HTTPAdapter, "send", send)
    client = monitor.steam.webapi.WebAPI(key="synthetic-owned-games-key", auto_load_interfaces=False)
    client.load_interfaces({"apilist": {"interfaces": [{"name": name, "methods": entries} for name, entries in methods.items()]}})
    return client, calls


@pytest.fixture(autouse=True)
# Isolates generated files and settings, and prevents any notification delivery
def isolated_settings(monkeypatch, tmp_path):
    for name, value in {"DEBUG_MODE": False, "VERBOSE_MODE": False, "COLORED_OUTPUT": False, "MONITORING_ACTIVE": False, "GAMES_LIBRARY_CHECK": True, "STEAM_LEVEL_XP_CHECK": False, "FRIENDS_CHECK": False, "FILE_SUFFIX": "", "STEAM_STATUS_FILE": "", "WEBHOOK_ENABLED": False, "ERROR_NOTIFICATION": False, "GAMES_LIBRARY_NOTIFICATION": False, "ACTIVE_INACTIVE_NOTIFICATION": False, "STATUS_NOTIFICATION": False, "GAME_CHANGE_NOTIFICATION": False, "NAME_CHANGE_NOTIFICATION": False}.items():
        monkeypatch.setattr(monitor, name, value)
    monkeypatch.chdir(tmp_path)


class StopPolling(Exception):
    pass


# Executes startup and one real poll, stopping at the next scheduled wait
def monitor_one_cycle(monkeypatch, client, cycles=1, before_wait=None):
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda: client)
    waits = []

    # Skips real delays without replacing the request or comparison paths
    def wait(seconds):
        waits.append(seconds)
        if before_wait is not None:
            before_wait(len(waits))
        if len(waits) == cycles + 1:
            raise StopPolling()

    monkeypatch.setattr(monitor.time, "sleep", wait)
    with pytest.raises(StopPolling):
        monitor.steam_monitor_user(STEAM_ID, "")


# Demonstrates the missing arguments fail locally, before the first owned-games HTTP call
def test_original_parameters_fail_before_http(monkeypatch):
    api, calls = make_client(monkeypatch)
    arguments = {"steamid": STEAM_ID, "include_appinfo": 1, "include_played_free_games": 1, "appids_filter": [], "include_free_sub": 0, "include_extended_appinfo": 0, "language": "en"}
    with pytest.raises(ValueError, match="Method requires 'include_family_licenses' to be set"):
        api.call("IPlayerService.GetOwnedGames", **arguments)
    assert calls == []


@pytest.mark.parametrize("entrypoint", ["names", "achievements", "information", "monitoring"])
# Covers all five call sites, including both startup and polling in the monitoring case
def test_owned_games_entrypoints_supply_required_parameters(monkeypatch, capsys, entrypoint):
    api, calls = make_client(monkeypatch)
    if entrypoint == "names":
        assert monitor.fetch_app_names(api, STEAM_ID, [20]) == {20: "Second game"}
    elif entrypoint == "achievements":
        assert monitor.fetch_recent_achievements(STEAM_ID, api, {"response": {"games": []}}) == []
    elif entrypoint == "information":
        monkeypatch.setattr(monitor, "steam_web_api_client", lambda: api)
        monitor.display_user_info(STEAM_ID)
        assert "Top games by lifetime hours" in capsys.readouterr().out
    else:
        monitor_one_cycle(monkeypatch, api)
    owned = [query for path, query in calls if "GetOwnedGames" in path]
    assert len(owned) == (2 if entrypoint == "monitoring" else 1)
    assert [query["include_appinfo"] for query in owned] == ([["1"], ["0"]] if entrypoint == "monitoring" else [["1"]])
    for query in owned:
        assert query["include_family_licenses"] == ["0"]
        assert query["include_all_free_games"] == ["0"]
        assert query["include_played_free_games"] == ["1"]
        assert query["language"] == ["en"]
        assert query["key"] == ["synthetic-owned-games-key"]
    if entrypoint == "names":
        assert owned[0]["appids_filter[0]"] == ["20"]


@pytest.mark.parametrize("kind,array,expected", [("bool", False, 0), ("uint32", False, 0), ("uint64", False, 0), ("uint128", False, 0), ("uint", False, 0), ("int32", False, 0), ("int64", False, 0), ("{enum}", False, 0), ("string", False, ""), ("uint32", True, []), ("string[]", False, [])])
# Defaults future required parameters by type, checking array metadata before the scalar element type
def test_future_required_parameter_defaults(monkeypatch, capsys, kind, array, expected):
    api, calls = make_client(monkeypatch, [{"name": "future_argument" + ("[0]" if array else ""), "type": kind, "optional": False}])
    metadata = copy.deepcopy(owned_games_parameters(api))
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    arguments = monitor.owned_games_arguments(api, STEAM_ID)
    assert arguments["future_argument"] == expected
    assert owned_games_parameters(api) == metadata
    api.call("IPlayerService.GetOwnedGames", **arguments)
    assert len(calls) == 1
    output = capsys.readouterr().out
    assert "future_argument" in output
    assert "synthetic-owned-games-key" not in output
    assert str(STEAM_ID) not in output


# Optional metadata and credentials stay wrapper-owned, and caller arrays are copied rather than changed
def test_optional_and_wrapper_owned_parameters_are_untouched(monkeypatch):
    api, _ = make_client(monkeypatch, [{"name": "skip_unvetted_apps", "type": "bool", "optional": True}])
    wanted = [20]
    arguments = monitor.owned_games_arguments(api, STEAM_ID, include_appinfo=1, appids_filter=wanted)
    assert arguments["include_appinfo"] == 1
    assert arguments["appids_filter"] == wanted
    assert arguments["appids_filter"] is not wanted
    assert "skip_unvetted_apps" not in arguments
    assert "key" not in arguments


# No provider argument array can leak mutations into the next request
def test_default_arrays_are_not_shared(monkeypatch):
    api, _ = make_client(monkeypatch)
    first = monitor.owned_games_arguments(api, STEAM_ID)
    first["appids_filter"].append(10)
    assert monitor.owned_games_arguments(api, STEAM_ID)["appids_filter"] == []


@pytest.mark.parametrize("kind", ["bytes", "{message}", "struct payload", ""])
# A type with no neutral value is a local defect rather than a guessed request or a privacy error
def test_unknown_required_type_is_a_local_parameter_error(monkeypatch, kind):
    api, calls = make_client(monkeypatch, [{"name": "future_argument", "type": kind, "optional": False}])
    with pytest.raises(ValueError) as failure:
        monitor.owned_games_arguments(api, STEAM_ID)
    advice = monitor.classify_recovery_error(failure.value)
    assert advice.code == "steam.parameters"
    assert advice.retryable is False
    assert calls == []


@pytest.mark.parametrize("message", ["Method requires 'include_family_licenses' to be set", "Unrecognized parameter 'old_parameter'", "Expected 'appids_filter' to be a list, got <class 'int'>"])
# The actual provider argument errors have actionable compatibility advice
def test_provider_parameter_failures_are_not_privacy_errors(message):
    advice = monitor.classify_recovery_error(ValueError(message))
    assert advice.code == "steam.parameters"
    assert "privacy" not in advice.summary
    assert monitor.OWNED_GAMES_GUIDE_URL in advice.fix


@pytest.mark.parametrize("failure,code", [(requests.Timeout(), "network.timeout"), (requests.ConnectionError(), "network.unavailable"), (ValueError("Steam did not return a complete games library"), "unknown"), (requests.exceptions.JSONDecodeError("Method requires 'x' to be set", "", 0), "unknown")])
# Transport, JSON decoding and snapshot validation retain their categories despite sharing exception ancestry
def test_other_failures_keep_their_categories(failure, code):
    assert monitor.classify_recovery_error(failure).code == code


# A repeated parameter defect is visible without debug, but does not stop core monitoring or spam each poll
def test_parameter_failure_is_visible_without_debug_and_not_repeated(monkeypatch, capsys):
    api, calls = make_client(monkeypatch, [{"name": "future_argument", "type": "bytes", "optional": False}])
    monitor_one_cycle(monkeypatch, api)
    output = capsys.readouterr().out
    assert output.count("* Error: Steam Monitor's request parameters are incompatible") == 1
    assert "The saved snapshot was kept" not in output
    assert not any("GetOwnedGames" in path for path, _ in calls)
    assert sum("GetPlayerSummaries" in path for path, _ in calls) == 2


@pytest.mark.parametrize("entrypoint", ["names", "information", "achievements"])
# Optional data paths do not silently swallow local compatibility failures
def test_optional_paths_report_parameter_defects(monkeypatch, capsys, entrypoint):
    api, _ = make_client(monkeypatch, [{"name": "future_argument", "type": "bytes", "optional": False}])
    if entrypoint == "names":
        assert monitor.fetch_app_names(api, STEAM_ID, [10]) == {}
    elif entrypoint == "information":
        monkeypatch.setattr(monitor, "steam_web_api_client", lambda: api)
        monitor.display_user_info(STEAM_ID)
    else:
        assert monitor.display_recent_achievements(STEAM_ID, api, {"response": {"games": []}}) is False
    assert "* Error: Steam Monitor's request parameters are incompatible" in capsys.readouterr().out


@pytest.mark.parametrize("saved", [False, True])
# Startup claims retained history only when a valid saved baseline was loaded
def test_unavailable_library_retention_message_matches_saved_state(monkeypatch, tmp_path, capsys, saved):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    if saved:
        (tmp_path / monitor.default_games_file(STEAM_ID)).write_text(json.dumps({"game_count": 1, "appids": [10]}), encoding="utf-8")
    api, _ = make_client(monkeypatch, owned_error=503)
    monitor_one_cycle(monkeypatch, api)
    output = capsys.readouterr().out
    assert ("The saved snapshot was kept" in output) is saved
    assert "request parameters are incompatible" not in output


# A mid-run metadata change is reported once, leaves the old library intact and permits recovery
def test_parameter_failure_during_polling_does_not_stop_other_features(monkeypatch, capsys):
    api, calls = make_client(monkeypatch)

    # Changes synthetic metadata only between iterations to exercise the actual argument builder
    def change_metadata(wait_count):
        parameters = owned_games_parameters(api)
        if wait_count == 1:
            parameters["future_argument"] = {"type": "bytes", "optional": False, "_array": False}
        elif wait_count == 3:
            parameters.pop("future_argument")

    monitor_one_cycle(monkeypatch, api, cycles=3, before_wait=change_metadata)
    assert capsys.readouterr().out.count("* Error: Steam Monitor's request parameters are incompatible") == 1
    assert sum("GetOwnedGames" in path for path, _ in calls) == 2
    assert sum("GetPlayerSummaries" in path for path, _ in calls) == 4


# A confirmed empty library is valid and remains distinct from an unavailable response
def test_empty_library_is_valid(monkeypatch):
    api, _ = make_client(monkeypatch, owned_payload={"response": {"game_count": 0}})
    payload = api.call("IPlayerService.GetOwnedGames", **monitor.owned_games_arguments(api, STEAM_ID))
    assert monitor.games_library_snapshot(payload) == (0, set())
