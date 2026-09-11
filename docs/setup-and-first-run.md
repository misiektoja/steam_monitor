# Setup & First Run

Before replacing a configuration, setup copies retained inline credentials to the selected private dotenv file when that file has no value for the same key. An existing dotenv value, including an explicit empty value, keeps precedence. If preservation fails, the original configuration stays in place. Setup backups omit inline credentials.

When rebuilding an existing configuration, setup keeps its saved `DOTENV_FILE` unless you pass `--env-file PATH`. A nonempty exported secret takes precedence over the dotenv file. An explicit empty value in that file still overrides the configuration, both after saving and on the next run. Quoted dotenv keys receive the same replacement confirmation as unquoted keys.

Setup replaces each file separately. If saving secrets fails after the configuration was saved, setup stops and identifies the saved configuration. Correct the destination then rerun `--setup` with the same `--config-file` and `--env-file`, review the settings and run `--doctor` before monitoring. A crash between replacements can also leave a new configuration beside the previous dotenv file. The configuration backup can recover non-secret settings. Replaced secrets are not backed up.

## Before You Start

Install the tool using [Installation](installation.md). You will need a Steam64 ID or complete Steam community profile URL and the [Steam Web API key](#steam-web-api-key). The wizard collects credentials through hidden prompts.

Open a terminal in the directory where you want to keep the configuration and monitoring output. Later commands should use that directory or explicitly select the same `--config-file` and `--env-file` paths. Manual installations use the [command equivalents](usage.md#command-format).

<a id="setup-wizard"></a>
## Guided Setup

The quickest way to a working configuration is to answer a few questions:

```sh
steam_monitor --setup
```

It asks for the profile to monitor, whether to save that profile in the config file, how often to check, your Steam Web API key, whether you want email or webhook alerts and where output goes. The output questions ask whether to write the per-target log file and whether to write a CSV file, and the CSV path is asked for only after you say yes, so answering no clears a saved one. A CSV path with no extension is saved with `.csv` added and a status file path with no extension is saved with `.json` added. Enter accepts the shown default and Ctrl+C cancels. **Nothing is written until you choose Save**: the answers are held until the end, where a summary shows exactly what is about to be written and lets you go back and change **one section without losing the other answers**. The summary's **File destinations** section changes where the configuration and dotenv files are written. Moving the dotenv file asks the authentication and notification questions again, since a secret you chose to keep was never going to reach the new file.

Answers are accepted in the formats people actually paste. The profile takes a **Steam64 ID, a Steam3 identifier, a vanity name or a full profile URL**, and is normalized to one canonical Steam64 ID. During fresh setup, a vanity name is resolved after the API key step. Intervals take **`30s`, `2m`, `1.5h`, `1h 30m`, `1d`** or a plain number of seconds. Supported units are `s`, `m`, `h` and `d`.

For webhook alerts, setup asks which service receives them, then takes the Discord webhook URL or an ntfy topic. A bare ntfy.sh topic name is expanded to its full URL. For ntfy it also offers a separate access token and artwork attachments.

Every answer setup cannot use offers a way out, so one value you cannot produce right now does not cost you the answers already given. A blank answer asks whether to continue without it and names what stops working, and a rejected one offers to enter it again. Declining switches the channel that needed it off, so half a mail server or a webhook with no destination is never written. Email setup signs in to the mail server before saving, so a wrong password or an unreachable host is caught during setup instead of at the first alert. No email is sent. A refused sign-in offers the mail server questions again, and if the server was only unreachable the answers are kept so `--doctor` can check them later.

Secrets are typed at a hidden prompt and go to the dotenv file. Non-secret settings go to the config file. Both destinations are checked before the first question, so an unwritable path or a directory given by mistake is reported straight away rather than after you have answered everything. `--setup` needs somewhere to put both files, so it refuses `--config-file none` and `--env-file none`. A configuration file already in place is replaced only after you agree, and setup offers to write somewhere else instead. The replaced file is backed up first. A rebuilt file starts from the settings already in place with your answers applied over them. A section you decline is cleared rather than carried over, so declining email leaves no mail server behind. A secret already in the dotenv file is never replaced without asking. The dotenv file is replaced without a backup, so the secret you replaced is not left behind in a `.bak` file. When it finishes, setup offers to run [`--doctor`](troubleshooting.md#doctor-preflight) and prints the exact commands to start monitoring. For a local install it then offers to **start monitoring right away** once that doctor run passed.

If the config file names a target in [`TARGET_STEAM_ID`](configuration.md#target-profile), running the tool with no arguments starts monitoring that profile. With no saved target, running it **with no arguments at all** prints the commands worth starting with and offers to open the wizard. Answering that offer exits 0. With no terminal to answer on there is no offer, so the run exits 1 like the argument error it replaced.

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

The recommended command keeps the key out of shell history and process listings. It validates the key against the Steam Web API before atomically updating `.env`:

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
