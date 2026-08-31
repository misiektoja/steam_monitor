# Troubleshooting

## Doctor Preflight

Before monitoring anything, `--doctor` checks whether the setup is actually ready and reports what is not:

```sh
steam_monitor --doctor <steam_user_id>
```

It is **read-only**: it writes no files, and it says so before the first check runs. Checks are grouped into **Environment**, **Configuration**, **Connectivity**, **Authentication**, **Target** and **Notifications**, and each row is marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`. Every non-passing row carries a `To fix:` line and a link to the relevant section here.

The Configuration section names the configuration and dotenv files in effect and reports **which secrets came from the dotenv file and which came from the environment**, by name only. No secret value is ever printed.

When email or webhook alerts validate and you are at a terminal, doctor then offers to send **one real test message per channel**, each behind its own confirmation. Declining is the default. Nothing is sent without an explicit `y`, so a scripted or containerized run stays message-free.

It exits `0` when every check passed and `1` when any check or approved delivery test failed, so it can be used as a container healthcheck or a CI smoke test:

```sh
steam_monitor --doctor <steam_user_id> && echo "ready"
```

Running it without a Steam64 ID checks everything except the monitored profile.

## When Something Goes Wrong

Every failure is reported in the same three-part shape:

```
* Error: Steam rejected the configured Web API key
To fix: Validate and replace it with 'steam_monitor --set-steam-api-key'
Guide: https://github.com/misiektoja/steam_monitor/blob/main/README.md#steam-web-api-key
```

The `To fix:` line names the command for the way you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as-is. The `Guide:` line links the section of this document that covers it.

Adding `--debug` appends a `Technical detail:` line with the underlying exception. That detail is for a bug report; the `To fix:` line is the one to act on. Secret values are redacted from all three.

During monitoring, a failure that keeps recurring prints its one-line summary each cycle but repeats the `To fix:` line only when the kind of failure changes, so a long Steam outage cannot fill the log with the same paragraph. A failure that is worth retrying, such as a timeout or a Steam outage, gets one short retry before the tool falls back to waiting a full polling interval. A rate limit waits for the period Steam asked for, and a rejected API key is not retried at all.
