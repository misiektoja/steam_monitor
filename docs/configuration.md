# Configuration

Every setting has a command-line flag, and most also have a configuration file entry. [`--setup`](setup-and-first-run.md#guided-setup) writes both files for you. This page covers changing them afterwards, or writing them by hand.

## Configuration File

To keep settings persistently, generate a default config template and save it to a file named `steam_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
steam_monitor --generate-config > steam_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
steam_monitor --generate-config steam_monitor.conf
```

> **IMPORTANT**: On **Windows PowerShell**, using redirection (`>`) can cause the file to be encoded in UTF-16, which will lead to "null bytes" errors when running the tool. It is highly recommended to provide the filename directly as an argument to `--generate-config` to ensure UTF-8 encoding.

Edit the `steam_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

### Replacing an Existing Config

Passing a filename never replaces an existing file silently. On a terminal the tool asks first. Outside one, in a script or a container, it stops and names `--force`:

```sh
steam_monitor --generate-config steam_monitor.conf --force
```

Either way the previous file is copied to `steam_monitor.conf.<timestamp>.bak` before the new template is written, and the backup path is printed. Both files are readable only by their owner.

Shell redirection works differently: `> steam_monitor.conf` truncates the file before the tool starts, so nothing can back it up. Pass the filename when the destination already exists.

## Target Profile

Save the monitored profile in the configuration file so you do not have to repeat it on every run:

```ini
TARGET_STEAM_ID = "76561197960435530"
```

`TARGET_STEAM_ID` accepts the same forms as the command line: a Steam64 ID, a Steam3 identifier, a vanity name or a full profile URL. A target written directly after the command takes precedence. With a saved target, start monitoring with:

```sh
steam_monitor
```

[`--setup`](setup-and-first-run.md#guided-setup) asks whether to save the target. Declining leaves `TARGET_STEAM_ID` empty and the printed start commands include the profile instead.

Path settings are validated before startup opens files. A monitoring run stops and names the setting to correct. `--doctor`, `--setup` and the `--set-...` commands report the same setting and continue on the built-in value, so it can still be repaired. Command-line path overrides still take precedence.

## SMTP Settings

Private password entry preserves leading and trailing spaces. The exact value checked with the mail server is saved.

Private entry preserves literal `${...}` text in saved passwords and other secrets. Assignments that need this protection carry a `# monitor:literal` comment. Keep that comment when editing the value. Unmarked assignments retain their existing interpolation behavior. The marker is read by this monitor. Other dotenv readers or shells may still interpolate the value.

[`--setup`](setup-and-first-run.md#guided-setup) collects these for you. To configure them by hand, set the SMTP settings in the `steam_monitor.conf` file.

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
steam_monitor --send-test-email
```

## Webhook Settings

A delivery keeps its original destination and credentials for every retry. Reloaded settings apply to the next delivery. Discord templates must produce a JSON object. Dictionary templates and JSON strings are supported, including strings with escaped format braces. A placeholder the alert cannot fill, such as `{title[0]}` or `{0}`, is reported with the template text that failed. Mentions remain disabled in every template.

Steam Monitor supports Discord webhooks and native ntfy topics. Webhook alerts are independent from email, so either channel can be enabled alone or both can receive the same event.

[`--setup`](setup-and-first-run.md#guided-setup) collects the webhook URL and detects the provider from it. To configure it separately, save the private destination through a hidden prompt:

```sh
steam_monitor --set-webhook-url
```

The command validates the URL and atomically stores only the private `WEBHOOK_URL` in `.env` without sending a message. Use a custom dotenv destination with `--env-file PATH`. Select the provider and event switches in `steam_monitor.conf`:

```python
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"  # or "ntfy"
WEBHOOK_ACTIVE_NOTIFICATION = True
WEBHOOK_INACTIVE_NOTIFICATION = True
WEBHOOK_STATUS_NOTIFICATION = False
WEBHOOK_GAME_CHANGE_NOTIFICATION = True
WEBHOOK_LEVEL_XP_NOTIFICATION = False
WEBHOOK_FRIENDS_NOTIFICATION = False
WEBHOOK_GAMES_NOTIFICATION = False
WEBHOOK_NAME_CHANGE_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = True
```

A `WEBHOOK_URL` left unset, or left at its `your_webhook_url` placeholder, switches webhook alerts off at startup instead of failing at the first alert. `--verbose` reports why.

For Discord, copy the URL from **Edit Channel -> Integrations -> Webhooks**. For ntfy, use a complete private topic URL such as `https://ntfy.sh/your-private-topic`. The service is detected from the URL. While `WEBHOOK_PROVIDER` is left at its default, that detection is silent and `--verbose` reports it. A warning appears only when your configuration file sets a provider the URL disagrees with. Protected ntfy topics can use `NTFY_ACCESS_TOKEN` from an environment variable or dotenv file.

Verify delivery without starting monitoring:

```sh
steam_monitor --send-test-webhook
```

Advanced integrations can set `WEBHOOK_USERNAME`, `WEBHOOK_AVATAR_URL`, `WEBHOOK_HEADERS`, `WEBHOOK_TEMPLATE` and `WEBHOOK_TRANSFORMS`. Template and header values can use `title`, `description`, `version`, `image_url`, `fields`, `fields_str`, `color`, `timestamp`, `username` and `avatar_url` placeholders. Discord mentions are always disabled.

`WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to Discord and are ignored when `WEBHOOK_PROVIDER` is `"ntfy"`. The ntfy provider needs no template: it sends the alert body as a native ntfy message with the subject as its title. Customize ntfy delivery through `WEBHOOK_HEADERS` (for example `X-Priority` or `X-Tags`).

`NTFY_IMAGES` enables bounded Steam avatar or game artwork attachments. It is disabled by default and needs the optional Pillow package:

```sh
pip install "steam_monitor[ntfy-images]"
```

Then enable it in `steam_monitor.conf`:

```ini
NTFY_IMAGES = True
```

If artwork is enabled while Pillow is missing, startup says so, names the exact install command and keeps sending text-only alerts. If image preparation or upload fails, delivery falls back to text. Debug mode records why image preparation failed.

Long ntfy text messages are visibly truncated below ntfy's 4 KB boundary so they remain notifications instead of temporary attachments. Intentional image attachments through `NTFY_IMAGES` are unchanged.

## Storing Secrets

It is recommended to store secrets like `STEAM_API_KEY`, `SMTP_PASSWORD`, `WEBHOOK_URL` or `NTFY_ACCESS_TOKEN` as either an environment variable or in a dotenv file.

Both work on their own. An exported environment variable is applied whether or not a dotenv file exists, and a value exported in your shell overrides the same name in the dotenv file. Run with `--verbose` to see which of the two supplied each secret.

Set environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export STEAM_API_KEY="your_steam_web_api_key"
export SMTP_PASSWORD="your_smtp_password"
export WEBHOOK_URL="https://discord.com/api/webhooks/..."
export NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
STEAM_API_KEY="your_steam_web_api_key"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="https://discord.com/api/webhooks/..."
NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

Prefer `steam_monitor --set-smtp-password` for `SMTP_PASSWORD`: the value is entered through a hidden prompt and the mail server has to accept it before it is saved. Incomplete mail settings are reported before anything is typed, so a password is never entered against a server that was never configured. An exported `SMTP_PASSWORD` wins over the saved one at startup, so the command says so after saving rather than leaving you with a value the next run will not read.

Saving a secret with `--set-steam-api-key`, `--set-smtp-password` or `--set-webhook-url` rewrites the dotenv file atomically with owner-only permissions and keeps no backup, so the replaced secret is not left behind in a `.bak` file. A secret you switch off, such as the ntfy access token in the setup wizard, has its line removed rather than left as an empty value.

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it.

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
steam_monitor <steam_target> --env-file /path/.env-steam_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
steam_monitor <steam_target> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

A forgotten `export` can shadow the dotenv file invisibly, so `--debug` names every secret and the source it resolved from, never the value:

```text
[DEBUG 12:00:00] Secret resolution: name=STEAM_API_KEY, source=environment, value=set, chars=32
[DEBUG 12:00:00] Secret resolution: name=SMTP_PASSWORD, source=dotenv file, value=set
```

A secret still holding its `your_...` placeholder counts as unset and is left out, and a run with no secret anywhere says so on one line. A length appears only for the secrets whose length the provider issues, never for a password you chose.

When a `--set-*` command or the setup wizard replaces a secret, it rewrites that one assignment in place and leaves every other line alone. A line you wrote as `export NAME=...` keeps its `export`, so a dotenv file you also source in a shell still exports it. A value you clear has its line removed rather than left empty.

## TLS Verification

The tool verifies the TLS certificate of every server it contacts: the Steam Web API, the connectivity check endpoint, the mail server that delivers email alerts and, when enabled, the webhook service.

Set `VERIFY_SSL` to `False` only on a network that intercepts TLS with its own certificate authority, such as a corporate proxy. With verification off, an intercepted connection cannot be told apart from the real service.

The startup summary shows `TLS verification` and [`--doctor`](troubleshooting.md#doctor-preflight) reports a warning while it is off.

## Check Intervals

If you want to customize polling intervals, use `-k` and `-c` flags (or corresponding configuration options):

```sh
steam_monitor <steam_target> -k 30 -c 120
```

* `STEAM_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online, away or snooze (seconds)
* `STEAM_CHECK_INTERVAL`, `-c`: check interval when the user is offline (seconds)

An active interval below 30 seconds invites the Steam rate limiter, which stops the tool seeing anything. `--doctor` warns when the configured interval is that short.


### Reloading secrets and backup contents

On systems with SIGHUP, reloading applies changes from the selected dotenv file. Removing a file-owned
assignment restores its independently configured fallback or clears the value when no fallback exists.
A read or parsing failure keeps the last usable credentials and reports how to correct the file.
Values exported when the process started continue to take precedence during reload.


Setup's configuration backup blanks inline secret assignments from older configurations while retaining
other settings and comments. General `--generate-config` backups remain exact copies and can contain
inline credentials. The dotenv file is not backed up during secret replacement.
