"""Tests the startup summary row model, its per-row routing, truncation, the grouped help and the cross-tool wording."""

from command_expectations import runtime_command
import ast
import argparse
from io import StringIO
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import steam_monitor as monitor


SOURCE = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Runs one isolated command-line action against the working-tree script
def run_cli(*arguments):
    return subprocess.run([sys.executable, str(PROJECT_ROOT / "steam_monitor.py"), *arguments], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)


# Verifies the selected Steam banner remains exact and version independent
def test_selected_banner_exact_content():
    assert monitor.STARTUP_BANNER == r"""
 .---------------.    ____  _
|         .--.   |   / ___|| |_ ___  __ _ _ __ ___
|    O===|  O |  |   \___ \| __/ _ \/ _` | '_ ` _ \
|   /     '--'   |    ___) | ||  __/ (_| | | | | | |
|  O             |   |____/ \__\___|\__,_|_| |_| |_|
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""


# Verifies the art is portable, bounded and free of trailing whitespace
def test_banner_ascii_width_and_whitespace():
    monitor.STARTUP_BANNER.encode("ascii")
    lines = monitor.STARTUP_BANNER.splitlines()
    assert max(map(len, lines)) <= 90
    assert all(line == line.rstrip() for line in lines)


# Verifies the Steam wordmark matches the standard FIGlet rows at the shared body column
def test_banner_steam_wordmark_rows():
    assert [line[21:] for line in monitor.STARTUP_BANNER.splitlines()[1:6]] == [
        " ____  _",
        "/ ___|| |_ ___  __ _ _ __ ___",
        "\\___ \\| __/ _ \\/ _` | '_ ` _ \\",
        " ___) | ||  __/ (_| | | | | | |",
        "|____/ \\__\\___|\\__,_|_| |_| |_|",
    ]


# Verifies the Monitor wordmark matches the standard FIGlet rows at the shared body column
def test_banner_monitor_wordmark_rows():
    assert [line[21:] for line in monitor.STARTUP_BANNER.splitlines()[7:12]] == [
        " __  __             _ _",
        "|  \\/  | ___  _ __ (_) |_ ___  _ __",
        "| |\\/| |/ _ \\| '_ \\| | __/ _ \\| '__|",
        "| |  | | (_) | | | | | || (_) | |",
        "|_|  |_|\\___/|_| |_|_|\\__\\___/|_|",
    ]


# Verifies the printed version stays dynamic and followed by one blank line
def test_banner_dynamic_version_line(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERSION", "9.9-test")
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monitor.print_startup_banner()
    assert capsys.readouterr().out == monitor.STARTUP_BANNER + "\n" + (" " * 21) + "v9.9-test\n\n"


# Verifies Steam, Monitor and the version share the same body column
def test_banner_version_alignment():
    banner_lines = monitor.STARTUP_BANNER.splitlines()
    steam_body_column = banner_lines[2].index("/ ___")
    monitor_body_indent = len(banner_lines[8]) - len(banner_lines[8].lstrip())
    version_indent = len(" " * 21) - len((" " * 21).lstrip())
    assert steam_body_column == monitor_body_indent == version_indent


# Verifies version output stays one line and excludes the startup art
def test_version_output_is_machine_friendly():
    result = run_cli("--version")
    assert result.returncode == 0
    assert result.stdout.splitlines() == [f"steam_monitor.py v{monitor.VERSION}"]
    assert monitor.STARTUP_BANNER.splitlines()[1] not in result.stdout


# Verifies generated config output begins with content and excludes the startup art
def test_generate_config_output_is_machine_friendly():
    result = run_cli("--generate-config")
    assert result.returncode == 0
    assert result.stdout.startswith("# Get your Steam Web API key")
    assert monitor.STARTUP_BANNER.splitlines()[1] not in result.stdout


# Verifies a refused combination names the option as it was typed rather than as argparse stores it
def test_a_refused_combination_names_the_positional_by_its_metavar():
    result = run_cli("--set-steam-api-key", "76561198000000000")

    assert result.returncode != 0
    assert "--set-steam-api-key cannot be combined with STEAM_TARGET" in result.stderr
    assert "--steam64-id" not in result.stderr


# Verifies an option is named by the spelling the user typed, not by its first alias
@pytest.mark.parametrize("typed", ["--verbose", "--debug"])
def test_a_refused_combination_names_the_option_that_was_typed(typed):
    result = run_cli("--set-steam-api-key", typed)

    assert result.returncode != 0
    assert f"--set-steam-api-key cannot be combined with {typed}" in result.stderr


# Verifies help shows one startup banner
def test_help_shows_one_startup_banner():
    result = run_cli("--help")
    assert result.returncode == 0
    assert result.stdout.count(" .---------------.") == 1


# Enables colour with a deterministic style map
@pytest.fixture
def colored(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Verifies the liveness banner timestamp carries the timestamp colour instead of the generic date colour
def test_liveness_check_timestamp_uses_timestamp_style(colored):
    assert monitor._colorize_line("Liveness check, timestamp:\tWed 26 Aug 2026, 20:23:03") == f"Liveness check, timestamp:\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}"


# Verifies a startup row reporting a switched feature carries the boolean colours like a True or False row
@pytest.mark.parametrize(("value", "part"), [("Enabled", "boolean_true"), ("True", "boolean_true"), ("Disabled", "boolean_false"), ("False", "boolean_false")])
def test_startup_rows_colour_a_switched_feature(colored, value, part):
    line = monitor._colorize_line(f"* Terminal truncation:          {value}")
    assert line == f"* Terminal truncation:          {colored[part]}{value}{monitor.ANSI_RESET}"


# Verifies a sentence that only mentions a presence state or answers with an English "no" stays plain, so a
# healthy report does not read as a failure
@pytest.mark.parametrize("line", [
    "* Monitoring healthy for 76561198128683189. The user is offline with no status or game change since the last check",
    "* Monitoring healthy for 76561198128683189. The user is online with no status or game change since the last check",
    "* No .env file found, reloading exported environment variables only",
    "* No recent achievements found or access is restricted by the user's privacy settings.",
    "* Polling intervals:           60 seconds while offline, 30 seconds while online",
    "Send a webhook alert when the user goes offline?",
])
def test_a_mentioned_state_or_english_no_is_not_painted(colored, line):
    spans = re.findall(r"\x1b\[[0-9;]*m(.*?)\x1b\[0m", monitor._colorize_line(line))
    assert not [span for span in spans if re.search(r"(?i)\b(online|offline|away|snooze|yes|no)\b", span)]


# Verifies a state the tool reports in capitals still carries its own colour
@pytest.mark.parametrize(("state", "part"), [("ONLINE", "status_online"), ("ACTIVE", "status_online"), ("OFFLINE", "status_offline"), ("INACTIVE", "status_offline"), ("AWAY", "status_away"), ("SNOOZE", "status_snooze")])
def test_a_reported_state_keeps_its_colour(colored, state, part):
    assert f"{colored[part]}{state}{monitor.ANSI_RESET}" in monitor._colorize_line(f"*** User got {state} !")


# Verifies a Yes or No answer is coloured only as the whole value of a labelled row
def test_an_answer_row_is_coloured_like_a_boolean(colored):
    assert monitor._colorize_line("* Friends check:               Yes") == f"* Friends check:               {colored['boolean_true']}Yes{monitor.ANSI_RESET}"
    assert monitor._colorize_line("* Friends check:               No") == f"* Friends check:               {colored['boolean_false']}No{monitor.ANSI_RESET}"


# Verifies the startup banner uses only its explicitly selected colours
def test_startup_banner_uses_only_its_own_colours(colored, capsys):
    monitor.print_startup_banner()
    output = capsys.readouterr().out
    sequences = set(re.findall(r"\x1b\[[0-9;]*m", output))
    assert sequences <= {colored["header"], colored["info"], monitor.ANSI_RESET}
    for line in monitor.STARTUP_BANNER.splitlines():
        if line:
            assert f"{colored['header']}{line}{monitor.ANSI_RESET}" in output


# Verifies every identity value is coloured for what it is: an id, a name or a link
def test_identity_values_are_coloured_by_their_kind(colored):
    assert monitor._colorize_line("* Target:                       76561198128683189") == f"* Target:                       {colored['id']}76561198128683189{monitor.ANSI_RESET}"
    assert monitor._colorize_line("Steam64 ID:\t\t\t76561198128683189") == f"Steam64 ID:\t\t\t{colored['id']}76561198128683189{monitor.ANSI_RESET}"
    assert monitor._colorize_line("Display name:\t\t\tmisiektoja") == f"Display name:\t\t\t{colored['username']}misiektoja{monitor.ANSI_RESET}"
    assert monitor._colorize_line("Profile URL:\t\t\thttps://steamcommunity.com/id/misiektoja") == f"Profile URL:\t\t\t{colored['link']}https://steamcommunity.com/id/misiektoja{monitor.ANSI_RESET}"


# Verifies a game title is coloured whatever punctuation it contains, so a feed does not colour only some rows
@pytest.mark.parametrize("name", ["Counter-Strike 2", "Assassin's Creed Valhalla", "Tom Clancy's Rainbow Six Siege", "S.T.A.L.K.E.R. 2", "Ratchet & Clank: Rift Apart"])
def test_game_titles_with_punctuation_are_coloured_whole(colored, name):
    assert f"{colored['game']}{name}{monitor.ANSI_RESET}" in monitor._colorize_line(f"Steam user misiektoja started playing '{name}'")


# Verifies two quoted titles on one line stay two names, since the closing quote rule could have joined them
def test_two_quoted_titles_on_one_line_stay_separate(colored):
    result = monitor._colorize_line("Steam user misiektoja changed game from 'Portal 2' to 'Half-Life: Alyx' after 2 hours")

    assert f"{colored['game']}Portal 2{monitor.ANSI_RESET}" in result
    assert f"{colored['game']}Half-Life: Alyx{monitor.ANSI_RESET}" in result


# Verifies quoted values shaped like a file name or a path stay plain, since a log destination is not a title
@pytest.mark.parametrize("value", ["steam_misiektoja_last_status.json", "/var/log/steam.log", "~/logs/output.txt", "C:\\Users\\me\\state.json"])
def test_quoted_file_and_path_values_stay_plain(colored, value):
    line = f"* Last status loaded from file '{value}'"

    assert monitor._colorize_line(line) == line


# Verifies a quoted placeholder inside a printed command stays plain, since it is text to replace rather than a title
@pytest.mark.parametrize("line", ["Run: steam_monitor '<steam64_id>'", "Replace '<topic>' with your own ntfy topic"])
def test_quoted_command_placeholders_stay_plain(colored, line):
    assert colored["game"] not in monitor._colorize_line(line)


# Verifies a quoted command-line option is left plain, since it is text to retype rather than a title
def test_quoted_command_options_stay_plain(colored):
    assert colored["game"] not in monitor._colorize_line("Replace '--env-file none' with a writable path")


# Verifies a quoted fragment of a URL stays plain, since it is a piece of an address rather than a title
@pytest.mark.parametrize("value", ["?code=", "&state="])
def test_quoted_url_fragments_stay_plain(colored, value):
    line = f"Copy everything after '{value}' from the address bar."

    assert monitor._colorize_line(line) == line


# Verifies every part the shipped theme offers is actually looked up somewhere, so a documented setting cannot do nothing
def test_every_theme_part_is_used():
    looked_up = set(re.findall(r"""colorize\(\s*["']([a-z_]+)["']""", SOURCE))
    looked_up |= set(re.findall(r"""_COLOR_STYLES\.get\(["']([a-z_]+)["']""", SOURCE))
    looked_up |= set(re.findall(r"""(?:style_name|state_style|key) = ["']([a-z_]+)["']""", SOURCE))
    looked_up |= set(re.findall(r""",\s*["']([a-z_]+)["']\),?\s*$""", SOURCE, re.M))
    looked_up |= set(re.findall(r"""["'][A-Za-z ]+["']:\s*["']([a-z_]+)["']""", SOURCE))

    assert not set(monitor.DEFAULT_COLOR_THEME) - looked_up


# Verifies argparse never adds a palette of its own, which from Python 3.14 would survive --no-color
def test_argparse_adds_no_palette_of_its_own():
    expected = {"color": False} if sys.version_info >= (3, 14) else {}

    assert monitor.argparse_color_kwargs() == expected


# Verifies the switch is actually passed to the parser, since the helper alone colours nothing
def test_the_parser_is_built_with_the_argparse_colour_switch():
    construction = re.search(r"\n    parser = \w+\(\n(.*?)\n\n", SOURCE, re.S)

    assert construction is not None, "the parser construction could not be found"
    assert "**argparse_color_kwargs()" in construction.group(1)


# Verifies a link printed inside a sentence is coloured too, not only a labelled URL row
def test_links_in_sentences_are_coloured(colored):
    line = monitor._colorize_line(f"Guide: {monitor.QUICK_START_GUIDE_URL}")
    assert line == f"Guide: {colored['link']}{monitor.QUICK_START_GUIDE_URL}{monitor.ANSI_RESET}"


class FakeStream:
    """A stream stand-in that reports whatever the test needs isatty() to say."""

    def __init__(self, interactive):
        self.interactive = interactive

    def isatty(self):
        return self.interactive


# Verifies the NO_COLOR convention is honoured on a terminal that would otherwise receive colour
def test_no_color_in_the_environment_switches_colour_off(monkeypatch):
    monkeypatch.setattr(monitor.sys, "stdin", FakeStream(True))
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert monitor._stream_supports_color(FakeStream(True)) is True

    monkeypatch.setenv("NO_COLOR", "1")

    assert monitor._stream_supports_color(FakeStream(True)) is False


# Verifies a config written against the pre-rename 'steam_id' key still colours identifiers
def test_legacy_theme_key_still_applies(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"steam_id": "red"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(sys.stdout)
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("red")


# Verifies the current key name wins when a config sets both the old and the new name
def test_current_theme_key_wins_over_the_legacy_name(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"steam_id": "red", "id": "green"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(sys.stdout)
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("green")


# Verifies the Setup Wizard heading keeps the newline inside the sibling-style header span
def test_setup_wizard_heading_uses_header_colour(colored, capsys):
    def interrupt(_prompt):
        raise KeyboardInterrupt

    assert monitor.run_setup_wizard(input_func=interrupt, interactive=True) == 1
    assert f"{colored['header']}Setup Wizard\n{monitor.ANSI_RESET}\n" in capsys.readouterr().out


@pytest.fixture
# Restores every module-level setting the summary reads
def summary_globals(monkeypatch):
    snapshot = {name: value for name, value in vars(monitor).items() if name.isupper()}
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)


# Collects what the terminal and the log file were each given, the way the real Logger splits them
class RoutedStream:
    def __init__(self):
        self.terminal = []
        self.log = []

    # Records text meant only for the reader at the terminal
    def terminal_only(self, message):
        self.terminal.append(message)

    # Records text meant only for the log file
    def log_only(self, message):
        self.log.append(message)

    # Present because every stream the tool writes to has one
    def flush(self):
        pass

    # Returns what the terminal was shown
    def terminal_text(self):
        return "".join(self.terminal)

    # Returns what the log file kept
    def log_text(self):
        return "".join(self.log)


# Collects the summary the given view would print at the terminal
def rendered_summary(rows, show_full):
    stream = RoutedStream()
    monitor.emit_startup_summary(rows, show_full=show_full, stream=stream)
    return stream.terminal_text()


# Verifies the log file keeps the complete summary even when the terminal was shown the concise view
def test_the_log_file_keeps_the_full_summary_whatever_the_terminal_showed(summary_globals):
    rows = [
        monitor.StartupSummaryRow("Always", "a", concise=True),
        monitor.StartupSummaryRow("Verbose only", "b"),
        monitor.StartupSummaryRow("Concise only", "c", concise=True, full=False),
    ]
    stream = RoutedStream()

    monitor.emit_startup_summary(rows, show_full=False, stream=stream)

    assert "Verbose only" not in stream.terminal_text()
    assert "Verbose only" in stream.log_text()
    # The orientation row has a better place in the full view, so the log keeps its own version instead
    assert "Concise only" not in stream.log_text()


# Verifies each row is routed independently rather than the whole block being shown or hidden together
def test_rows_are_routed_independently(summary_globals):
    rows = [
        monitor.StartupSummaryRow("Always", "a", concise=True),
        monitor.StartupSummaryRow("Verbose only", "b"),
        monitor.StartupSummaryRow("Concise only", "c", concise=True, full=False),
    ]

    concise = rendered_summary(rows, show_full=False)
    full = rendered_summary(rows, show_full=True)

    assert "Always" in concise and "Always" in full
    assert "Verbose only" not in concise and "Verbose only" in full
    assert "Concise only" in concise and "Concise only" not in full


# Verifies the real summary hides the diagnostic rows until the full view is asked for
def test_the_real_summary_hides_diagnostics_until_asked(summary_globals):
    rows = monitor.build_startup_summary("76561198000000000", "tool.conf", None, "tool.log")

    concise = rendered_summary(rows, show_full=False)
    full = rendered_summary(rows, show_full=True)

    assert "Polling intervals" in concise
    assert "Config" in concise
    # Points a newcomer at the two modes, so the full view has no reason to repeat it
    assert "More details" in concise and "More details" not in full
    assert "Output:" in concise and "Output:" not in full
    for label in ("Install method", "Secrets from dotenv", "Secrets from environment", "Verbose mode", "ASCII log separators"):
        assert label not in concise, f"{label} should not be in the concise view"
        assert label in full, f"{label} should be in the full view"


# Verifies the concise view points at the diagnostic modes and stops once one of them is on
def test_the_concise_summary_points_at_the_diagnostic_modes(summary_globals):
    rows = monitor.build_startup_summary("76561198000000000", "tool.conf", None, "tool.log")

    concise = rendered_summary(rows, show_full=False)
    full = rendered_summary(rows, show_full=True)

    assert "* More details:" in concise
    assert "use --verbose or --debug" in concise
    assert "* More details:" not in full


# Verifies both notification channels are reported with the categories that are actually enabled
def test_the_notification_rollups_name_their_categories(monkeypatch, summary_globals):
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)

    concise = rendered_summary(monitor.build_startup_summary("76561198000000000", "tool.conf", None, "tool.log"), show_full=False)

    assert "Notifications (email)" in concise
    assert "On (online and offline changes, game changes)" in concise
    assert "Notifications (webhook)" in concise
    assert "Off" in concise


# Verifies truncation measures what is displayed, so colour codes do not eat into the visible width
def test_truncation_measures_display_width_not_escape_sequences():
    pytest.importorskip("wcwidth")

    truncated = monitor.truncate_string_per_line("\x1b[31m0123456789ABCDEF\x1b[0m", 10)

    assert re.sub(r"\x1b\[[0-9;]*m", "", truncated) == "0123456789"


# Verifies a double-width character costs two columns, so a CJK game title does not wrap past the limit
def test_truncation_counts_double_width_characters():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("原神原神原神", 4) == "原神"


# Verifies each line is measured on its own rather than the whole message being cut at one offset
def test_truncation_applies_to_every_line():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("abcdef\nabcdef", 3) == "abc\nabc"


# Verifies the command line width wins over the configured one
def test_truncation_width_prefers_the_command_line():
    assert monitor.resolve_truncate_chars(80, 120, False) == 80
    assert monitor.resolve_truncate_chars(None, 120, False) == 120


# Verifies truncation is off without a log file, where the trimmed text would be lost for good
def test_truncation_is_disabled_when_logging_is_disabled():
    assert monitor.resolve_truncate_chars(120, 120, True) == 0


# Verifies the sentinel expands to the detected terminal width and says what it detected
def test_truncation_sentinel_expands_to_the_terminal_width(monkeypatch, capsys):
    monkeypatch.setattr(monitor.shutil, "get_terminal_size", lambda: os.terminal_size((132, 40)))

    assert monitor.resolve_truncate_chars(999, 0, False) == 132
    assert "132 characters" in capsys.readouterr().out


# Verifies the notification rollups wrap into the value column rather than running off the terminal
def test_the_notification_rollups_wrap_into_their_column(summary_globals):
    rendered = rendered_summary([monitor.StartupSummaryRow("Notifications (email)", "On (" + ", ".join(["category"] * 20) + ")", concise=True)], show_full=False)

    lines = rendered.split("\n")
    assert len(lines) > 1
    assert all(len(line) <= 100 for line in lines)
    # Continuation lines line up under the value rather than starting at the left margin
    assert lines[1].startswith(" " * 32)


# Verifies the help examples are grouped by what the reader is trying to do
def test_the_help_examples_are_grouped():
    epilog = monitor.help_examples()

    for group in ("Getting started", "Notifications", "Information and diagnostics"):
        assert f"\n{group}:\n" in epilog, f"the {group} group is missing"
    assert epilog.startswith("Examples:")
    assert monitor.QUICK_START_GUIDE_URL in epilog


# Verifies every example command is written for the detected install rather than hardcoded
def test_the_help_examples_suit_the_install(monkeypatch):
    monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    assert runtime_command("steam_monitor --setup") in monitor.help_examples()

    monkeypatch.setattr("sys.argv", ["/home/user/steam_monitor.py"])
    assert runtime_command("python3 steam_monitor.py --setup") in monitor.help_examples()


# Verifies the examples reach the commands a newcomer needs first
@pytest.mark.parametrize("flag", ["--setup", "--doctor", "--set-steam-api-key", "--send-test-email", "--send-test-webhook", "--debug"])
def test_the_help_examples_cover_the_first_commands(flag):
    assert flag in monitor.help_examples()


# Verifies a row is verbose-only unless it opts in, which is what keeps the concise view short
def test_rows_are_verbose_only_by_default():
    row = monitor.StartupSummaryRow("Label", "value")

    assert row.concise is False
    assert row.full is True


# Verifies a feature row reaches the concise view only when that feature is switched on
@pytest.mark.parametrize("enabled", [True, False])
def test_a_feature_row_is_concise_only_when_it_is_on(monkeypatch, summary_globals, enabled):
    monkeypatch.setattr(monitor, "FRIENDS_CHECK", enabled)

    concise = rendered_summary(monitor.build_startup_summary("76561198000000000", "tool.conf", None, None), show_full=False)

    assert ("Friends tracking" in concise) is enabled


# Verifies the concise view ends by naming the flags that reveal the rest
def test_the_concise_view_points_at_the_verbose_flags(summary_globals):
    concise = rendered_summary(monitor.build_startup_summary("76561198000000000", "tool.conf", None, None), show_full=False)

    assert concise.rstrip().endswith("use --verbose or --debug")


# Verifies the welcome screen keeps the block shape shared with the sibling tools
def test_the_welcome_screen_keeps_the_shared_block_shape(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])

    monitor.print_welcome_screen(interactive=False)
    lines = capsys.readouterr().out.split("\n")

    # Label on its own line, command indented four spaces below it, one blank line between blocks
    for label, command in (
        ("Quickest start (already configured):", "steam_monitor <steam_target>"),
        ("Easiest start (guided setup wizard):", "steam_monitor --setup"),
        ("Check setup before monitoring:", "steam_monitor --doctor <steam_target>"),
    ):
        index = lines.index(label)
        assert lines[index + 1] == f"    {runtime_command(command)}", lines[index + 1]
        assert lines[index + 2] == ""
    # These two are single lines rather than blocks, and the guide value is column aligned
    assert runtime_command("Full options: steam_monitor --help") in lines
    assert f"Guide:        {monitor.QUICK_START_GUIDE_URL}" in lines


# The wording these tools share, so a user who runs two of them reads the same sentences in both.
# Each entry was copied from spotify_monitor, spotify_profile_monitor and instagram_monitor, where all
# three already agree. Changing one here without changing it there is the drift this test exists to catch.
CROSS_TOOL_STRINGS = (
    # Doctor
    "Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.",
    "No dotenv file selected",
    "Using environment variables and other configured sources",
    "No secrets loaded",
    "Nothing was read from a dotenv file, the environment, the configuration file or the command line",
    "The requested dotenv file was not found",
    "Email notifications are disabled",
    "Webhook alerts are disabled",
    "Doctor will not write files. Each approved test sends one real message.",
    "Send one test email now? This will deliver a real message",
    "Doctor test email delivered",
    "Doctor test email delivery failed",
    "Doctor test webhook through {provider} delivered",
    "Doctor test webhook through {provider} delivery failed",
    "Test email was not sent",
    "Test webhook through {provider} was not sent",
    "One real test email was sent after confirmation",
    "One real test webhook was sent after confirmation",
    "The approved test email could not be delivered",
    "The approved test webhook could not be delivered",
    "You declined the real delivery test",
    "Run doctor again and approve the email test when ready",
    "Run doctor again and approve the webhook test when ready",
    "Monitoring healthy for ",
    " since the last check",
    # Setup wizard
    "The setup wizard needs an interactive terminal (TTY).",
    "This asks a few questions and writes a ready-to-run configuration.",
    "Press Enter to accept the shown default. Ctrl+C cancels.",
    "Secrets go to the dotenv file. Non-secret settings go to the config file.",
    "Detected install method: ",
    "This value is required.",
    "Try entering the {label} again?",
    "Continue without the {label}? {consequence}",
    "Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.",
    "Configure email notifications?",
    "Which email notifications should be enabled?",
    "Set up webhook alerts (Discord, ntfy etc.)?",
    "Which webhook service should receive alerts?",
    "Sends a Discord embed to one channel webhook.",
    "Sends a native notification to one ntfy topic URL.",
    "Which webhook URL should be used?",
    "Keep the saved URL",
    "Paste a new URL",
    "Keeps the private value without displaying or changing it.",
    "Paste the Discord webhook URL",
    "Paste the ntfy topic URL or ntfy.sh topic name",
    "In ntfy: choose a hard-to-guess topic. Paste its complete topic URL, or just the topic name when it is hosted on ntfy.sh.",
    "That does not look like a complete HTTPS webhook URL. Copy it from the webhook service and try again.",
    "Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores.",
    "Which ntfy authentication should be used?",
    "Paste the ntfy access token only",
    "Paste only the access token without a Bearer or Basic prefix.",
    "Which webhook alerts should be sent?",
    "Which setup section should be changed?",
    "Return to summary",
    "Keep every current answer.",
    "What would you like to do?",
    "Save settings",
    "Write the displayed settings to the selected files.",
    "Review or change settings",
    "Edit one section without losing the other answers.",
    "Discard answers and exit",
    "Leave the destination files unchanged.",
    "Discard all entered answers and exit?",
    "Run doctor now? It writes no files and offers real delivery tests only with separate approval.",
    "Persist this target in the generated config?",
    "Press Enter to accept the shown default. Ctrl+C cancels.",
    "The setup wizard needs an interactive terminal (TTY).",
    "Run --setup from an interactive shell or use --generate-config and edit the files manually.",
    "Start monitoring now? Monitoring will continue until Ctrl+C.",
    "seconds or use s/m/h/d",
    "  Enter a positive whole number.",
    "  This value is required.",
    "  Please answer 'y' or 'n'.",
    "  Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.",
    # Setup summary rows, which the sibling monitors render from the same aligned label list
    '("Persist target", ',
    '("Authentication status", ',
    '("Email", ',
    '("Email notifications", ',
    '("Webhook", ',
    '("Webhook alerts", ',
    '("Config destination", ',
    '("Dotenv destination", ',
    '("Install method", ',
)


# Verifies every sentence shared with the sibling monitors is still spelled the way they spell it
@pytest.mark.parametrize("text", CROSS_TOOL_STRINGS)
def test_the_cross_tool_wording_is_unchanged(text):
    assert text in SOURCE, text


# Verifies the config file decides screen clearing and colour before the banner, not the built-in defaults
def test_the_config_file_settings_reach_the_banner(tmp_path, monkeypatch):
    config = tmp_path / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\nCOLORED_OUTPUT = False\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor.sys, "argv", ["steam_monitor", "--config-file", str(config)])

    monitor.apply_early_output_config()

    assert monitor.CLEAR_SCREEN is False
    assert monitor.COLORED_OUTPUT is False


# Verifies an unreadable or absent config file leaves the built-in output settings alone
@pytest.mark.parametrize("content", [None, "CLEAR_SCREEN = (", "CLEAR_SCREEN = 'yes'"])
def test_an_unusable_config_leaves_the_output_settings_alone(tmp_path, monkeypatch, content):
    config = tmp_path / "steam_monitor.conf"
    if content is not None:
        config.write_text(content, encoding="utf-8")
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor.sys, "argv", ["steam_monitor", "--config-file", str(config)])

    monitor.apply_early_output_config()

    assert monitor.CLEAR_SCREEN is True
    assert monitor.COLORED_OUTPUT is True


# Verifies '--config-file none' is respected before argparse, so no file is read to decide output settings
def test_config_file_none_skips_the_early_config_read(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "find_config_file", lambda _path=None: pytest.fail("a config file was searched for"))
    monkeypatch.setattr(monitor.sys, "argv", ["steam_monitor", "--config-file", "none"])

    monitor.apply_early_output_config()

    assert monitor.COLORED_OUTPUT is True


# Verifies the config path is read from argv in both spellings argparse accepts
@pytest.mark.parametrize("arguments,expected", [
    (["--config-file", "a.conf"], "a.conf"),
    (["--config-file=a.conf"], "a.conf"),
    (["--doctor"], None),
    (["--config-file"], None),
])
def test_the_early_config_path_is_read_from_argv(arguments, expected):
    assert monitor.early_config_file_argument(arguments) == expected


# Verifies every doctor result marker keeps its bracketed spelling and its own colour
def test_doctor_markers_are_bracketed_and_coloured(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    assert [monitor.render_doctor_marker(status) for status in ("PASS", "WARN", "FAIL", "SKIP")] == ["[PASS]", "[WARN]", "[FAIL]", "[SKIP]"]

    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)})
    coloured = {status: monitor.render_doctor_marker(status) for status in monitor.DOCTOR_MARK_STYLES}
    for status, rendered in coloured.items():
        assert rendered.endswith(f"[{status}]{monitor.ANSI_RESET}"), status
    assert len(set(coloured.values())) == len(coloured)


# Verifies the doctor sections keep the order the sibling monitors render them in
def test_the_doctor_section_order_matches_the_sibling_tools():
    assert monitor.DOCTOR_SECTIONS == ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")


# Verifies the install method is named with the vocabulary every one of these tools prints
def test_the_install_method_vocabulary_is_shared():
    assert (monitor.INSTALL_METHOD_PYPI, monitor.INSTALL_METHOD_SCRIPT) == ("pip", "manual")
    assert monitor.install_method_display_name("pip") == "PyPI install"
    assert monitor.install_method_display_name("manual") == "downloaded script"


# The rows shared with the sibling monitors, in the order every one of them prints
SHARED_ROW_ORDER = ("Target", "Polling intervals", "Notifications (email)", "Email transport", "Email recipient", "Notifications (webhook)", "Webhook provider", "Delivery confirmations", "Output", "Output logging", "Config", "Dotenv", "Liveness output", "CSV output", "Terminal truncation", "Process id", "Python version", "Operating system", "Install method", "Secrets from dotenv", "Secrets from environment", "Secrets from config file", "Secrets from command line", "TLS verification", "ASCII log separators", "Coloured output", "Verbose mode", "Debug mode", "More details")


# Verifies the status file row names the file the run will use, built from the target when no path was given
def test_the_status_file_row_names_the_file_the_run_will_use(monkeypatch, summary_globals):
    monkeypatch.setattr(monitor, "STEAM_STATUS_FILE", "")

    named = [row.value for row in monitor.build_startup_summary("76561198000000000", "tool.conf", None, "tool.log") if row.label == "Status file"]
    unknown = [row.value for row in monitor.build_startup_summary(None, "tool.conf", None, "tool.log") if row.label == "Status file"]

    assert named == ["steam_76561198000000000_last_status.json"]
    assert unknown == ["None"]


# Verifies the shared rows keep the order and the label column width every sibling monitor prints
def test_the_shared_summary_rows_match_the_sibling_tools(summary_globals):
    rows = monitor.build_startup_summary("76561198000000000", "tool.conf", ".env", "tool.log")

    assert [row.label for row in rows if row.label in SHARED_ROW_ORDER] == list(SHARED_ROW_ORDER)
    # The renderer pads "<label>:" into a 30-character column, so a longer label swallows the separating space
    assert max(len(row.label) for row in rows) <= 28


# Verifies a run without a target reports the shared three-line block rather than dumping the whole help screen
def test_a_missing_target_reports_the_shared_error_block():
    result = run_cli("--config-file", "none", "--env-file", "none")

    assert result.returncode == 1
    assert "* Error: A Steam profile target needs to be defined" in result.stdout
    assert f"To fix: Pass the profile to watch as a {monitor.STEAM_TARGET_FORMS}" in result.stdout
    assert f"Guide: {monitor.QUICK_START_GUIDE_URL}" in result.stdout
    assert "usage: steam_monitor" not in result.stdout + result.stderr


# Verifies both delivery announcements are painted for their channel, so the two theme keys are not settings that do nothing
@pytest.mark.parametrize("line,part", [
    ("* Sending email notification to alerts@example.test", "email"),
    ("* Sending webhook notification", "webhook"),
])
def test_a_delivery_announcement_is_painted_for_its_channel(colored, line, part):
    assert monitor._colorize_line(line).startswith(colored[part])


# Verifies the two channels keep the values every sibling monitor ships, so a channel reads the same in all of them
def test_the_delivery_channels_keep_the_shared_colours():
    assert monitor.DEFAULT_COLOR_THEME["email"] == "bright_cyan"
    assert monitor.DEFAULT_COLOR_THEME["webhook"] == "bright_blue"


# Verifies the line colouriser leaves a link inside an already styled span alone, so styles never nest
def test_a_link_inside_a_styled_span_is_not_recoloured(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)})
    styled = monitor.colorize("info", "Guide: https://example.test/page")

    assert monitor.apply_color_to_text(styled) == styled
    assert monitor.apply_color_to_text("Guide: https://example.test/page") == f"Guide: {monitor.colorize('link', 'https://example.test/page')}"


# Verifies a line the caller already styled keeps that style, so the whole-line rules never wrap it twice
def test_an_already_styled_line_is_not_wrapped_again(colored):
    styled = monitor.colorize("error", "  1 check(s) failed, 1 warning(s). Fix the failures above.")

    assert monitor.apply_color_to_text(styled) == styled


# Verifies a quoted command inside a styled span keeps the span's colour instead of being cut in half by a reset
def test_a_quoted_name_inside_a_styled_span_is_not_recoloured(colored):
    styled = monitor.colorize("info", "To fix: Save one with 'steam_monitor.py --set-steam-api-key', or export it")

    assert monitor.apply_color_to_text(styled) == styled


# Verifies the warnings printed while the configuration is resolved are coloured like every later line,
# which is what the stream installed before argparse is for
def test_the_early_stream_colours_a_warning_printed_before_the_log_opens(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    buffer = StringIO()

    monitor.ColorStream(buffer, truncate=False).write("* Warning: Configured webhook provider did not match the URL. Using Discord.\n")

    assert buffer.getvalue() == f"{colored['warning']}* Warning: Configured webhook provider did not match the URL. Using Discord.{monitor.ANSI_RESET}\n"


# Verifies the early stream leaves lines at full width, since truncation is only resolved once arguments are parsed
def test_the_early_stream_does_not_truncate(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 10)
    early, resolved = StringIO(), StringIO()

    monitor.ColorStream(early, truncate=False).write("a line that is well past ten columns\n")
    monitor.ColorStream(resolved).write("a line that is well past ten columns\n")

    assert early.getvalue() == "a line that is well past ten columns\n"
    assert resolved.getvalue() == "a line tha\n"


# Verifies the log file writer reaches the real terminal, so replacing the early stream never colours a line twice
def test_the_logger_unwraps_the_early_stream(monkeypatch, tmp_path):
    terminal = StringIO()
    monkeypatch.setattr(sys, "stdout", monitor.ColorStream(monitor.ColorStream(terminal, truncate=False)))

    logger = monitor.Logger(str(tmp_path / "steam_monitor.log"))
    try:
        assert logger.terminal is terminal
    finally:
        logger.logfile.close()


# Verifies the TLS row colours its state word, the one setting whose off state weakens a security property
def test_the_tls_row_colours_its_state(colored):
    on_row = monitor._colorize_line("* TLS verification:             On")
    off_row = monitor._colorize_line("* TLS verification:             Off, server certificates are not checked")

    assert on_row == f"* TLS verification:             {colored['boolean_true']}On{monitor.ANSI_RESET}"
    assert off_row == f"* TLS verification:             {colored['boolean_false']}Off{monitor.ANSI_RESET}, server certificates are not checked"


HELP_SAMPLE = """usage: monitor [-h] [--config-file PATH] [TARGET]

positional arguments:
  TARGET                The target to monitor

Configuration & dotenv files:
  --config-file PATH    Path to a config file
  -m, --check-interval SECONDS
                        Time between checks (default: 60)

Examples:

Getting started:
  # Guided setup, see https://example.invalid/guide/
  python3 monitor.py --setup <target>

Guide: https://example.invalid/guide/
"""

HELP_SAMPLE_EPILOG = HELP_SAMPLE[HELP_SAMPLE.index("Examples:"):]


# Enables colour with the shipped theme and returns the escape sequence of every part
@pytest.fixture
def help_palette(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Returns the sample help screen with the help palette applied
@pytest.fixture
def colored_help(help_palette):
    return monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG)


# Verifies colouring changes no character of the screen, since argparse laid out its columns on the plain text
def test_the_coloured_help_keeps_the_plain_layout(colored_help):
    assert monitor.ANSI_ESCAPE_RE.sub("", colored_help) == HELP_SAMPLE


# Verifies the argument groups and the example tasks share one heading colour, the anchors the reader scans for
def test_the_help_headings_carry_the_heading_colour(help_palette, colored_help):
    for heading in ("positional arguments:", "Configuration & dotenv files:", "Examples:", "Getting started:"):
        assert f"{help_palette['help_heading']}{heading}{monitor.ANSI_RESET}" in colored_help


# Verifies an option name and the value it takes are coloured apart, in the usage block and in the option rows
def test_the_help_option_names_and_their_values_are_coloured_apart(help_palette, colored_help):
    option = f"{help_palette['help_option']}--config-file{monitor.ANSI_RESET}"
    metavar = f"{help_palette['help_metavar']}PATH{monitor.ANSI_RESET}"

    assert f"{option} {metavar}" in colored_help
    assert f"[{option} {metavar}]" in colored_help
    assert f"{help_palette['help_usage']}usage:{monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['help_metavar']}TARGET{monitor.ANSI_RESET}                The target to monitor" in colored_help


# Verifies the examples separate the comment from the command and mark the value the reader has to replace
def test_the_help_examples_mark_comments_commands_and_placeholders(help_palette, colored_help):
    assert f"{help_palette['help_comment']}  # Guided setup" in colored_help
    assert f"{help_palette['help_command']}  python3 monitor.py --setup" in colored_help
    assert f"{help_palette['help_placeholder']}<target>{monitor.ANSI_RESET}" in colored_help


# Verifies a default note is dimmed and a documentation link keeps the shared link colour
def test_the_help_default_notes_and_links_stay_secondary(help_palette, colored_help):
    assert f"{help_palette['help_default']}(default: 60){monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['link']}https://example.invalid/guide/{monitor.ANSI_RESET}" in colored_help


# Verifies the help screen stays plain while colour is switched off, so --no-color and NO_COLOR clear all of it
def test_the_help_palette_switches_off_with_colour():
    assert monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG) == HELP_SAMPLE


# Verifies the finished help screen reaches the terminal untouched, past the colouriser that paints monitoring output
def test_the_help_screen_is_not_repainted_by_the_monitoring_rules(help_palette):
    buffer = StringIO()
    parser = monitor.ColoredHelpParser(prog="monitor", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config-file", metavar="PATH", help="Path to a config file")
    parser.print_help(monitor.ColorStream(buffer))

    written = buffer.getvalue()
    assert written == parser.format_help()
    assert help_palette["help_option"] in written


# Verifies a cut line closes the colour it opened, so the truncated tail does not paint every line printed after it
def test_a_truncated_line_closes_its_open_colour():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("\x1b[31m0123456789ABCDEF\x1b[0m", 10) == "\x1b[31m0123456789" + monitor.ANSI_RESET


# Verifies no extra reset is added when the colour closed before the cut or the line was never cut
def test_a_closed_or_uncut_colour_gains_no_extra_reset():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("\x1b[31m0123\x1b[0m456789ABCDEF", 10) == "\x1b[31m0123\x1b[0m456789"
    assert monitor.truncate_string_per_line("\x1b[31m0123\x1b[0m", 10) == "\x1b[31m0123\x1b[0m"
    assert monitor.truncate_string_per_line("0123456789ABCDEF", 10) == "0123456789"


# Verifies the setup screens colour their links, since they print before the output stream colouriser is installed
def test_setup_screen_links_are_coloured(monkeypatch):
    link = monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["link"])
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {"link": link})

    assert monitor.colorize_links("Guide: https://example.test/page") == f"Guide: {link}https://example.test/page{monitor.ANSI_RESET}"


# Verifies no setup screen prints a link without colouring it, which is how a plain link gets in
def test_no_setup_screen_prints_a_plain_link():
    setup = re.compile(r"^(?:run_setup_wizard|run_scrobble_health_setup_wizard|_wizard_|run_set_|run_browser_cookie_import|print_welcome_screen|print_doctor_next_steps|print_spotify_scrobble_app_guidance)")
    tree = ast.parse(Path(monitor.__file__).read_text(encoding="utf-8"))
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    plain = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"):
            continue
        nested = list(ast.walk(node))
        prints_link = any(isinstance(item, ast.Constant) and isinstance(item.value, str) and "http" in item.value for item in nested) or any(isinstance(item, ast.Name) and "URL" in item.id for item in nested)
        coloured = any(isinstance(item, ast.Name) and item.id in ("colorize", "colorize_links") for item in nested)
        owner, current = "", parents.get(node)
        while current is not None:
            if isinstance(current, ast.FunctionDef):
                owner = current.name
                break
            current = parents.get(current)
        if prints_link and not coloured and setup.match(owner):
            plain.append(f"{owner}:{node.lineno}")

    assert plain == []


# Verifies a fix block keeps its guide line a link while the rest of the block stays informational
def test_a_fix_block_guide_line_is_a_link(monkeypatch):
    link = monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["link"])
    info = monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["info"])
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {"link": link, "info": info})

    assert monitor.colorize_fix_line("To fix: Set the key then re-run") == f"{info}To fix: Set the key then re-run{monitor.ANSI_RESET}"
    assert monitor.colorize_fix_line("Guide: https://example.test/page") == f"Guide: {link}https://example.test/page{monitor.ANSI_RESET}"
    assert 'colorize("info", f"Guide:' not in Path(monitor.__file__).read_text(encoding="utf-8")


# Verifies the early peek carries the theme, since --help is printed and exited from inside argparse before the config load
def test_the_early_output_config_carries_the_help_theme(monkeypatch, tmp_path):
    (tmp_path / "steam_monitor.conf").write_text('COLOR_THEME = {"help_heading": "bright_red"}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "COLOR_THEME", {})
    monkeypatch.setattr(monitor, "CONFIG_DISCOVERY_DISABLED", False)
    monkeypatch.setattr(monitor.sys, "argv", ["steam_monitor", "--help"])

    monitor.apply_early_output_config()

    assert monitor.COLOR_THEME == {"help_heading": "bright_red"}
