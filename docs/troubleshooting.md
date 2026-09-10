# Troubleshooting

## Doctor Preflight

Before monitoring anything, `--doctor` checks whether the setup is actually ready and reports what is not:

```sh
steam_monitor --doctor <steam_target>
```

It is **read-only**: it writes no files and says so before the first check runs. It opens with the detected install method, then groups checks into **Environment**, **Configuration**, **Authentication**, **Connectivity**, **Target** and **Notifications**. Each row is marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`, colour-coded by status when colour output is on. Every `[WARN]` and `[FAIL]` row carries an indented `To fix:` line under its marker, plus a `Guide:` link when a documentation page covers that row. A `[SKIP]` row names a check that could not run and says why.

The Configuration section names the configuration and dotenv files in effect and reports **which secrets came from the dotenv file and which came from the environment**, by name only. No secret value is ever printed. It also reports whether [TLS verification](configuration.md#tls-verification) is on, and warns while it is off. Settings that control timing and counts, such as the check intervals and `SMTP_PORT`, are checked for usable values and every one that fails is named in a single row.

It also names the **log and CSV files monitoring would write** and reports whether each one can be created. The log file name includes the Steam ID or `FILE_SUFFIX`, so it is only resolved when a target is given. Without one, the row reports the base path instead.

The Notifications section **signs in to the configured SMTP server** and validates webhook settings without sending anything. Each ready row lists the **alert categories** that channel would deliver.

When email or webhook alerts validate and you are at a terminal, doctor then offers to send **one real test message per channel**, each behind its own confirmation. Declining is the default. Nothing is sent without an explicit `y`, so a scripted or containerized run stays message-free. The `Summary` line is printed after the tests finish and counts their results, so the sentence and the exit code always describe the same run.

The report ends with a **Next steps** block naming the command that starts monitoring, carrying the same `--config-file` and `--env-file` this run checked. It carries the target this run used, leaves it out when the configuration file already supplies one and otherwise shows `<steam_target>` for you to replace. While a check is failing it asks for the failures first.

It exits `0` when every check passed and `1` when any check or approved delivery test failed, so it can be used as a container healthcheck or a CI smoke test:

```sh
steam_monitor --doctor <steam_target> && echo "ready"
```

`steam_target` can be a Steam64 ID, Steam3 identifier, vanity name or full profile URL. Running doctor without a target checks everything except the monitored profile. An explicitly selected dotenv path that does not exist is reported as a warning with the path and recovery command.

## When Something Goes Wrong

Every failure is reported in the same three-part shape:

```
* Error: Steam rejected the configured Web API key
To fix: Validate and replace it with 'steam_monitor --set-steam-api-key'
Guide: https://misiektoja.github.io/steam_monitor/setup-and-first-run/#steam-web-api-key
```

The `To fix:` line names the command for the way you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as-is. The `Guide:` line opens the page of this documentation that covers the failure.

Startup uses the same shape. Starting without a profile to watch reports the missing target and the forms it accepts rather than printing the whole help screen.

Adding `--debug` appends a `Technical detail:` line with the underlying exception, unless that exception is the line already printed above it. That detail is for a bug report. The `To fix:` line is the one to act on. Secret values are redacted from all three.

The banner that says nothing changed prints in any mode: `* Monitoring healthy for <steam_id>` with what was checked, followed by `Liveness check, timestamp:`. It is timed rather than counted in checks, so it appears once per `LIVENESS_CHECK_INTERVAL` of quiet, measured from the last thing the run printed. A monitoring failure is reported as `* Error: <what failed> (retrying in <time>)`, with the `To fix:` paragraph under it the first time that category appears. Every monitor in this family prints that same line. A failure the tool can retry away, such as a Steam outage or a lost connection, is reported once the short retry has failed too, so a blip of a single check prints nothing. A failure that needs you, such as a rejected API key, is reported on the first check. With `--verbose` every first failing check is reported. During a long outage the failure is reported in full once, then the tool stays quiet and reminds you once an hour with `* Monitoring degraded for <steam_id>`, the summary of what is still failing, when it started and how many checks have failed so far, so a two-day outage is a handful of lines rather than one block per check. The reminder has its own clock and does not depend on `LIVENESS_CHECK_INTERVAL`, so it keeps coming when the banner is off. When the failure clears, `* Monitoring recovered for <steam_id>` reports how long it lasted. An outage that starts failing differently is still one outage: a lost connection that reads as a timeout on one check and as an unreachable host on the next prints nothing new, a change to another kind of failure that clears on its own is one line, `* Monitoring failure changed for <steam_id>. <what fails now>`, and a change to a failure that needs you is reported in full. A failure that is worth retrying, such as a timeout or a Steam outage, gets one short retry before the tool falls back to waiting a full polling interval. A rate limit waits for the period Steam asked for, and a rejected API key is not retried at all.

## Verbose and Debug Output

Two flags control how much the tool explains about itself.

`--verbose` reports what the tool is doing in plain `* ` lines. It expands the startup summary, which is where the configuration file, dotenv file, install method and the source of each secret are named. During monitoring it stays quiet unless something happens: it reports any tracked feature that could not fire its alert this cycle and each delivered alert with the inbox or webhook it reached. Use `--debug` for a line per completed check.

A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

```sh
steam_monitor <steam_target> --verbose
```

`--debug` traces the whole run in timestamped `[DEBUG HH:MM:SS]` lines. Each line names the operation, then lists its details as comma-separated `key=value` fields, so a long trace stays scannable:

```
[DEBUG 23:47:21] Polling Steam: steamid=76561197960435530, endpoints=ISteamUser.GetPlayerSummaries+IPlayerService.GetRecentlyPlayedGames
[DEBUG 23:47:21] Polling Steam: steamid=76561197960435530, personastate=0, outcome=OK
```

Traced operations include configuration loading, the connectivity probe, every Steam Web API call each polling cycle makes, SMTP delivery, each webhook attempt with its HTTP status and retry decision, and the state files being read and written. Every operation that makes an outbound call reports its result as `outcome=OK` or `outcome=failed` with an `error=` field, so a trace never stops at what was attempted:

```sh
steam_monitor <steam_target> --debug
```

The two modes are independent, so pass both to see everything. Either one on its own expands the startup summary, adding the detected install method, which secrets came from where, and the diagnostic state.

Either mode can also be turned on permanently with the `VERBOSE_MODE` and `DEBUG_MODE` configuration settings. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without the `* Email delivered` and `* Webhook delivered` lines, which is worth doing when alerts are frequent. A flag on the command line always wins, so `--debug` still applies when the configuration file sets `DEBUG_MODE = False`.

If long paths or game titles wrap and make the output hard to read, set `TRUNCATE_CHARS` or use the `--truncate N` flag to cut each screen line to a maximum width. Use `999` to auto-detect the terminal width. The log file always keeps the full line, so the setting is ignored when logging is disabled with `-d`. It is off by default and needs the optional `wcwidth` library to measure display width, otherwise lines are left untouched.

Debug mode is the fastest way to find out why a tracked feature reports nothing. Steam level, XP, friends list and games library lookups each degrade quietly when Steam refuses them, usually because the profile is private. Debug names the endpoint that failed and verbose adds a line saying the matching alert cannot fire, once when the feature stops working and once when it works again. Verbose is the lighter of the two when the question is only whether monitoring is still running. Debug also records why ntfy artwork preparation fell back to text.

Secret values are never printed by either mode. Redaction happens inside both printers rather than at each call site, so a known secret is replaced with `<redacted>` no matter which line interpolates it. The webhook destination is traced by host name alone. Debug output is switched off entirely for the duration of `--set-steam-api-key` and `--set-webhook-url`, so a pasted value cannot reach the console or the log.
