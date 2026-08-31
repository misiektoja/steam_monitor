# Third-party notices

steam_monitor original code is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).

The distributed package contains no vendored third-party source. It declares the dependencies below, which are installed from PyPI under their own licenses and remain the property of their authors.

## Runtime dependencies

| Component | License | Use |
| --- | --- | --- |
| [steam](https://pypi.org/project/steam/) | MIT | Steam client and Web API access for presence and game activity |
| [requests](https://pypi.org/project/requests/) | Apache-2.0 | HTTP for the monitored service, notifications and artwork |
| [python-dateutil](https://pypi.org/project/python-dateutil/) | Apache-2.0 or BSD-3-Clause | Timestamp parsing and relative date arithmetic |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | BSD-3-Clause | Reading secrets from `.env` |
| [Pillow](https://pypi.org/project/Pillow/) | MIT-CMU | Artwork handling for image notifications, `ntfy-images` extra |
| [colorama](https://pypi.org/project/colorama/) | BSD-3-Clause | ANSI color support on Windows terminals |

## Build, test and lint dependencies

These are not part of the distributed package.

| Component | License | Use |
| --- | --- | --- |
| [pytest](https://pypi.org/project/pytest/) | MIT | Test suite |
| [PyYAML](https://pypi.org/project/PyYAML/) | MIT | Validating workflows and issue templates in the test suite |
| [Ruff](https://pypi.org/project/ruff/) | MIT | Linting the module and the test suite |
| [pip-audit](https://pypi.org/project/pip-audit/) | Apache-2.0 | Dependency vulnerability audit in the supply chain workflow |
| [CycloneDX](https://pypi.org/project/cyclonedx-bom/) | Apache-2.0 | Software bill of materials in the supply chain workflow |
| [setuptools](https://pypi.org/project/setuptools/), [wheel](https://pypi.org/project/wheel/) | MIT | Package build |

## External services

The tool contacts Steam. Optional notification delivery contacts the SMTP server or webhook endpoint you configure. Nothing is sent anywhere you have not configured.

## Reporting a licensing problem

If you believe a dependency is misattributed here, open an issue or email <misiektoja-github@rm-rf.ninja>.
