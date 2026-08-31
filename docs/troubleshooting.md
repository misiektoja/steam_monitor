# Troubleshooting

## Doctor Preflight

Before monitoring anything, `--doctor` checks whether the setup is actually ready and reports what is not:

```sh
steam_monitor --doctor <steam_target>
```

It is **read-only**: it writes no files and says so before the first check runs. It opens with the detected install method, then groups checks into **Environment**, **Configuration**, **Authentication**, **Connectivity**, **Target** and **Notifications**. Each row is marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`, colour-coded by status when colour output is on. Every non-passing row carries a `To fix:` line and a link to the documentation page that covers it.

The Configuration section names the configuration and dotenv files in effect and reports **which secrets came from the dotenv file and which came from the environment**, by name only. No secret value is ever printed.

It also names the **log and CSV files monitoring would write** and reports whether each one can be created. The log file name includes the Steam ID or `FILE_SUFFIX`, so it is only resolved when a target is given. Without one, the row reports the base path instead.

When email or webhook alerts validate and you are at a terminal, doctor then offers to send **one real test message per channel**, each behind its own confirmation. Declining is the default. Nothing is sent without an explicit `y`, so a scripted or containerized run stays message-free.

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

Adding `--debug` appends a `Technical detail:` line with the underlying exception. That detail is for a bug report; the `To fix:` line is the one to act on. Secret values are redacted from all three.

During monitoring, a failure that keeps recurring prints its one-line summary each cycle but repeats the `To fix:` line only when the kind of failure changes, so a long Steam outage cannot fill the log with the same paragraph. A failure that is worth retrying, such as a timeout or a Steam outage, gets one short retry before the tool falls back to waiting a full polling interval. A rate limit waits for the period Steam asked for, and a rejected API key is not retried at all.

## Verbose and Debug Output

Two flags control how much the tool explains about itself.

`--verbose` adds startup detail, including the detected install method and which secrets came from the dotenv file versus the environment:

```sh
steam_monitor <steam_target> --verbose
```

`--debug` traces the whole run in timestamped `[DEBUG HH:MM:SS]` lines: the configuration file being loaded, the connectivity endpoint being probed, every Steam Web API call each polling cycle makes, the SMTP host an email is sent through, each webhook attempt with its HTTP status and retry decision, the state files being read and written, and the technical cause of any failure:

```sh
steam_monitor <steam_target> --debug
```

The two modes are independent, so pass both to see everything. Either one on its own expands the startup summary, adding the detected install method, which secrets came from where, and the diagnostic state.

Either mode can also be turned on permanently with the `VERBOSE_MODE` and `DEBUG_MODE` configuration settings. A flag on the command line always wins, so `--debug` still applies when the configuration file sets `DEBUG_MODE = False`.

If long paths make the startup summary hard to read, `TRUNCATE_CHARS` bounds each value: set it to a number of characters, or to `"Auto"` to fit the summary to the terminal width. Truncated values end with a visible `...` marker. It is off by default.

Debug mode is the fastest way to find out why a tracked feature reports nothing. Steam level, XP, friends list and games library lookups each degrade quietly when Steam refuses them, usually because the profile is private. Debug names the endpoint that failed and verbose adds a line saying the matching alert cannot fire this cycle. Debug also records why ntfy artwork preparation fell back to text.

Secret values are never printed by either mode. Redaction happens inside both printers rather than at each call site, so a known secret is replaced with `<redacted>` no matter which line interpolates it. The webhook destination is traced by host name alone. Debug output is switched off entirely for the duration of `--set-steam-api-key` and `--set-webhook-url`, so a pasted value cannot reach the console or the log.
