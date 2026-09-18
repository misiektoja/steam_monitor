import copy
import json
import socket
import sys

import pytest
from dotenv import dotenv_values

import steam_monitor as monitor


@pytest.fixture(autouse=True)
# Restores effective configuration after each isolated startup case
def isolated_configuration(monkeypatch, tmp_path):
    for name, value in list(vars(monitor).items()):
        if name.isupper():
            monkeypatch.setattr(monitor, name, copy.copy(value) if isinstance(value, (dict, list, set)) else value)
    for key in monitor.SECRET_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize("source", ['SMTP_PASSWORD: "synthetic-private-credential" =\n', 'SMTP_PASSWORD = (\n    "synthetic-private-credential" unexpected\n)\n'])
# Malformed source may contain credentials that never reached effective configuration
def test_syntax_error_omits_unloaded_credentials(monkeypatch, tmp_path, capsys, debug, source):
    monkeypatch.setattr(monitor, "DEBUG_MODE", debug)
    config = tmp_path / "broken.conf"
    config.write_text(source, encoding="utf-8")
    assert not monitor.load_config_file(config, namespace={})
    output = capsys.readouterr().out
    assert "synthetic-private-credential" not in output
    assert "broken.conf" in output
    assert "Source:" not in output


@pytest.mark.parametrize("existing", [None, "", "synthetic-existing"])
# Inline credentials survive replacement without overriding an explicit dotenv value
def test_preserve_inline_credentials(tmp_path, existing):
    config = tmp_path / "settings.conf"
    original = 'SMTP_PASSWORD = "synthetic-inline"\n'
    config.write_text(original, encoding="utf-8")
    env = tmp_path / "private.env"
    if existing is not None:
        env.write_text("SMTP_PASSWORD=" + json.dumps(existing) + "\nKEEP=unchanged\n", encoding="utf-8")
    monitor.preserve_inline_config_secrets(config, env)
    saved = dotenv_values(env, interpolate=False)
    assert saved["SMTP_PASSWORD"] == ("synthetic-inline" if existing is None else existing)
    assert config.read_text(encoding="utf-8") == original
    if existing is not None:
        assert saved["KEEP"] == "unchanged"
    else:
        assert env.stat().st_mode & 0o077 == 0


# A failed private write cannot destroy the original inline credential
def test_preservation_failure_leaves_original_config(tmp_path):
    config = tmp_path / "settings.conf"
    original = 'SMTP_PASSWORD = "synthetic-inline"\n'
    config.write_text(original, encoding="utf-8")
    directory = tmp_path / "not-a-file"
    directory.mkdir()
    with pytest.raises((OSError, ValueError)):
        monitor.preserve_inline_config_secrets(config, directory)
    assert config.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -1, True, "30", 10 ** 400])
# Effective runtime validation rejects unusable timing values without conversion errors
def test_invalid_runtime_timing(monkeypatch, value):
    setting = "SPOTIFY_CHECK_INTERVAL" if hasattr(monitor, "runtime_numeric_errors") else "CHECK_INTERNET_TIMEOUT"
    monkeypatch.setattr(monitor, setting, value)
    validate = getattr(monitor, "runtime_numeric_errors", None) or monitor.runtime_configuration_errors
    assert any(setting in error for error in validate())


# Normal startup must report invalid timing before attempting a connection
def test_normal_startup_validates_before_network(monkeypatch, tmp_path, capsys):
    config = tmp_path / "settings.conf"
    setting = "SPOTIFY_CHECK_INTERVAL" if hasattr(monitor, "runtime_numeric_errors") else "CHECK_INTERNET_TIMEOUT"
    config.write_text(setting + " = 1e309\n", encoding="utf-8")
    calls = []

    # Records attempts at the actual socket boundary without replacing a provider client
    def offline(sock, address):
        calls.append(address)
        raise OSError("Network is unreachable")
    monkeypatch.setattr(socket.socket, "connect", offline)
    monkeypatch.setattr(sys, "argv", [monitor.__file__, "--config-file", str(config), "--env-file", "none", "--send-test-email"])
    with pytest.raises(SystemExit) as stopped:
        monitor.main()
    assert stopped.value.code == 1
    assert not calls
    output = capsys.readouterr()
    assert setting in output.out + output.err


@pytest.mark.parametrize("record", [{}, [], [1], [-1, "online"], [1e309, "online"], ["yesterday", "online"], [1700000000, {}]])
# Damaged saved status is rejected before any caller performs date arithmetic
def test_invalid_saved_status(tmp_path, record):
    path = tmp_path / "status.json"
    text = json.dumps(record)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        monitor.read_status_record(path)
    assert path.read_text(encoding="utf-8") == text


# Extra saved fields remain compatible with earlier readers
def test_valid_saved_status_keeps_extra_fields(tmp_path):
    path = tmp_path / "status.json"
    record = [1700000000, 0, None, {"note": "legacy"}]
    path.write_text(json.dumps(record), encoding="utf-8")
    assert monitor.read_status_record(path) == record


@pytest.mark.parametrize("payload", [{"response": {}}, {}, {"response": {"game_count": 3, "games": []}}, {"response": {"game_count": -1, "games": []}}])
# A missing or partial response must never masquerade as an empty library
def test_incomplete_games_snapshot(payload):
    with pytest.raises(ValueError):
        monitor.games_library_snapshot(payload)


# Steam explicitly confirms an empty accessible library with a zero count
def test_explicit_empty_library():
    assert monitor.games_library_snapshot({"response": {"game_count": 0}}) == (0, set())


@pytest.mark.parametrize("saved", [{"game_count": 3, "appids": [10, 20]}, {"game_count": 2, "appids": [10, 10, 20]}])
# Earlier releases counted the response list while deduplicating the IDs, so their files must still load
def test_saved_snapshot_tolerates_a_legacy_count(saved):
    assert monitor.games_library_snapshot(saved, saved=True) == (2, {10, 20})


@pytest.mark.parametrize("saved", [[], {"game_count": -1, "appids": []}, {"game_count": 1, "appids": "10"}, {"game_count": 1, "appids": [0]}])
# A saved snapshot with an unusable shape is still refused rather than adopted
def test_saved_snapshot_rejects_unusable_shapes(saved):
    with pytest.raises(ValueError):
        monitor.games_library_snapshot(saved, saved=True)


# Legacy filenames keep the original persona spelling while display text can be normalized
def test_migrate_whitespace_persona(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "STEAM_STATUS_FILE", "")
    old = tmp_path / "steam_ Someone _last_status.json"
    old.write_text("[1700000000, 0, null]", encoding="utf-8")
    monitor.migrate_legacy_state_files(76561201960287930, " Someone ")
    assert not old.exists()
    assert (tmp_path / "steam_76561201960287930_last_status.json").read_text(encoding="utf-8") == "[1700000000, 0, null]"


# AST spans remain usable when running on Python versions without end-position attributes
def test_legacy_ast_span_preserves_multiline_secret():
    import ast
    text = 'SMTP_PASSWORD = (\n    "first"\n    "second"\n)\nKEEP = 7\n'
    assignment = ast.parse(text).body[0]
    assert isinstance(assignment, ast.Assign)
    value = assignment.value
    for node in ast.walk(value):
        for name in ("end_lineno", "end_col_offset"):
            if hasattr(node, name):
                delattr(node, name)
    end_line, end_column = monitor.config_node_end(value, text)
    assert (end_line, end_column) == (3, 12)
    restored = text.splitlines(keepends=True)
    restored[1:3] = ['    ""\n']
    assignment = ast.parse("".join(restored)).body[0]
    assert isinstance(assignment, ast.Assign)
    assert ast.literal_eval(assignment.value) == ""


@pytest.mark.parametrize("status", [429, 503])
# Real ValvePython iteration stops after a provider-wide failure instead of issuing more work
def test_achievement_failure_stops_real_client(monkeypatch, capsys, status):
    from urllib.parse import urlsplit
    import requests
    from requests.adapters import HTTPAdapter
    methods = {"IPlayerService": {"GetOwnedGames": ["steamid", "include_appinfo", "include_played_free_games", "appids_filter[0]", "include_free_sub", "include_extended_appinfo", "language"]}, "ISteamUserStats": {"GetPlayerAchievements": ["steamid", "appid"]}}
    calls = []

    # Returns real responses at the HTTP boundary while keeping the provider library intact
    def send(adapter, request, **kwargs):
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        path = urlsplit(request.url).path
        calls.append(path)
        if "GetSupportedAPIList" in path:
            payload = {"apilist": {"interfaces": [{"name": interface, "methods": [{"name": method, "version": 1, "httpmethod": "GET", "parameters": [{"name": parameter, "type": "string", "optional": True, "description": ""} for parameter in parameters]} for method, parameters in entries.items()]} for interface, entries in methods.items()]}}
        elif "GetOwnedGames" in path:
            payload = {"response": {"game_count": 100, "games": [{"appid": number, "name": "Game", "playtime_forever": 1} for number in range(1, 101)]}}
        else:
            response.status_code = status
            response.headers["Retry-After"] = "60"
            payload = {"error": "temporarily unavailable"}
        response._content = json.dumps(payload).encode()
        return response
    monkeypatch.setattr(HTTPAdapter, "send", send)
    client = monitor.steam.webapi.WebAPI(key="synthetic-api-key")
    assert monitor.display_recent_achievements(76561201960287930, client, {"response": {"games": []}}) is False
    assert sum("GetPlayerAchievements" in path for path in calls) == 1
    output = capsys.readouterr().out
    assert "No recent achievements" not in output
    assert "run the command again" in output
    if status == 429:
        assert "1 minute" in output
