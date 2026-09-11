# Setup & First Run

## Before You Start

Install the tool using [Installation](installation.md). You will need a Steam64 ID or complete Steam community profile URL and the [Steam Web API key](#steam-web-api-key). The wizard collects credentials through hidden prompts.

Open a terminal in the directory where you want to keep the configuration and monitoring output. Later commands should use that directory or explicitly select the same `--config-file` and `--env-file` paths. Manual installations use the [command equivalents](usage.md#command-format).

<a id="setup-wizard"></a>
## Guided Setup

The quickest way to a working configuration is to answer a few questions:

```sh
steam_monitor --setup
```

The wizard asks for the profile, whether to save it, polling interval, your Steam Web API key, alerts and output files. Press Enter to accept a default. Review or change any section before choosing **Save**. Ctrl+C cancels without saving.

Enter a **Steam64 ID, Steam3 identifier, vanity name or full profile URL**. Intervals accept seconds or durations such as `30s`, `2m`, `1.5h`, `1h 30m` and `1d`.

For webhook alerts, setup asks which service receives them, then takes the Discord webhook URL or an ntfy topic. A bare ntfy.sh topic name is expanded to its full URL. For ntfy it also offers a separate access token and artwork attachments.

Setup explains invalid answers and lets you retry or continue with the affected feature disabled. Email setup checks sign-in without sending a message. If the mail server is unreachable, check the saved settings later with `--doctor`.

Secrets go to `.env` and other settings go to `steam_monitor.conf`. Setup asks before replacing files or saved secrets. A rerun uses saved settings as defaults. Declining a section disables it. See [Storing Secrets](configuration.md#storing-secrets) for backup details.

Use `--config-file PATH` and `--env-file PATH` or the summary's **File destinations** section to choose other files. Both paths must be writable. `--config-file none` and `--env-file none` are not supported by setup.

After saving, setup offers [Doctor Preflight](troubleshooting.md#doctor-preflight) and can start monitoring once the checks pass.

With [`TARGET_STEAM_ID`](configuration.md#target-profile) saved, running without arguments starts monitoring that profile. Otherwise, it shows starting commands and offers the wizard in an interactive terminal.

If there is no terminal to answer on, setup says so and points at `--generate-config` instead of hanging.

## Quick Start

If you would rather configure it by hand, first save your [Steam Web API key](#steam-web-api-key) through the hidden prompt:

```sh
steam_monitor --set-steam-api-key
```

Then pass the profile as `steam_target` to start monitoring:

```sh
steam_monitor <steam_target>
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 steam_monitor.py --set-steam-api-key
python3 steam_monitor.py <steam_target>
```

To get the list of all supported command-line arguments / flags:

```sh
steam_monitor --help
```

## Steam Web API key

You can get the Steam Web API key here: [http://steamcommunity.com/dev/apikey](http://steamcommunity.com/dev/apikey)

Provide the `STEAM_API_KEY` secret using one of the following methods:

 - Answer the questions in `--setup`, which validates and saves it for you (recommended)
 - Save and validate it through a hidden prompt with `--set-steam-api-key`
 - Set it as an [environment variable](configuration.md#storing-secrets), for example `export STEAM_API_KEY=...`
 - Add it to a [.env file](configuration.md#storing-secrets) as `STEAM_API_KEY=...` for persistent use
 - Pass it at runtime with `-u` / `--steam-api-key`

The hidden prompt validates the key with Steam before saving it to `.env`:

```sh
steam_monitor --set-steam-api-key
```

For a custom private settings file:

```sh
steam_monitor --set-steam-api-key --env-file /path/.env-steam_monitor
```

A key passed with `-u` / `--steam-api-key` may remain visible in shell history or process listings.

Fallback:

 - Hard-code it in the code or config file

If you store the `STEAM_API_KEY` in a dotenv file you can update its value and send a `SIGHUP` signal to the process to reload the file with the new API key without restarting the tool. More info in [Storing Secrets](configuration.md#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

## User Privacy Settings

In order to monitor Steam user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [Steam Privacy Settings](https://steamcommunity.com/my/edit/settings).

The value in **My Profile → Game details** should be set to **Friends Only** or **Public**.

## Continue with Usage

Use [Usage](usage.md) for monitoring and output options or [Configuration](configuration.md) to adjust saved settings. If setup or monitoring fails, run [Doctor Preflight](troubleshooting.md#doctor-preflight) and follow the reported recovery steps.
