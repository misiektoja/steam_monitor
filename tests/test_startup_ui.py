"""Tests the startup summary row model, its per-row routing, truncation and the grouped help."""

import pytest

import steam_monitor as monitor


@pytest.fixture
# Restores every module-level setting the summary reads
def summary_globals(monkeypatch):
    snapshot = {name: value for name, value in vars(monitor).items() if name.isupper()}
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)


# Collects the summary the given view would print
def rendered_summary(rows, show_full):
    lines = []
    monitor.emit_startup_summary(rows, show_full=show_full, printer=lines.append)
    return "\n".join(lines)


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
    rows = monitor.build_startup_summary("tool.conf", None, "tool.log")

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
    rows = monitor.build_startup_summary("tool.conf", None, "tool.log")

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

    concise = rendered_summary(monitor.build_startup_summary("tool.conf", None, "tool.log"), show_full=False)

    assert "Notifications (email)" in concise
    assert "On (online/offline, game)" in concise
    assert "Notifications (webhook)" in concise
    assert "Off" in concise


# Verifies a value longer than the configured width is cut with a visible marker rather than silently
def test_an_overlong_value_is_truncated_visibly(monkeypatch, summary_globals):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 20)

    rendered = rendered_summary([monitor.StartupSummaryRow("Path", "/very/long/path/" + "x" * 100, concise=True)], show_full=False)

    value = rendered.split(":", 1)[1].strip()
    assert len(value) == 20
    assert value.endswith("...")


# Verifies a value that fits is left exactly as it is
def test_a_short_value_is_not_touched(monkeypatch, summary_globals):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 40)

    assert monitor.truncate_summary_value("short") == "short"


# Verifies truncation is off by default, so existing output is unchanged for anyone who did not ask
def test_truncation_is_off_by_default(summary_globals):
    assert monitor.startup_summary_value_width() == 0
    assert monitor.truncate_summary_value("x" * 500) == "x" * 500


# Verifies the auto width is derived from the terminal rather than guessed
def test_the_auto_width_follows_the_terminal(monkeypatch, summary_globals):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", "Auto")
    monkeypatch.setattr(monitor.shutil, "get_terminal_size", lambda fallback=(0, 0): type("Size", (), {"columns": 100, "lines": 24})())

    assert monitor.startup_summary_value_width() == 68


# Verifies an unusable width setting falls back to no truncation instead of raising during startup
@pytest.mark.parametrize("setting", ["nonsense", None, [], -5])
def test_an_unusable_width_setting_disables_truncation(monkeypatch, summary_globals, setting):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", setting)

    assert monitor.startup_summary_value_width() == 0


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

    for group in ("Getting started", "Configuration and secrets", "Notifications", "Information and diagnostics"):
        assert f"  {group}" in epilog, f"the {group} group is missing"
    assert epilog.startswith("Examples:")
    assert monitor.GUIDE_URL in epilog


# Verifies every example command is written for the detected install rather than hardcoded
def test_the_help_examples_suit_the_install(monkeypatch):
    monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    assert "steam_monitor --setup" in monitor.help_examples()

    monkeypatch.setattr("sys.argv", ["/home/user/steam_monitor.py"])
    assert "python3 steam_monitor.py --setup" in monitor.help_examples()


# Verifies the examples reach the commands a newcomer needs first
@pytest.mark.parametrize("flag", ["--setup", "--doctor", "--generate-config", "--set-steam-api-key", "--send-test-email", "--send-test-webhook"])
def test_the_help_examples_cover_the_first_commands(flag):
    assert flag in monitor.help_examples()


# Verifies a row is verbose-only unless it opts in, which is what keeps the concise view short
def test_rows_are_verbose_only_by_default():
    row = monitor.StartupSummaryRow("Label", "value")

    assert row.concise is False
    assert row.full is True and row.log is True


# Verifies a feature row reaches the concise view only when that feature is switched on
@pytest.mark.parametrize("enabled", [True, False])
def test_a_feature_row_is_concise_only_when_it_is_on(monkeypatch, summary_globals, enabled):
    monkeypatch.setattr(monitor, "FRIENDS_CHECK", enabled)

    concise = rendered_summary(monitor.build_startup_summary("tool.conf", None, None), show_full=False)

    assert ("Friends tracking" in concise) is enabled


# Verifies the concise view ends by naming the flags that reveal the rest
def test_the_concise_view_points_at_the_verbose_flags(summary_globals):
    concise = rendered_summary(monitor.build_startup_summary("tool.conf", None, None), show_full=False)

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
        assert lines[index + 1] == f"    {command}", lines[index + 1]
        assert lines[index + 2] == ""
    # These two are single lines rather than blocks, and the guide value is column aligned
    assert "Full options: steam_monitor --help" in lines
    assert f"Guide:        {monitor.QUICK_START_GUIDE_URL}" in lines
