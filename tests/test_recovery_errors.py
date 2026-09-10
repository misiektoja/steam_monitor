"""Tests that every failure carries a stable code, an actionable fix, and no secrets."""

import ast
import inspect
import re
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests as req

import steam_monitor as monitor


SECRET_API_KEY = "0123456789ABCDEF0123456789ABCDEF"


@pytest.fixture
# Restores the settings the recovery paths read, since the whole suite shares one imported module
def restored_globals():
    names = ("DEBUG_MODE", "VERBOSE_MODE", "STEAM_API_KEY", "WEBHOOK_URL", "SMTP_PASSWORD", "CLI_CONFIG_PATH", "DOTENV_FILE")
    snapshot = {name: getattr(monitor, name) for name in names}
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)


# Returns an HTTP error carrying the given status, the way requests raises one
def http_error(status_code, message="request failed"):
    response = req.Response()
    response.status_code = status_code
    return req.exceptions.HTTPError(message, response=response)


# Verifies the code set is closed, so a message cannot be invented outside the taxonomy
def test_an_unknown_recovery_code_is_refused():
    with pytest.raises(ValueError, match="Unsupported recovery code"):
        monitor.make_recovery_advice("steam.made_up", "summary", "fix", True)


# Verifies every code the classifier can produce is inside the declared set
@pytest.mark.parametrize("context", ["runtime", "config", "target", "email", "webhook", "file", "set_steam_api_key", "set_webhook_url"])
def test_the_classifier_only_produces_declared_codes(context):
    samples = [
        None, "", "timed out", "connection refused", "rate limit exceeded", "forbidden",
        "not found", "service unavailable", "private profile", "could not save",
        "interactive terminal", "cancelled", "does not exist", "must be discord",
        http_error(401), http_error(403), http_error(404), http_error(429), http_error(500), http_error(503),
        ValueError("Invalid Steam community URL"), TimeoutError("timed out"),
    ]
    for sample in samples:
        advice = monitor.classify_recovery_error(sample, context=context)
        assert advice.code in monitor.RECOVERY_CODES, (context, sample, advice.code)
        assert advice.summary, (context, sample)
        assert advice.fix, (context, sample)
        assert isinstance(advice.retryable, bool)


# Verifies a rate limit is classified as retryable so the loop waits rather than giving up
def test_a_rate_limit_is_retryable():
    advice = monitor.classify_recovery_error(http_error(429), context="runtime")

    assert advice.code == "steam.rate_limited"
    assert advice.retryable is True


# Verifies a rejected API key is not retryable, since retrying it can only fail again
def test_a_rejected_api_key_is_not_retryable():
    for error in (http_error(401), http_error(403)):
        advice = monitor.classify_recovery_error(error, context="runtime")

        assert advice.code == "auth.api_key_invalid"
        assert advice.retryable is False
        assert "--set-steam-api-key" in advice.fix


# Verifies a Steam outage is retryable, since it resolves without the user doing anything
def test_a_steam_outage_is_retryable():
    advice = monitor.classify_recovery_error(http_error(503), context="runtime")

    assert advice.code == "steam.unavailable"
    assert advice.retryable is True


# Verifies a timeout and a connection failure are separated, since they suggest different checks
def test_transport_failures_are_separated():
    assert monitor.classify_recovery_error(TimeoutError("request timed out"), context="runtime").code == "network.timeout"
    assert monitor.classify_recovery_error(req.exceptions.ConnectionError("name resolution failed"), context="runtime").code == "network.unavailable"


# Verifies a deleted account is reported as a target problem rather than as a transport failure
def test_a_missing_profile_is_a_target_problem():
    advice = monitor.classify_recovery_error(http_error(404), context="runtime")

    assert advice.code == "target.not_found"
    assert advice.retryable is False


# Verifies each context reaches its own family of codes rather than falling through to one generic answer
def test_each_context_reaches_its_own_codes():
    assert monitor.classify_recovery_error("syntax error", context="config").code == "config.invalid"
    assert monitor.classify_recovery_error("file does not exist", context="config").code == "config.missing"
    assert monitor.classify_recovery_error("authentication failed", context="email").code == "smtp.authentication"
    assert monitor.classify_recovery_error("could not be reached", context="webhook").code == "webhook.connection"
    assert monitor.classify_recovery_error("cannot load", context="file").code == "file.unreadable"
    assert monitor.classify_recovery_error("Invalid Steam community URL", context="target").code == "target.invalid"


# Verifies a fix line points at documentation the reader can open
def test_a_fix_carries_its_guide_link():
    advice = monitor.classify_recovery_error(http_error(403), context="runtime")

    assert "Guide: " in advice.fix
    assert monitor.DOCS_BASE_URL in advice.fix


# Verifies advice already classified is carried across an exception boundary unchanged
def test_advice_survives_an_exception_boundary():
    original = monitor.make_recovery_advice("network.timeout", "summary", "fix", True, "detail")
    cause = TimeoutError("underlying")

    error = monitor.RecoveryError(original, cause=cause)

    assert monitor.classify_recovery_error(error) is original
    assert error.__cause__ is cause
    assert str(error) == "summary"


# Verifies the rendered block is the shared Error and To fix shape, with technical detail held back
def test_the_rendered_block_hides_technical_detail_by_default(restored_globals):
    monitor.DEBUG_MODE = False

    rendered = monitor.render_recovery_error(http_error(403, "403 Client Error: Forbidden"), context="runtime")

    lines = rendered.splitlines()
    assert lines[0].startswith("* Error: ")
    assert any(line.startswith("To fix: ") for line in lines)
    assert "Technical detail:" not in rendered


# Verifies debug mode is what reveals the technical cause, and only that
def test_debug_mode_reveals_the_technical_detail(restored_globals):
    monitor.DEBUG_MODE = True

    rendered = monitor.render_recovery_error(http_error(403, "403 Client Error: Forbidden"), context="runtime")

    assert "Technical detail: " in rendered
    assert "403 Client Error" in rendered


# Verifies a secret reaching a failure message is redacted in every field of the advice
def test_a_secret_never_reaches_the_advice(restored_globals):
    monitor.STEAM_API_KEY = SECRET_API_KEY
    error = http_error(403, f"403 Forbidden for url: https://api.steampowered.com/x?key={SECRET_API_KEY}")

    advice = monitor.classify_recovery_error(error, context="runtime")
    rendered = monitor.render_recovery_error(error, context="runtime", debug=True)

    assert SECRET_API_KEY not in advice.summary
    assert SECRET_API_KEY not in advice.fix
    assert SECRET_API_KEY not in advice.detail
    assert SECRET_API_KEY not in rendered
    assert "<redacted>" in rendered


# Verifies malformed secret assignments cannot expose a value tail after whitespace
def test_malformed_config_redacts_the_complete_secret_value(tmp_path, capsys, restored_globals):
    config = tmp_path / "broken.conf"
    config.write_text('SMTP_PASSWORD = "top secret value\n', encoding="utf-8")

    assert monitor.load_config_file(config, namespace={}, report_errors=True) is False

    output = capsys.readouterr().out
    assert "top" not in output
    assert "secret value" not in output
    assert "SMTP_PASSWORD = <redacted>" in output


# Verifies the fix is rendered whenever this printer runs, since its caller only reaches it on a new failure
# category and the throttling of a lasting outage is the outage reporter's job rather than a second guard's
def test_the_printed_failure_carries_its_fix(capsys, restored_globals):
    monitor.DEBUG_MODE = False

    monitor.print_recovery_error(http_error(503), "runtime", retry_note="retrying in 5 minutes")

    output = capsys.readouterr().out
    assert output.startswith("* Error: The Steam Web API is temporarily unavailable (retrying in 5 minutes)\n")
    assert output.count("To fix: ") == 1


# Every place that reports a problem without the classifier and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the Steam library": "raised at import, while a dependency the classifier itself needs is missing",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "need the optional Pillow package": "a wizard hint above the question that offers to switch the feature off",
    "Could not resolve": "a wizard hint inside the question that re-asks, where the next prompt is the recovery",
    "cannot be resolved without a Steam Web API key": "a wizard hint inside the question that re-asks, where the next prompt is the recovery",
    "Setup needs a writable dotenv file": "an answer hint inside the question that re-asks, where the next prompt is the recovery",
    "Monitoring failure changed for": "a one-line note on a classified outage that already had its full report",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be|could not|couldn't|unable to", re.IGNORECASE)


# Returns the literal text one print argument shows, leaving out the parts an f-string fills at runtime
def printed_text(node):
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        return "".join(printed_text(part) for part in node.values)
    if isinstance(node, ast.BinOp):
        return printed_text(node.left) + printed_text(node.right)
    return ""


# Returns every printed line that reads as a problem, paired with the line it sits on
def reported_problems(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        text = " ".join(printed_text(argument) for argument in node.args)
        if TROUBLE_WORDS.search(text):
            found.append((node.lineno, " ".join(text.split())))
    return found


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier():
    unexplained = [f"line {line}: {text[:120]}" for line, text in reported_problems((Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")) if not any(marker in text for marker in CLASSIFIER_EXEMPTIONS)]

    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source():
    source = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]
    problems = reported_problems(source)

    assert len(inspected) > 200
    assert all(any(marker in text for _, text in problems) for marker in CLASSIFIER_EXEMPTIONS), "an exemption stopped matching a printed line"


# Applies a usable mail server, so a test that breaks one setting is not also broken by the others
def configure_smtp(monkeypatch):
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_USER", "sender")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "not-a-real-password")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.com")


@pytest.mark.parametrize("setting, value", [
    ("SMTP_HOST", "not a host"),
    ("SMTP_PORT", "not a port"),
    ("SENDER_EMAIL", "not-an-email"),
    ("SMTP_PASSWORD", ""),
])
# Verifies a refused setting names the fix and the guide, so no delivery path reports without saying what to do
def test_a_refused_smtp_setting_carries_the_shared_error_block(capsys, monkeypatch, setting, value):
    configure_smtp(monkeypatch)
    monkeypatch.setattr(monitor, setting, value)

    assert monitor.send_email("subject", "body", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert "* Error: The SMTP settings are incorrect (" in output
    assert "To fix: Check SMTP_HOST, SMTP_PORT, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file" in output
    assert f"Guide: {monitor.SMTP_GUIDE_URL}" in output


# Verifies a message the tool cannot send carries the same block as an unusable setting
def test_an_unsendable_message_carries_the_shared_error_block(capsys, monkeypatch):
    configure_smtp(monkeypatch)

    assert monitor.send_email("", "body", "", True, smtp_timeout=1) == 1
    assert monitor.send_email("subject", "", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert output.count("* Error: The SMTP settings are incorrect (") == 2
    assert output.count(f"Guide: {monitor.SMTP_GUIDE_URL}") == 2


# Verifies a mail server that refuses the session is reported with the fix rather than as a bare line
def test_a_refused_smtp_session_carries_the_shared_error_block(capsys, monkeypatch):
    configure_smtp(monkeypatch)
    monkeypatch.setattr(monitor.smtplib, "SMTP", Mock(side_effect=OSError("connection refused")))

    assert monitor.send_email("subject", "body", "", True, smtp_timeout=1) == 1

    output = capsys.readouterr().out
    assert "* Error: The SMTP server could not be reached" in output
    assert f"Guide: {monitor.SMTP_GUIDE_URL}" in output


# Verifies a refused webhook delivery carries the fix and the guide the email failures carry
def test_a_refused_webhook_delivery_carries_the_shared_error_block(capsys, monkeypatch, restored_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")
    monkeypatch.setattr(monitor, "post_webhook_request", Mock(return_value=http_error(404).response))

    assert monitor.send_webhook("title", "body", "status", force=True, sleeper=lambda _seconds: None) == 1

    output = capsys.readouterr().out
    assert "* Error: The webhook service returned HTTP 404" in output
    assert "To fix: " in output
    assert f"Guide: {monitor.WEBHOOK_GUIDE_URL}" in output


# Verifies an unusable webhook setting is refused with the same block, so configuration and delivery read alike
def test_an_unusable_webhook_setting_carries_the_shared_error_block(capsys, monkeypatch, restored_globals):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "carrier pigeon")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")

    assert monitor.send_webhook("title", "body", "status", force=True) == 1

    output = capsys.readouterr().out
    assert "* Error: WEBHOOK_PROVIDER must be discord or ntfy" in output
    assert f"Guide: {monitor.WEBHOOK_GUIDE_URL}" in output


# Verifies no delivery path prints at all, since a print there is an error line that skipped the recovery block
def test_no_delivery_path_prints_outside_the_recovery_block():
    source = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
    delivery = {"send_email", "send_webhook", "print_webhook_error", "smtp_connect_and_login", "post_webhook_request"}
    offenders = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef) or node.name not in delivery:
            continue
        offenders.extend(f"{node.name}:{call.lineno}" for call in ast.walk(node) if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "print")

    assert not offenders, "delivery paths printing outside the recovery block: " + ", ".join(offenders)


# Verifies the refusal to replace an existing file points at the section describing that file
def test_the_existing_file_refusal_points_at_the_configuration_file_section():
    advice = monitor.classify_recovery_error(context="file.exists")

    assert advice.code == "file.exists"
    assert f"Guide: {monitor.CONFIG_FILE_GUIDE_URL}" in advice.fix
    assert advice.fix.rstrip().endswith("#configuration-file")


# Verifies the missing-target advice names the accepted forms and a command carrying the paths this run was given
def test_a_missing_target_advises_the_accepted_forms(restored_globals):
    monitor.CLI_CONFIG_PATH = "/tmp/steam_monitor.conf"
    monitor.DOTENV_FILE = "/tmp/steam_monitor.env"

    advice = monitor.classify_recovery_error(context="target.missing")

    assert advice.code == "target.missing"
    # The summary follows the shape every sibling uses for a target it was never given
    assert advice.summary == "No Steam profile was provided"
    assert monitor.STEAM_TARGET_FORMS in advice.fix
    assert "--config-file /tmp/steam_monitor.conf" in advice.fix
    assert "--env-file /tmp/steam_monitor.env" in advice.fix
    assert f"Guide: {monitor.QUICK_START_GUIDE_URL}" in advice.fix


# Verifies the startup gate can restate the missing target in its own words without losing the shared fix
def test_a_missing_target_keeps_the_shared_fix_under_its_own_summary(restored_globals):
    monitor.CLI_CONFIG_PATH = ""
    monitor.DOTENV_FILE = ""

    advice = monitor.classify_recovery_error(context="target.missing", detail="A Steam profile target needs to be defined")

    assert advice.code == "target.missing"
    assert advice.summary == "A Steam profile target needs to be defined"
    assert advice.fix == monitor.classify_recovery_error(context="target.missing").fix


# Verifies a write the tool reports as a file problem is classified as unwritable rather than left unknown
def test_a_failed_file_write_is_classified_as_unwritable(restored_globals):
    advice = monitor.classify_recovery_error(PermissionError(13, "Permission denied"), context="file", detail="Cannot save games library to '/x/games.json'")

    assert advice.code == "file.unwritable"
    assert advice.fix.startswith("Check that the directory exists and is writable, or choose another path")
    assert advice.fix.endswith(f"Guide: {monitor.DIAGNOSTICS_GUIDE_URL}")


# Verifies a profile CSV row that cannot be written carries the same fix as every other unwritable file
def test_a_failed_profile_csv_write_carries_the_shared_fix(restored_globals, capsys):
    monitor.print_recovery_error(RuntimeError("Failed to write to profile CSV file '/x/p.csv': [Errno 2] No such file or directory"), context="file.unwritable")

    printed = capsys.readouterr().out
    assert printed.startswith("* Error: Failed to write to profile CSV file '/x/p.csv'")
    assert "To fix: Check that the directory exists and is writable, or choose another path" in printed


# Verifies a failed CSV write reports through the recovery block, since the monitoring loop carries on past it
def test_no_csv_write_failure_prints_its_own_line():
    csv_writers = {"init_csv_file", "init_profile_csv_file", "write_csv_entry", "write_profile_csv_entry"}
    offenders = []
    guarded = 0
    for node in ast.walk(ast.parse(Path(monitor.__file__).read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Try) or (node.body[-1].end_lineno or node.body[0].lineno) - node.body[0].lineno > 6:
            continue
        if not any(isinstance(inner, ast.Call) and getattr(inner.func, "id", "") in csv_writers for statement in node.body for inner in ast.walk(statement)):
            continue
        guarded += 1
        offenders.extend(f"line {statement.lineno}" for handler in node.handlers for statement in handler.body if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and getattr(statement.value.func, "id", "") == "print")

    assert guarded >= 11, f"only {guarded} CSV writes are guarded, so this no longer covers them"
    assert not offenders, "CSV write failures reported outside the recovery block:\n" + "\n".join(offenders)


# Verifies added context does not replace the error text the rules read, which used to make every such failure unknown
@pytest.mark.parametrize("message, expected", [("429 rate limit exceeded", "steam.rate_limited"), ("Connection timed out", "network.timeout")])
def test_a_caller_supplied_detail_does_not_hide_the_error(message, expected):
    advice = monitor.classify_recovery_error(Exception(message), detail="Cannot read the Steam profile")

    assert advice.code == expected
    assert "Cannot read the Steam profile" in advice.detail


# Returns every literal string one argument can evaluate to, following a conditional or a code held in a local name
def literal_values(node, assignments):
    if isinstance(node, ast.Constant):
        return {node.value} if isinstance(node.value, str) else set()
    if isinstance(node, ast.IfExp):
        return literal_values(node.body, assignments) | literal_values(node.orelse, assignments)
    if isinstance(node, ast.Name) and assignments.get(node.id):
        return set().union(*(literal_values(value, assignments) for value in assignments[node.id]))
    return set()


# Returns every code an advice builder can pass, which is what makes a declared code with no producer visible
def builder_codes(source):
    tree = ast.parse(source)
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    codes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("advice", "make_recovery_advice") and node.args:
            codes |= literal_values(node.args[0], assignments)
    return codes


# Verifies a local file descriptor limit is reported as itself rather than as a failure of the call that hit it
def test_a_file_descriptor_limit_is_not_reported_as_a_service_failure():
    try:
        try:
            raise OSError(24, "Too many open files")
        except OSError as inner:
            raise RuntimeError("the Steam request failed") from inner
    except RuntimeError as error:
        advice = monitor.classify_recovery_error(error)

    assert advice.code == "resource.exhausted"
    assert advice.retryable is False
    assert "not a Steam problem" in advice.summary
    assert "ulimit -n 4096" in advice.fix


# Verifies the descriptor limit is matched as a whole errno, so errno 240 or 241 in a message is not mistaken for it
def test_a_neighbouring_errno_is_not_a_file_descriptor_limit():
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 24] Too many open files")) is True
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 240] something else")) is False
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 241] something else")) is False


# Verifies every declared code has a producer, so the set records what the tool reports rather than what it might
def test_every_declared_code_is_reachable():
    unreachable = set(monitor.RECOVERY_CODES) - builder_codes(Path(monitor.__file__).read_text(encoding="utf-8"))

    assert unreachable == set(), f"codes with no producer: {sorted(unreachable)}"


# Verifies no advice builder names a code outside the declared set, so the set stays the whole taxonomy
def test_no_code_outside_the_declared_set_is_produced():
    undeclared = builder_codes(Path(monitor.__file__).read_text(encoding="utf-8")) - set(monitor.RECOVERY_CODES)

    assert undeclared == set(), f"codes produced but not declared: {sorted(undeclared)}"


# Verifies a key that was never provided is reported as a missing secret, not as one Steam rejected
def test_a_missing_web_api_key_is_reported_as_a_missing_secret(restored_globals):
    monitor.CLI_CONFIG_PATH = ""
    monitor.DOTENV_FILE = ""

    advice = monitor.classify_recovery_error(context="secret.missing", detail="No Steam Web API key is configured")

    assert advice.code == "secret.missing"
    assert advice.summary == "No Steam Web API key is configured"
    assert "--set-steam-api-key" in advice.fix
    assert "export STEAM_API_KEY" in advice.fix
    assert f"Guide: {monitor.STEAM_API_KEY_GUIDE_URL}" in advice.fix


# Verifies the startup gate and the doctor row both report the missing key through that same category
def test_the_startup_gate_and_the_doctor_row_share_the_missing_key_category():
    source = Path(monitor.__file__).read_text(encoding="utf-8")

    assert source.count('context="secret.missing", detail="No Steam Web API key is configured"') == 2


# The only advice that names no page, and the reason no page covers it
GUIDELESS_ADVICE = {
    "The connectivity endpoint did not answer in time": "no page covers this check and the doctor report already ends with the troubleshooting link",
    "The connectivity endpoint could not be reached": "no page covers this check and the doctor report already ends with the troubleshooting link",
}

# The guide sits in this positional slot for each builder, or inside the fix when the signature carries no slot
GUIDE_SLOT = {"advice": 4, "make_recovery_advice": 5}


# True when this builder attaches a documentation link in any of the three shapes the tool uses
def attaches_a_guide(node, source):
    slot = GUIDE_SLOT.get(getattr(node.func, "id", ""))
    if slot is not None and len(node.args) > slot:
        return True
    if any(keyword.arg in ("guide_url", "guide") for keyword in node.keywords):
        return True
    return "recovery_fix_with_guide" in (ast.get_source_segment(source, node.args[2]) or "")


# Returns every expression assigned to each plain name in the module, so a fix held in a variable can be read
def assigned_expressions(tree):
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    return assignments


# Returns the text of the summary or fix, resolving one level of plain-name assignment
def resolved_text(node, source, assignments):
    if isinstance(node, ast.Name):
        return " ".join(ast.get_source_segment(source, value) or "" for value in assignments.get(node.id, []))
    return ast.get_source_segment(source, node) or ""


# Returns every advice builder that names no page, paired with the summary it reports
def guideless_advice(source):
    tree = ast.parse(source)
    assignments = assigned_expressions(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT) or len(node.args) < 3:
            continue
        # A builder that re-wraps an already-classified advice carries whatever guide that advice was given
        if isinstance(node.args[2], ast.Attribute) and node.args[2].attr == "fix":
            continue
        if attaches_a_guide(node, source) or "recovery_fix_with_guide" in resolved_text(node.args[2], source, assignments):
            continue
        found.append((node.lineno, resolved_text(node.args[1], source, assignments)))
    return found


# A failure with no page to read leaves the operator with a one-line fix and nowhere to go next
def test_every_failure_names_a_page():
    source = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
    unexplained = [f"line {line}: {summary[:100]}" for line, summary in guideless_advice(source) if not any(marker in summary for marker in GUIDELESS_ADVICE)]

    assert unexplained == []


# An allowlist that stopped matching anything would quietly cover every failure in the file
def test_the_guide_guard_still_inspects_the_source():
    source = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT]
    bare = guideless_advice(source)

    assert len(inspected) > 40
    assert all(any(marker in summary for _, summary in bare) for marker in GUIDELESS_ADVICE), "an allowlisted summary stopped matching a builder"


# One concept carried three names across this family: a renderer taking a built advice, a renderer taking the
# failure itself, and a third pair named after the monitoring loop. Pinned here so a call copied from a sibling
# cannot quietly mean something else
def test_the_recovery_printers_share_one_contract():
    advice_first = ("advice", "debug", "retry_note", "with_fix", "label")
    error_first = ("error", "context", "debug", "detail", "retry_note", "with_fix", "label")

    assert tuple(inspect.signature(monitor.render_recovery_advice).parameters) == advice_first
    assert tuple(inspect.signature(monitor.print_recovery_advice).parameters) == advice_first
    assert tuple(inspect.signature(monitor.render_recovery_error).parameters) == error_first
    assert tuple(inspect.signature(monitor.print_recovery_error).parameters) == error_first


# The advice pair prints what the caller built, so a summary the classifier would never produce survives the trip
def test_the_advice_printer_does_not_reclassify(capsys, restored_globals):
    monitor.DEBUG_MODE = False
    advice = monitor.make_recovery_advice("network.timeout", "a summary no rule produces", "a fix of its own", True)

    returned = monitor.print_recovery_advice(advice)

    assert capsys.readouterr().out == "* Error: a summary no rule produces\nTo fix: a fix of its own\n"
    assert returned is advice


# The error pair classifies what the caller hands it, which is the difference between the two front doors
def test_the_error_printer_classifies_what_it_was_given(capsys, restored_globals):
    monitor.DEBUG_MODE = False

    returned = monitor.print_recovery_error(http_error(503), context="runtime")

    assert returned.code != "unknown"
    assert capsys.readouterr().out.startswith(f"* Error: {returned.summary}\n")


# Both front doors reach the same renderer, so the retry note, the label and a suppressed fix behave the same way
def test_both_front_doors_render_the_same_line(restored_globals):
    monitor.DEBUG_MODE = False
    advice = monitor.classify_recovery_error(http_error(503), "runtime")

    through_advice = monitor.render_recovery_advice(advice, retry_note="retrying in 5 minutes", with_fix=False, label="Warning")
    through_error = monitor.render_recovery_error(http_error(503), "runtime", retry_note="retrying in 5 minutes", with_fix=False, label="Warning")

    assert through_advice == through_error
    assert through_advice == f"* Warning: {advice.summary} (retrying in 5 minutes)"


# A detail that only repeats the summary spends a line saying nothing, so the block drops it and keeps a real one
def test_a_detail_repeating_the_summary_is_dropped():
    repeated = monitor.make_recovery_advice("unknown", "the same sentence twice", "a fix", False, "the same sentence twice")
    differing = monitor.make_recovery_advice("unknown", "the summary", "a fix", False, "the raw cause")

    assert "Technical detail:" not in monitor.render_recovery_advice(repeated, debug=True)
    assert "Technical detail: the raw cause" in monitor.render_recovery_advice(differing, debug=True)


# A run that already prints the technical cause cannot be told to re-run for it
def test_the_unrecognized_failure_fix_follows_the_diagnostic_mode(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    plain = monitor.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    debugging = monitor.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix

    assert "--debug" in plain
    assert "--debug" not in debugging
