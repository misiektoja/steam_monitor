"""Tests that printed commands, described secrets and guide links match the detected install method."""

from command_expectations import runtime_command
import shlex
import inspect
import pytest

import steam_monitor as monitor


@pytest.fixture(autouse=True)
# Keeps install detection and path rendering deterministic regardless of how the suite itself was started
def isolated_install_detection(monkeypatch):
    monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)
    monkeypatch.delenv("STEAM_MONITOR_IN_CONTAINER", raising=False)
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "system", lambda: "Linux")


# Verifies a downloaded script is detected from the invoked file name
def test_a_downloaded_script_is_detected(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/home/user/steam_monitor.py", "--doctor"])

    assert monitor.install_method() == monitor.INSTALL_METHOD_SCRIPT
    assert monitor.install_method_display_name() == "downloaded script"
    assert monitor.render_command(["--version"]) == runtime_command("python3 steam_monitor.py --version")


# Verifies a value only shaped like a placeholder is quoted, so pasting the rendered command cannot run a substitution
def test_a_value_shaped_like_a_placeholder_is_quoted():
    crafted = "<$(echo>marker)>"

    assert shlex.split(monitor.quote_command_argument(crafted)) == [crafted]
    assert monitor.quote_command_argument("<steam_target>") == "<steam_target>"


# Verifies the packaged console script is detected and rendered by its entry point name
def test_a_pypi_install_is_detected(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor", "--doctor"])

    assert monitor.install_method() == monitor.INSTALL_METHOD_PYPI
    assert monitor.install_method_display_name() == "PyPI install"
    assert monitor.render_command(["--version"]) == runtime_command("steam_monitor --version")


# Verifies detection can be pinned explicitly, which containers and packaged builds need
def test_the_install_method_can_be_overridden(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/home/user/steam_monitor.py"])
    monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "pip")

    assert monitor.install_method() == monitor.INSTALL_METHOD_PYPI


# Verifies a container is named in the install method, so printed guidance can be tailored to it
def test_a_container_is_reported_in_the_install_method(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setenv("STEAM_MONITOR_IN_CONTAINER", "true")

    assert monitor.running_in_container() is True
    assert monitor.install_method_display_name() == "PyPI install in a container"


# Verifies the active config and dotenv paths are carried into every printed command
def test_active_paths_are_carried_into_printed_commands(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/home/user/my tool.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/home/user/secrets.env")

    rendered = monitor.render_command(["--send-test-email"])

    assert rendered == runtime_command("steam_monitor --send-test-email --config-file '/home/user/my tool.conf' --env-file /home/user/secrets.env")


# Verifies a command that must stay path-free does not inherit the active paths
def test_paths_can_be_left_out(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/home/user/tool.conf")

    assert monitor.render_command(["--generate-config"], include_paths=False) == runtime_command("steam_monitor --generate-config")


# Verifies an explicitly supplied path is rendered even when the active ones are left out
def test_an_explicit_path_wins_over_the_active_ones(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/home/user/other.env")

    rendered = monitor.render_command(["--send-test-webhook"], include_paths=False, env_path="/home/user/chosen.env")

    assert rendered == runtime_command("steam_monitor --send-test-webhook --env-file /home/user/chosen.env")


# Verifies the disabled dotenv search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_dotenv_search_is_carried_only_where_it_is_accepted(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")

    assert monitor.render_command(["--doctor"]) == runtime_command("steam_monitor --doctor --env-file none")
    assert monitor.render_command(["--set-steam-api-key"]) == runtime_command("steam_monitor --set-steam-api-key")
    assert monitor.render_command(["--setup"]) == runtime_command("steam_monitor --setup")


# Verifies the disabled config search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_config_search_is_carried_only_where_it_is_accepted(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "CONFIG_DISCOVERY_DISABLED", True)

    assert monitor.render_command(["--doctor"]) == runtime_command("steam_monitor --doctor --config-file none")
    assert monitor.render_command(["--set-steam-api-key"]) == runtime_command("steam_monitor --set-steam-api-key --config-file none")
    assert monitor.render_command(["--setup"]) == runtime_command("steam_monitor --setup")
    assert monitor.render_command(["--doctor"], include_paths=False) == runtime_command("steam_monitor --doctor")


# Verifies arguments containing spaces are quoted for the shell the user pastes into
def test_windows_quoting_uses_double_quotes(monkeypatch):
    monkeypatch.setattr("sys.argv", ["C:\\\\tools\\\\steam_monitor.exe"])
    monkeypatch.setattr(monitor, "system", lambda: "Windows")

    assert monitor.quote_command_argument("C:\\Program Files\\tool.conf") == '"C:\\Program Files\\tool.conf"'
    assert monitor.quote_command_argument("--version") == "--version"


# Verifies the optional artwork install hint follows the same install detection as every other command
def test_the_artwork_install_hint_follows_the_install_method(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    assert monitor.ntfy_images_install_command() == 'pip3 install "steam_monitor[ntfy-images]"'

    monkeypatch.setattr("sys.argv", ["/home/user/steam_monitor.py"])
    assert monitor.ntfy_images_install_command().startswith('pip3 install "Pillow')


# Verifies a described secret discloses no part of its value, since diagnostic output reaches public bug reports
def test_a_described_secret_discloses_nothing():
    secret = "ABCDEFGHIJKLMNOP"

    described = str(monitor.secret_fields(secret, "STEAM_API_KEY"))

    for length in range(2, len(secret) + 1):
        assert secret[:length] not in described
        assert secret[-length:] not in described


# Verifies a short secret is described the same way as a long one, since only its presence is reported
def test_a_short_secret_is_described_the_same_way():
    assert monitor.secret_fields("ab")["value"] == "set"
    assert monitor.secret_fields("short")["value"] == "set"


# Verifies an absent secret is named as absent instead of reading as a value that is present
def test_an_absent_secret_is_reported_as_not_set():
    assert monitor.secret_fields("")["value"] == "not set"
    assert monitor.secret_fields(None)["value"] == "not set"


# Verifies an unedited placeholder is reported as absent rather than as a loaded secret
def test_a_placeholder_secret_is_reported_as_not_set():
    assert monitor.secret_fields("your_steam_api_key", "STEAM_API_KEY")["value"] == "not set"


# The diagnostic line is documented as comma-separated key=value fields, so the length travels as its own field
@pytest.mark.parametrize("key, value, fields", [
    ("STEAM_API_KEY", "0123456789ABCDEF0123456789ABCDEF", {"value": "set", "chars": 32}),
    ("SMTP_PASSWORD", "a-password-the-user-picked", {"value": "set", "chars": None}),
    ("STEAM_API_KEY", "", {"value": "not set", "chars": None}),
])
def test_no_secret_field_value_carries_a_comma(key, value, fields):
    assert monitor.secret_fields(value, key) == fields
    assert all("," not in str(part) for part in fields.values())


# Verifies the setup advice names the files this run was given instead of sending the user to the default ones
def test_setup_advice_names_the_files_this_run_was_given(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/home/user/steam_monitor.py", "--set-smtp-password"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/steam.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/steam.env")

    advice = monitor.classify_recovery_error(ValueError("The mail server settings are incomplete"), context="set_smtp_password")

    assert runtime_command("run python3 steam_monitor.py --setup --config-file /etc/steam.conf --env-file /etc/steam.env") in advice.fix


# Verifies the printed-command renderer takes the family's two shared parameters before any tool-specific one
def test_the_command_renderer_shares_one_contract():
    parameters = list(inspect.signature(monitor.render_command).parameters.values())
    assert [parameter.name for parameter in parameters[:2]] == ["arguments", "include_paths"]
    assert [parameter.default for parameter in parameters[:2]] == [None, True]
    # A tool-specific extra is keyword-only, so a positional call copied from a sibling cannot bind to it
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[2:])


# Verifies the renderer with no arguments prints the bare command, which is what the help screen puts before each example
def test_the_renderer_with_no_arguments_prints_the_bare_command():
    prefix = monitor.render_command(include_paths=False)
    assert prefix and not prefix.endswith(" ")
    assert monitor.render_command(["--doctor"], include_paths=False) == f"{prefix} --doctor"
