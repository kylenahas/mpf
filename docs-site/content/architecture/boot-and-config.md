---
title: "From boot to game"
weight: 6
summary: "What MPF does between `mpf game` and attract mode: loading and merging config files, the config cache, validation, the five init phases, and the reset into attract mode."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

This page follows MPF from the moment it starts to the moment attract mode is running: where the config comes from,
how files are combined and checked, and what MPF builds in each step of its startup. It explains several things the
rest of the site uses, such as why a list in your copy of a built-in mode is added to MPF's list, and when custom code
and mode code first run.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart virtual
platform, with every event MPF posted recorded. The merge rules were checked by calling MPF's merge function, and the
cache by loading the same files twice. `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## 1. Loading the config

MPF reads its config in this order (`YamlMultifileConfigLoader.load_mpf_config` in `mpf/core/config_loader.py`):

1. **`config_spec.yaml`**, MPF's description of every section and setting, with types and defaults.
2. **The machine config**: MPF's own `mpf/mpfconfig.yaml` first, then your `config/config.yaml` on top. `mpf game -c
   a.yaml,b.yaml` loads several machine files in that order instead of `config.yaml`.
3. **Each mode in `modes:`**: MPF's copy of the mode first, if it's a built-in mode, then
   `modes/<name>/config/<name>.yaml` from your machine folder on top.
4. **Shows**, from the `shows` folders.

### Splitting a config into files

A config file can include others with `config:`, relative to its own folder:

`config/config.yaml`:

```yaml
#config_version=6

config: hardware.yaml

modes:
  - base

machine:
  balls_installed: 2
```

`config/hardware.yaml`:

```yaml
#config_version=6

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_trough2:
    number:
  s_ramp:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:

ball_devices:
  bd_trough:
    ball_switches: s_trough1, s_trough2
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 2s
    tags: trough, drain, home

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

virtual_platform_start_active_switches: s_trough1, s_trough2
```

Splitting the hardware from the rules this way keeps each file short. The included file is merged **over** the file
that includes it (`ConfigProcessor._load_config_file_and_return_loaded_files`), so if both set the same value, the
included file's value is used. In the test run, the switches from `hardware.yaml` were all there, and with
`machine: balls_installed: 3` added to `hardware.yaml`, the machine had 3 balls, not the 2 from `config.yaml`.

### How files are merged

Every "on top" above is the same merge, `Util.dict_merge`:

| In the later file | Result |
|---|---|
| A section or setting that's new | Added. |
| A section that exists, holding settings | Merged setting by setting, at every level. |
| A single value that exists | Replaced. |
| A list that exists | **Appended** to the existing list. |
| A section with `_overwrite: true` inside | Replaces the existing section completely. |
| A section with `_delete: true` inside | Removes the existing section. |

The appending of lists is why [changing a built-in mode](/build/modes/#changing-a-built-in-mode) sometimes needs
`_overwrite`. Each row of the table was checked by merging two small configs with `Util.dict_merge` in the
test run.

### The config cache

Reading and checking YAML takes time, so MPF keeps a cache. After loading a set of files, it saves the result in the
system's temporary folder, in a file named after a hash of the files' paths (`<hash>.mpf_cache`). Next time, if no
file in the set (including files pulled in with `config:`) has changed since the cache was written, MPF loads the
cache instead (`ConfigProcessor.load_config_files_with_cache`).

In the test run, loading `config.yaml` wrote the cache file to the temporary folder; loading it again read the cache.
After `hardware.yaml`, the included file, was changed, MPF read the cache, saw the change (`Config file in cache
changed`), and loaded the files instead.

Two options of `mpf game` control it: `-a` loads from the files even if a cache exists, and `-A` doesn't write a
cache. If MPF ever seems to ignore a config change, `-a` rules the cache out.

### Checking the config

Each file is checked as it's loaded: section names against `config_spec.yaml`, then, as each device or player is set
up, every setting's type and value, with defaults filled in for settings you left out. These checks produce the error
messages in [Debugging](/build/debugging/#common-mistakes-and-their-messages). Some mistakes only show up later, when
a value is first used; Debugging lists those too.

## 2. Building the machine

With the config loaded, `MachineController.initialize` (`mpf/core/machine.py`) loads the hardware platforms and MPF's
core parts, then posts five **init phases** as queue events. Each part of MPF hooks the phase it needs, so the phases
are what decide the startup order. From the handlers registered in MPF's source:

| Phase | What happens, among other things |
|---|---|
| `init_phase_1` | Devices are created from the config (`DeviceManager`); mode configs are loaded and mode objects created (`ModeController.load_modes`); config players and the show controller are set up. |
| `init_phase_2` | Modes are initialized, which calls each mode's `mode_init` (`ModeController.initialize_modes`); switches are read from the hardware; ball devices create their ball counters; machine-wide control events are connected; BCP connects to the media controller. |
| (between 2 and 3) | Plugins are loaded. |
| `init_phase_3` | Shows and assets are loaded. |
| (between 3 and 4) | [Custom code](/architecture/custom-code/) is loaded: each class is created, which calls its `on_load`. |
| `init_phase_4` | The ball controller starts its task that sends new balls to the playfield; MPF's own BCP servers start. |
| `init_phase_5` | Ball devices with an unstable count try to reorder their balls. |

In the test run, the base mode's `mode_init` posted an event during `init_phase_2`, and a custom code class's
`on_load` posted one after `init_phase_3` and before `init_phase_4`, in the order the table gives.

After the phases, the hardware platforms are started, and MPF waits for any **boot holds**: parts of MPF that asked
for startup to wait, for example for a media controller to connect. Then it posts `init_done`.

## 3. Reset and attract mode

`init_done` leads to the reset: `machine_reset_phase_1`, `_2` and `_3`, which devices use to return to their start
state. Drop targets and drop target banks, for example, have `machine_reset_phase_3` in their default `reset_events`
(`config_spec.yaml`). Then `reset_complete`. The `attract`
mode starts on `reset_complete`, and the machine is ready for a game.

In the test run, the recorded events went `init_done`, `machine_reset_phase_1`, `machine_reset_phase_2`,
`machine_reset_phase_3`, `reset_complete`, then `mode_attract_started`. [How events
work](/architecture/how-events-work/#a-game-event-by-event) continues the timeline from there to the end of a game.

## The complete machine

The machine config is the two files under [Splitting a config into files](#splitting-a-config-into-files).

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100
  code: base.Base

variable_player:
  s_ramp_active:
    score: 1000
```

`modes/base/code/base.py`:

```python
from mpf.core.mode import Mode


class Base(Mode):

    def mode_init(self):
        self.machine.events.post("base_mode_init")
```

The test also loaded a `custom_code:` class whose `on_load` posts `custom_code_loaded`, to see where custom code runs;
see [Machine-wide custom code](/architecture/custom-code/) for a complete one.
