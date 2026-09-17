"""Regression tests for private settings carried across setup destinations."""

import os
import importlib
import socket
import sys

import pytest

monitor = importlib.import_module("steam_monitor")
PRIMARY_KEY = "STEAM_API_KEY"


# Restores startup-mutated settings and mutable bookkeeping after each independent scenario
@pytest.fixture(autouse=True)
def restore_settings(monkeypatch):
    for key in monitor.SECRET_KEYS:
        monkeypatch.setenv(key, os.environ.get(key, ""))
        monkeypatch.delenv(key, raising=False)
    for name, value in list(vars(monitor).items()):
        if name.isupper():
            monkeypatch.setattr(monitor, name, value.copy() if isinstance(value, (dict, list, set)) else value)


# Supplies only interactive answers while keeping configuration and credential resolution real
def destination_answers(config_path, env_path):
    # Answers destination prompts and declines optional configuration
    def answer(prompt):
        if "Configuration file destination" in prompt:
            return str(config_path)
        if "Dotenv file destination" in prompt:
            return str(env_path)
        if "Continue without" in prompt:
            return "y"
        return "n"
    return answer


# Proves a kept file credential reaches the new dotenv without replacing its existing values
@pytest.mark.parametrize("destination_value", [None, "", "destination-key"])
def test_moving_dotenv_preserves_kept_credentials(tmp_path, monkeypatch, destination_value):
    old = tmp_path / "old.env"
    new = tmp_path / "new.env"
    config = tmp_path / "monitor.conf"
    key = PRIMARY_KEY
    for name in monitor.SECRET_KEYS:
        monkeypatch.delenv(name, raising=False)
    old.write_text(f'{key}="retained-key"\n', encoding="utf-8")
    if destination_value is not None:
        new.write_text(f'{key}="{destination_value}"\n', encoding="utf-8")
    values = dict(monitor._config_template_defaults())
    values[key] = "retained-key"
    if key == "MS_APP_CLIENT_ID":
        values["MS_APP_CLIENT_SECRET"] = "retained-secret"
        with old.open("a", encoding="utf-8") as stream:
            stream.write('MS_APP_CLIENT_SECRET="retained-secret"\n')
    if key == "LASTFM_API_KEY":
        values["LASTFM_API_SECRET"] = "retained-secret"
        with old.open("a", encoding="utf-8") as stream:
            stream.write('LASTFM_API_SECRET="retained-secret"\n')
    state = monitor.WizardSetupState(config, old, values)
    monitor._wizard_collect_destination_section(state, input_func=destination_answers(config, new), getpass_func=lambda _prompt: "")
    if state.secret_updates:
        monitor.update_dotenv_file(new, state.secret_updates)
    actual = monitor._wizard_private_values(new).get(key)
    assert actual == ("retained-key" if destination_value is None else destination_value)
    assert "retained-key" in old.read_text(encoding="utf-8")


# Runs Doctor offline with an unreadable dotenv through the actual command entry point
def test_doctor_reports_invalid_dotenv_encoding(tmp_path, monkeypatch, capsys):
    config = tmp_path / "monitor.conf"
    env = tmp_path / "broken.env"
    config.write_text("CLEAR_SCREEN=False\n", encoding="utf-8")
    env.write_bytes(b'UNRELATED_SETTING="bad-encoding-\xff"\n')
    monkeypatch.setattr(sys, "argv", [monitor.__file__, "--doctor", "--config-file", str(config), "--env-file", str(env)])

    # Refuses DNS at the network boundary without replacing the Doctor implementation
    def offline(*_args, **_kwargs):
        raise socket.gaierror("offline")
    monkeypatch.setattr(socket, "getaddrinfo", offline)
    with pytest.raises(SystemExit) as stopped:
        monitor.main()
    assert stopped.value.code == 1
    output = capsys.readouterr().out
    assert "UTF-8" in output
    assert "Dotenv file loaded" not in output


# Resolves an explicit configuration before dispatching each private credential command
@pytest.mark.parametrize("flag,runner", [("--set-steam-api-key", "run_set_steam_api_key"), ("--set-smtp-password", "run_set_smtp_password"), ("--set-webhook-url", "run_set_webhook_url")])
def test_secret_commands_use_selected_configuration(tmp_path, monkeypatch, flag, runner):
    config = tmp_path / "selected.conf"
    env = tmp_path / "selected.env"
    config.write_text("VERIFY_SSL=False\nTARGET_STEAM_ID='76561201960435530'\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [monitor.__file__, "--config-file", str(config), "--env-file", str(env), flag])
    reached = []

    # Records the already resolved command context at the dispatch boundary
    def capture(**kwargs):
        reached.append((monitor.CLI_CONFIG_PATH, monitor.VERIFY_SSL, kwargs["env_file"]))
    monkeypatch.setattr(monitor, runner, capture)
    with pytest.raises(SystemExit) as stopped:
        monitor.main()
    assert stopped.value.code == 0
    assert reached == [(str(config), False, str(env))]


# Proves each cause names itself, so a readable file with bad bytes and an unopenable one do not share one message
@pytest.mark.parametrize("error,expected_detail,expected_fix", [
    (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"), "is not valid UTF-8 text", "Save the dotenv file as UTF-8"),
    (PermissionError(13, "Permission denied"), "could not be opened", "Check the dotenv file path and its read permissions"),
    (ValueError("unexpected"), "could not be read", "Check that the dotenv file is readable UTF-8 text"),
])
def test_dotenv_load_problem_names_its_cause(error, expected_detail, expected_fix):
    detail, fix = monitor.dotenv_load_problem("/tmp/private.env", error)

    assert detail == f"Dotenv file '/tmp/private.env' {expected_detail}"
    assert fix == expected_fix
