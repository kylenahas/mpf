---
title: "Install and run MPF"
weight: 1
---

This page covers getting MPF running with a project folder. Facts come from `pyproject.toml`, `mpf/commands/` and
`mpf/_version.py` in the MPF source (version `0.82.0.dev0`).

## Requirements

- Python 3.10 up to (not including) 3.15.
- Core dependencies are pinned in `pyproject.toml` (`ruamel.yaml`, `pyserial`, `pyserial-asyncio`, `prompt_toolkit`,
  `Pillow` and a few more). The package manager installs them for you.
- Optional extras exist for specific hardware and features (for example `osc`, `pin2dmd`, `zedmd`, `rpi`, `uvloop`,
  `vpe`). `mpf[all]` pulls in all of them.

{{< note >}}
FAST controllers talk over serial using `pyserial` / `pyserial-asyncio`, which are core dependencies. No extra is
needed for FAST.
{{< /note >}}

## Install

The package is named `mpf` and registers a console script called `mpf`:

```bash
pip install mpf
```

{{< note >}}
This page was written from the source tree, not from a package index. If you are working from a checkout of the
repository, install it with `pip install -e .` from the repository root instead.
{{< /note >}}

Check the install:

```bash
mpf --version
```

This prints the MPF, config file and BCP versions (the `--version` option is defined in `mpf/commands/__init__.py`).

## Create a project folder

```bash
mpf init my_machine
```

`mpf init` (`mpf/commands/init.py`) creates the folder if needed, then writes:

```text
my_machine/
  config/config.yaml
  modes/attract/config/attract.yaml
  modes/base/config/base.yaml
```

It only creates files that do not already exist, so running it again will not overwrite your work. Without a folder
name it initializes the current directory.

## Run it

From inside the project folder:

```bash
mpf game
```

`game` is the default command, so plain `mpf` does the same. You can also pass the machine folder as the first argument.

Useful options (all defined in `mpf/commands/game.py`):

| Option | What it does |
|---|---|
| `-c <file>` | Config file(s) to load instead of `config.yaml`. Comma-separated for several. |
| `-x` | Force the **virtual** platform for every device (no hardware needed; balls do not move). |
| `-X` | Force the **smart virtual** platform for every device (simulates ball ejects; best for testing). |
| `-t` | Use the ASCII text UI instead of the default one. |
| `-b` | Do not try to connect to a BCP server (no media controller). |
| `-v` / `-V` | Verbose logging to the log file / to the console. |
| `-a` | Ignore the config cache and reload from files. |
| `-A` | Do not write the config cache. |
| `-P` | Production mode: for unattended machines, run it inside a restart loop. |

See the full list on the [command line reference](/reference/cli/).

{{< note >}}
Running with no `-x` or `-X` uses whatever platform your `hardware:` section names. With an empty config that is
the `virtual` platform (the default of `hardware: platform`).
{{< /note >}}

## Other commands

`mpf` also has `init`, `both` (starts MPF and the media controller together), `hardware`, `diagnosis`, `service`,
`test`, `wire` and `build`. Packages like the media controller can register more. The reference page lists them.

Next: [what lives in a machine folder](/get-started/machine-folder/).
