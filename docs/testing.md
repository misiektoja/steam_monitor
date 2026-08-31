# Testing

The offline test suite covers everything in `steam_monitor.py` that can run without network access. Steam client and Web API calls are replaced with test doubles.

## Running the suite

From the repository root:

```sh
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests exercise the working tree rather than an installed copy.

Run the linter the same way CI does:

```sh
pip install -e '.[lint]'
python -m ruff check steam_monitor.py tests
```

Build this documentation the way CI does, which fails on a broken link or a missing page:

```sh
pip install -r docs/requirements.txt
mkdocs build --strict
```

CI runs all three on every push and pull request, across Python 3.9 through 3.14, and again before anything is published to PyPI.

## What is covered

The test layout mirrors the surfaces a user touches rather than the module layout. See [tests/README.md](https://github.com/misiektoja/steam_monitor/blob/main/tests/README.md) for the file-by-file map.

## Conventions

* Keep every test offline. If a code path needs network access, stub it with `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a leaked global affects whatever runs next.
* Never use a real Steam Web API key, SMTP password or webhook URL.

A change to the monitoring loop, authentication or Steam data handling is not verified by this suite alone. Exercise it against a real account and say so in the pull request, without usernames or credentials.
