# Configuration

Examples on this page use the PyPI command `steam_monitor`. Manual script users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format-by-installation-method).

<a id="configuration-file"></a>
## Configuration File

You can pass most settings as command-line options or save them in a configuration file for later runs.

The easiest way to create this file is `steam_monitor --setup`.

To edit every available setting yourself, generate a default configuration file:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
steam_monitor --generate-config > steam_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
steam_monitor --generate-config steam_monitor.conf
```

> **Windows PowerShell:** Pass the filename directly to `--generate-config`. PowerShell redirection can write UTF-16, which the tool rejects with a "null bytes" error.

When the named file already exists, `--generate-config` asks before replacing it and keeps a timestamped `.bak` backup next to it. Add `--force` to replace it without the question.

The file contains a short explanation above each setting.

A configuration file is read as data, not executed. The tool accepts only `SETTING = value` lines where the name is one of the documented settings and the value is a plain literal such as a string, number, `True`, `False`, `None`, a list or a dictionary. Comments and blank lines are fine.

Imports, function calls, expressions and unknown settings are rejected with the setting and line number to correct.

If the same setting appears in more than one place, the item later in this list wins:

1. Built-in defaults
2. The discovered or explicitly selected configuration file
3. Values from the selected `.env` file
4. Secret environment variables
5. Command-line options

By default the tool looks for a configuration file named `steam_monitor.conf` in the current directory, the home directory (`~`) and the script directory. Use `--config-file` to name another location or `--config-file none` to disable automatic config discovery for one run.

<a id="monitored-target"></a>
## Monitored Target

The Steam target is a positional argument. It is required to start monitoring:

```sh
steam_monitor <steam_target>
```

The target can be a Steam64 ID, a Steam3 identifier, a vanity name or a full profile URL.

To stop repeating it, save it in the configuration file:

```ini
TARGET_STEAM_ID = "76561201960435530"
```

`TARGET_STEAM_ID` accepts the same forms as the command line. Then `steam_monitor` alone starts monitoring that profile. A positional argument still wins, so you can watch someone else for one run without editing the file:

```sh
steam_monitor 76561201960287930
```

<a id="smtp-settings"></a>
## SMTP Settings

Email notifications need SMTP server details for the sending account. Add them to `steam_monitor.conf` or use the setup wizard. Setup checks the login without sending an email. To replace only the password, run `steam_monitor --set-smtp-password`. Password entry is hidden and preserves spaces.

Send one test message to verify the settings:

```sh
steam_monitor --send-test-email
```

Every alert is sent as both HTML and plain text in one message. Mail clients that render HTML show the Steam user, the game, the status and the values that changed in bold, with the profile and store pages as links. Clients that do not fall back to the plain text, which is unchanged.

<a id="webhook-settings"></a>
## Webhook Settings

Steam Monitor can send activity alerts through Discord or the native [ntfy publish API](https://docs.ntfy.sh/publish/). Webhook alerts are independent from email, so either channel can be enabled alone or both can receive the same event.

[`--setup`](setup-and-first-run.md#run-the-setup-wizard) collects the webhook URL and detects the provider from it. To configure it separately, save the private destination through a hidden prompt:

```sh
steam_monitor --set-webhook-url
```

The command checks the URL and saves `WEBHOOK_URL` to `.env` without sending a message. Use `--env-file PATH` for another destination. Select the provider and event switches in `steam_monitor.conf`:

```python
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"  # or "ntfy"
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = True
WEBHOOK_STATUS_NOTIFICATION = False
WEBHOOK_GAME_CHANGE_NOTIFICATION = True
WEBHOOK_LEVEL_XP_NOTIFICATION = False
WEBHOOK_FRIENDS_NOTIFICATION = False
WEBHOOK_GAMES_NOTIFICATION = False
WEBHOOK_NAME_CHANGE_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = True
```

A `WEBHOOK_URL` left unset, or left at its `your_webhook_url` placeholder, switches webhook alerts off at startup instead of failing at the first alert. `--verbose` reports why.

The service is detected from the URL. While `WEBHOOK_PROVIDER` is left at its default, that detection is silent and `--verbose` reports it. A warning appears only when your configuration file sets a provider the URL disagrees with.

Verify delivery without starting monitoring:

```sh
steam_monitor --send-test-webhook
```

<a id="ntfy"></a>
### ntfy

For ntfy.sh or a self-hosted ntfy server, use a complete private topic URL such as `https://ntfy.sh/steam-monitor-long-random-value`. Public `ntfy.sh` URLs select the ntfy request format automatically. Set the provider in `steam_monitor.conf` for a self-hosted endpoint:

```ini
WEBHOOK_PROVIDER = "ntfy"
```

The ntfy provider needs no template. Steam Monitor sends the alert body as a native ntfy message with the subject as its title. Long ntfy text messages are visibly truncated below ntfy's 4 KB boundary so they remain notifications instead of temporary attachments.

Topics on the public ntfy.sh service are public unless protected through an account reservation. Treat an unprotected topic name like a password. Protected ntfy topics can use `NTFY_ACCESS_TOKEN` from an environment variable or dotenv file:

```ini
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

`NTFY_IMAGES` enables bounded Steam avatar or game artwork attachments. It is disabled by default and needs the optional Pillow package:

```sh
pip install "steam_monitor[ntfy-images]"
```

Then enable it in `steam_monitor.conf`:

```ini
NTFY_IMAGES = True
```

If artwork is enabled while Pillow is missing, startup says so, names the exact install command and keeps sending text-only alerts. If image preparation or upload fails, delivery falls back to text. Debug mode records why image preparation failed. Intentional image attachments through `NTFY_IMAGES` are not affected by the text truncation above.

Customize ntfy delivery further through `WEBHOOK_HEADERS`, for example `X-Priority` or `X-Tags`:

```ini
WEBHOOK_HEADERS = {
    "X-Webhook-Title": "{title}",
}
```

Header values support the same placeholders as `WEBHOOK_TEMPLATE` and apply to both Discord and ntfy.

<a id="discord"></a>
### Discord

If you are new to Discord, follow these steps to get your private webhook URL:

1. Open your Steam alerts server and choose the channel that should receive them.
2. Select **Edit Channel**, open **Integrations** then choose **Webhooks**.
3. Create a webhook, choose a name if you want then copy its private URL.
4. Save it with `steam_monitor --set-webhook-url`.

Treat this link like a password because anyone who has it can post through it.

Keep the default provider in `steam_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "discord"
```

Discord alerts carry the same emphasis as the HTML email, since Discord renders markdown in an embed. Bold values stay bold and links stay clickable. Only Discord gets that wording: ntfy receives the plain body, because it would show the markers literally.

<a id="advanced-discord-format-customization"></a>
### Advanced Discord-format customization

`WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` change the sender name and HTTPS avatar for Discord-format payloads:

```ini
WEBHOOK_USERNAME = "Steam Monitor"
WEBHOOK_AVATAR_URL = "https://example.com/path/avatar.png"
```

`WEBHOOK_TEMPLATE` controls the Discord-format request body. It supports these placeholders:

- `{title}`
- `{description}`
- `{version}`
- `{image_url}`
- `{fields}` and `{fields_str}`
- `{color}`
- `{timestamp}`
- `{username}`
- `{avatar_url}`

Discord templates must produce a JSON object. Use a dictionary or a JSON string encoding an object, including legacy strings with doubled object braces. Lists, non-JSON strings and unsupported placeholders are rejected before delivery. Alert text is kept literal and all payloads replace `allowed_mentions` with `{"parse": []}` so alert text cannot trigger Discord mentions. Reloaded settings apply to the next delivery.

`WEBHOOK_TRANSFORMS` applies string methods to shared placeholder values before the template and headers are rendered:

```ini
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
    ("description", "strip"),
]
```

The tuple format is `(field_to_target, method_name, *optional_arguments)`. Invalid templates, avatar URLs, transforms or formatted headers fail before a request is attempted. `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to the Discord request format and are ignored when `WEBHOOK_PROVIDER` is `"ntfy"`. ntfy continues to use its native publish API while transformations and header placeholders use the same shared title and description values.

<a id="terminal-colours"></a>
## Terminal Colours

Terminal output is coloured by default. `COLORED_OUTPUT` and `COLOR_THEME` apply to monitoring output and to the `--setup`, `--doctor` and `--help` screens. `--no-color` turns colour off for all of them.

The `--help` screen is coloured too. Group headings, option names, the values those options take, the example commands and the comments above them each get their own colour, so the screen can be scanned instead of read.

Turn it off for one run:

```sh
steam_monitor <steam_target> --no-color
```

Turn it off permanently in the config file:

```python
COLORED_OUTPUT = False
```

On Windows, install [colorama](https://pypi.org/project/colorama/) for colours in the older Command Prompt. Windows Terminal needs nothing extra.

Each part of the output has a logical name. `COLOR_THEME` in the config file overrides only the names it lists. Combine attributes with spaces or `+`, for example `"bright_cyan bold"` or `"red underline"`. Valid colours are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and their `bright_` variants, plus the `bold`, `dim`, `underline` and `blink` attributes. An empty string leaves that part uncoloured.

The built-in colours apply unless you set `COLOR_THEME`. Older configurations may set every colour explicitly. Remove that block to use current defaults or edit individual values to keep a custom theme. The old `steam_id` key is still accepted as `id`.

```python
COLOR_THEME = {
    "game": "bright_magenta bold",
    "duration": "cyan",
}
```

The four presence colours apply where the tool reports a state, such as a `Status:` row, a status change line or a capitalised state like `*** User got OFFLINE !`. A sentence that only mentions a state, such as the liveness line `The user is offline with no status or game change since the last check`, stays in the default colour. The two boolean colours apply to a `Yes` or `No` that is the whole value of a labelled row, not to the word inside a sentence.

| Theme key | Default | What it colours |
| --- | --- | --- |
| `header` | `bright_cyan` | Report and wizard headings, plus the ASCII banner |
| `section` | `bright_white` | Section names and every command the tool tells you to run |
| `username` | `bright_cyan underline` | The monitored account name and the detected install method |
| `id` | `bright_magenta` | The Steam64 ID |
| `status_online` | `green` | An online presence |
| `status_offline` | `red` | An offline presence |
| `status_away` | `yellow` | An away presence |
| `status_snooze` | `magenta` | A snooze presence |
| `status_other` | `white` | A presence value the tool does not recognise |
| `game` | `bright_yellow` | Game titles |
| `duration` | `green` | Time spans such as `3 hours, 21 minutes` |
| `timestamp_label` | *(empty)* | The `Timestamp:` label, left uncoloured by default |
| `timestamp_value` | `cyan` | The timestamp itself |
| `info` | `cyan` | `To fix:` lines, notes, prompts and `[SKIP]` rows |
| `warning` | `yellow` | `* Warning:` lines and `[WARN]` rows |
| `error` | `red` | `* Error:` lines and `[FAIL]` rows |
| `signal` | `yellow` | `* Signal ... received` lines |
| `email` | `bright_cyan` | Lines reporting an email being sent |
| `webhook` | `bright_blue` | Lines reporting a webhook being sent |
| `date` | `magenta` | Single dates and times |
| `date_range` | `magenta` | Date and time ranges |
| `boolean_true` | `green` | `True`, `Enabled`, `On`, a `Yes` answer and `[PASS]` rows |
| `boolean_false` | `red` | `False`, `Disabled`, `Off` and a `No` answer |
| `link` | `blue underline` | URLs |
| `help_heading` | `bright_cyan bold` | The `--help` group headings and example task names |
| `help_usage` | `bright_white bold` | The `usage:` label |
| `help_option` | `bright_green` | Option names such as `--doctor` |
| `help_metavar` | `yellow` | The value each option takes, such as a path or a number of seconds |
| `help_placeholder` | `bright_magenta` | Values to replace in the help examples |
| `help_command` | `bright_white` | The commands in the help examples |
| `help_comment` | `bright_black` | The `#` comment above each help example |
| `help_default` | `bright_black` | The `(default: ...)` notes |

<a id="storing-secrets"></a>
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

Use `steam_monitor --set-smtp-password` after configuring the other SMTP settings. It checks sign-in before saving and keeps input hidden. An exported `SMTP_PASSWORD` overrides the saved value at startup.

Secret commands save the dotenv file with owner-only permissions and leave the original intact if writing fails. Replaced secrets are not backed up.

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

Secret commands update the selected value without changing other dotenv settings. Clearing a value removes its assignment.

<a id="tls-verification"></a>
## TLS Verification

The tool verifies the TLS certificate of every server it contacts: the Steam Web API, the connectivity check endpoint, the mail server that delivers email alerts and, when enabled, the webhook service.

Set `VERIFY_SSL` to `False` only on a network that intercepts TLS with its own certificate authority, such as a corporate proxy. With verification off, an intercepted connection cannot be told apart from the real service.

The startup summary shows `TLS verification` and [`--doctor`](troubleshooting.md#doctor-preflight) reports a warning while it is off.

