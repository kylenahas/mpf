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

Install MPF into a Python **virtual environment** (venv): a folder holding its own copy of Python and its own
packages. MPF and its dependencies then can't clash with other Python software on the computer, and you can keep a
second venv for another MPF version instead of uninstalling one to try the other. Some Linux distributions (Debian 12,
Ubuntu 23.04 and later) refuse `pip install` outside a venv altogether.

Here is the whole install on Linux in one recording: steps 1 to 3 below, then
[creating a project folder](#create-a-project-folder) and listing what it made:

{{< asciicast src="casts/install.cast" poster="npt:20.5" caption="The full install on Ubuntu 22.04 with Python 3.10: create the venv, activate it, `pip install mpf`, check the version, then `mpf init my_machine` and `ls -R` of the new folder. `pip` installed MPF 0.81.0, the current release on PyPI at the time; these docs are written against the 0.82.0.dev0 source." >}}

### 1. Create the venv

Do this once. The examples use a folder named `mpfenv` in your home folder; any name and place will do.

macOS and Linux:

```bash
python3 -m venv ~/mpfenv
```

Windows (PowerShell):

```powershell
python -m venv $HOME\mpfenv
```

The venv uses whichever Python ran the command, so check that it is 3.10 to 3.14 first with `python3 --version`
(`python --version` on Windows). To pick a specific installed version, name it: `python3.12 -m venv ~/mpfenv`.

{{< warn >}}
**Ubuntu and Debian leave out the venv module.** On a stock Ubuntu 22.04, `python3 -m venv` stopped with `The virtual
environment was not created successfully because ensurepip is not available` and asked for the `python3.10-venv`
package. Install it once, then run `python3 -m venv ~/mpfenv` again:

```bash
sudo apt install python3-venv
```
{{< /warn >}}

### 2. Activate it

Activate the venv in every new terminal window before you run `pip` or `mpf`:

| Shell | Command |
|---|---|
| macOS and Linux | `source ~/mpfenv/bin/activate` |
| Windows PowerShell | `~\mpfenv\Scripts\Activate.ps1` |
| Windows Command Prompt | `%USERPROFILE%\mpfenv\Scripts\activate.bat` |

The prompt then starts with `(mpfenv)`, and `python`, `pip` and `mpf` all come from the venv. `deactivate` leaves it.
On the test machine, after `deactivate`, the `mpf` command was no longer found at all.

{{< asciicast src="casts/venv-activate.cast" poster="npt:6.5" caption="Activating and leaving the venv on Ubuntu 22.04. While it is active, `python` is the venv's own copy; after `deactivate` it is back to the system's `/usr/bin/python3`." >}}

{{< note >}}
If PowerShell says running scripts is disabled on this system, its execution policy is blocking `Activate.ps1`. Either
use Command Prompt and `activate.bat`, or allow local scripts for your user once with
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
{{< /note >}}

### 3. Install MPF

With the venv active:

```bash
pip install mpf
```

The package is named `mpf` and registers a console script, also called `mpf`, inside the venv.

{{< note >}}
This page was written from the source tree, not from a package index. If you are working from a checkout of the
repository, install it with `pip install -e .` from the repository root instead (with the venv active).
{{< /note >}}

Check the install:

```bash
mpf --version
```

On the test machine this printed one line:

```text
Mission Pinball Framework v0.82.0.dev0
```

{{< tip >}}
**Trying another version?** Make a second venv (say `mpfenv-next`), activate it and install there. Your working
`mpfenv` stays exactly as it was.
{{< /tip >}}

## Create a project folder

With the venv active:

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

From inside the project folder, with the venv active:

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
