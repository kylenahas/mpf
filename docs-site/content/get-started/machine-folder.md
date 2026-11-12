---
title: "The machine folder"
weight: 2
---

An MPF machine is a folder. MPF is told where it is (the current directory, or the first argument to `mpf`), then
loads configuration from fixed places inside it. This page describes those places, taken from
`mpf/core/config_loader.py` and `mpf/mpfconfig.yaml`.

## Layout

```text
my_machine/
  config/
    config.yaml          main machine config (default name)
  modes/
    attract/
      config/attract.yaml
    base/
      config/base.yaml
      code/              optional Python for this mode
  shows/                 optional show files: every *.yaml here (subfolders included) is a show named after the file
                         (modes can also have their own modes/<mode>/shows/ folder)
  data/                  written by MPF at runtime (see below)
```

## What loads, in what order

1. MPF's own defaults: `mpf/mpfconfig.yaml` (shipped with MPF). It sets logging levels, file paths, and lists which
   core modules, devices, config players and platforms exist.
2. Your machine config file(s): `config/config.yaml`, or the files you pass with `-c`. Several files are
   **merged** in the order given, with later files overriding earlier ones.
3. For each name in the `modes:` list of the machine config, a mode config at `modes/<name>/config/<name>.yaml`. If MPF
   ships a built-in mode with that name (see [built-in modes](/reference/builtin-modes/)), the built-in config is loaded
   first and your file is merged on top.

A mode named in `modes:` with no config file in either place stops MPF with an error that tells you the exact path it
expected (`modes/<name>/config/<name>.yaml`).

## The `modes:` list

The generated `config.yaml` is just:

```yaml
#config_version=6

modes:
  - attract
  - base
```

`attract` and `base` come from `mpf init`. `attract` is a built-in mode that MPF starts after boot and between games.
MPF's own `mpfconfig.yaml` already lists `attract` and `game`, and your list is added to it, so the `game` mode is
always available without being named.
`base` is your own mode: the template starts it on `ball_starting` and stops it on `ball_will_end`, so it is the
natural place for rules that apply for the whole of every ball.

Shows can also be defined inline in a `shows:` section. A show name defined twice (for example a file and an inline
entry, or two files in different folders) stops MPF with a "Duplicate show" error.

## Files MPF writes

`mpfconfig.yaml` defines these default paths (relative to the machine folder):

| Setting | Default path | Contents |
|---|---|---|
| `mpf: paths: machine_vars` | `data/machine_vars.yaml` | Persisted machine variables |
| `mpf: paths: audits` | `data/audits.yaml` | Auditor data |
| `mpf: paths: high_scores` | `data/high_scores.yaml` | High scores |
| `mpf: paths: earnings` | `data/earnings.yaml` | Earnings data |

Do not edit these by hand while MPF is running.

## The config cache

To start faster, MPF stores a processed copy of your configs (a pickle) and reuses it while the source files have
not changed. If you suspect stale config, start with `mpf game -a` (reload from files) or `-A` (do not write the cache).

## Version header

Config files start with `#config_version=6`. The current MPF expects config version **6** (`_version.py`).

Next: [your first machine](/get-started/first-machine/).
