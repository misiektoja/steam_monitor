# Historical configuration templates

Each file is the `CONFIG_BLOCK` a released version shipped, extracted from its tag. They exist so
`test_config_upgrades.py` can replay every configuration this tool ever generated through the current parser,
which is what catches a renamed or removed setting that would reject an upgrading user's file.

| File | Released in |
| --- | --- |
| `v1.7.conf` | v1.7 |
| `v1.8.conf` | v1.8 |
| `v1.8.1.conf` | v1.8.1 |
| `v1.9.conf` | v1.9 |
| `v1.9.1.conf` | v1.9.1 |
| `v1.9.2.conf` | v1.9.2 |

Never edit these files. A released template is a historical fact. When a setting is renamed or removed, add the old name to
`RETIRED_CONFIG_SETTINGS` instead.
