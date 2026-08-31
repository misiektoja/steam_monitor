# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability.

Report it privately through [GitHub security advisories](https://github.com/misiektoja/steam_monitor/security/advisories/new), which keeps the report visible only to the maintainer until an advisory is published. If you cannot use that, email <misiektoja-github@rm-rf.ninja>.

Do not include Steam Web API keys, SMTP passwords, webhook URLs or ntfy tokens or the accounts you monitor in a report. Include the affected version, the impact, the preconditions to reproduce it and a sanitized proof when you have one.

The maintainer will acknowledge the report and coordinate disclosure once a fix is available.

## Supported versions

Security fixes are made on the default branch and shipped in the next release to [PyPI](https://pypi.org/project/steam-monitor/) and the [GitHub releases](https://github.com/misiektoja/steam_monitor/releases). Only the latest released version is supported. Earlier versions receive no backports.

## Security posture

This tool holds credentials for your own Steam access and records what other accounts do. Both matter when you deploy it.

- **The configuration file is executed as Python.** When no `--config-file` is given, the tool loads the first configuration it finds in the current working directory, then your home directory, then the script directory, and runs it. Treat a configuration file as code: only load one you wrote yourself, and do not run the tool from a directory whose contents you do not control. This is a known limitation, tracked for a future release that will parse the file as data instead.
- **Secrets belong in `.env`, not in the configuration file.** Point the tool at a dotenv file with `--env-file` and keep it owner-readable only. A secret placed in the configuration file is read by anything that can read that file.
- **Credentials are masked in output.** Tokens and keys are redacted in the log and in error messages, so a log you attach to an issue does not carry them. Check anything you paste regardless.
- **Monitoring an account is subject to the law where you are.** The tool is intended for accounts you own or are authorized to observe.

## Supply chain

Every GitHub Actions workflow pins third-party actions to a commit SHA with the version recorded alongside it. The test suite fails when a pin or its version comment is missing, or when a workflow passes an event value straight into a shell. Dependencies and actions are tracked by Dependabot. Each change runs secret scanning, a dependency vulnerability audit and an SBOM build. CodeQL analyzes the Python source with the `security-extended` query set, and OpenSSF Scorecard scores the repository's security practices. See [.github/workflows/supply-chain.yml](https://github.com/misiektoja/steam_monitor/blob/main/.github/workflows/supply-chain.yml) and [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/steam_monitor/blob/main/THIRD_PARTY_NOTICES.md).

Publishing to PyPI runs the full test suite first and stops if it fails, so no untested artifact is released under the project's name. The upload runs in a named GitHub environment and uses trusted publishing rather than a stored API token. Release archives carry SHA-256 checksums and a signed build provenance attestation, which `gh attestation verify` checks against this repository.
