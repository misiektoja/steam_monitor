# Debugging Tools

## Verbose and Debug Output

Two flags control how much the tool explains about itself.

`--verbose` adds startup detail, including the detected install method and which secrets came from the dotenv file versus the environment:

```sh
steam_monitor <steam_user_id> --verbose
```

`--debug` traces the whole run in timestamped `[DEBUG HH:MM:SS]` lines: the configuration file being loaded, the connectivity endpoint being probed, every Steam Web API call each polling cycle makes, the SMTP host an email is sent through, each webhook attempt with its HTTP status and retry decision, the state files being read and written, and the technical cause of any failure:

```sh
steam_monitor <steam_user_id> --debug
```

The two modes are independent, so pass both to see everything. Either one on its own expands the startup summary, adding the detected install method, which secrets came from where, and the diagnostic state.

If long paths make the startup summary hard to read, `TRUNCATE_CHARS` bounds each value: set it to a number of characters, or to `"Auto"` to fit the summary to the terminal width. Truncated values end with a visible `...` marker. It is off by default. Both can also be enabled permanently with the `VERBOSE_MODE` and `DEBUG_MODE` configuration settings. A flag on the command line always wins, so `--debug` still applies when the configuration file sets `DEBUG_MODE = False`.

Debug mode is the fastest way to find out why a tracked feature reports nothing. Steam level, XP, friends list and games library lookups each degrade quietly when Steam refuses them, usually because the profile is private. Debug names the endpoint that failed and verbose adds a line saying the matching alert cannot fire this cycle.

Secret values are never printed by either mode. Redaction happens inside both printers rather than at each call site, so a known secret is replaced with `<redacted>` no matter which line interpolates it. Where a secret has to be identified, only a short masked prefix and suffix are shown, and the webhook destination is traced by host name alone. Debug output is switched off entirely for the duration of `--set-steam-api-key` and `--set-webhook-url`, so a pasted value cannot reach the console or the log.

## Coloring Log Output with GRC

The tool has native **color output** support for terminal since v1.5 (see `COLORED_OUTPUT` and `COLOR_THEME` config options), but you can also use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 steam_monitor_<user_steam_id/file_suffix>.log
```
