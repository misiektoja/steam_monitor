"""Tests that printed commands, masked secrets and guide links match the detected install method."""

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
    assert monitor.render_command(["--version"]) == "python3 steam_monitor.py --version"


# Verifies the packaged console script is detected and rendered by its entry point name
def test_a_pypi_install_is_detected(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor", "--doctor"])

    assert monitor.install_method() == monitor.INSTALL_METHOD_PYPI
    assert monitor.install_method_display_name() == "PyPI install"
    assert monitor.render_command(["--version"]) == "steam_monitor --version"


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

    assert rendered == "steam_monitor --send-test-email --config-file '/home/user/my tool.conf' --env-file /home/user/secrets.env"


# Verifies a command that must stay path-free does not inherit the active paths
def test_paths_can_be_left_out(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/home/user/tool.conf")

    assert monitor.render_command(["--generate-config"], include_paths=False) == "steam_monitor --generate-config"


# Verifies an explicitly supplied path is rendered even when the active ones are left out
def test_an_explicit_path_wins_over_the_active_ones(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/home/user/other.env")

    rendered = monitor.render_command(["--send-test-webhook"], include_paths=False, env_path="/home/user/chosen.env")

    assert rendered == "steam_monitor --send-test-webhook --env-file /home/user/chosen.env"


# Verifies the disabled dotenv search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_dotenv_search_is_carried_only_where_it_is_accepted(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")

    assert monitor.render_command(["--doctor"]) == "steam_monitor --doctor --env-file none"
    assert monitor.render_command(["--set-steam-api-key"]) == "steam_monitor --set-steam-api-key"
    assert monitor.render_command(["--setup"]) == "steam_monitor --setup"


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


# Verifies a masked secret discloses no part of its value, since diagnostic output reaches public bug reports
def test_a_masked_secret_discloses_nothing():
    secret = "ABCDEFGHIJKLMNOP"

    masked = monitor.mask_secret(secret)

    assert masked == "<redacted>"
    for length in range(2, len(secret) + 1):
        assert secret[:length] not in masked
        assert secret[-length:] not in masked


# Verifies a short secret is not treated differently from a long one
def test_a_short_secret_is_masked_the_same_way():
    assert monitor.mask_secret("ab") == "<redacted>"
    assert monitor.mask_secret("short") == "<redacted>"


# Verifies an absent secret is named as absent instead of reading as a value that is present
def test_an_absent_secret_is_reported_as_not_set():
    assert monitor.mask_secret("") == "(not set)"
    assert monitor.mask_secret(None) == "(not set)"


# Verifies the setup advice names the files this run was given instead of sending the user to the default ones
def test_setup_advice_names_the_files_this_run_was_given(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/home/user/steam_monitor.py", "--set-smtp-password"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/steam.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/steam.env")

    advice = monitor.classify_recovery_error(ValueError("The mail server settings are incomplete"), context="set_smtp_password")

    assert "run python3 steam_monitor.py --setup --config-file /etc/steam.conf --env-file /etc/steam.env" in advice.fix
