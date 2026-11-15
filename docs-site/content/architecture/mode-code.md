---
title: "Writing mode code"
weight: 2
summary: "When config isn't enough: a Python class for a mode, its lifecycle methods, handlers and delays that clean up after themselves, the player and devices, and settings from the mode's config."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

Most rules fit in config: [shots](/build/shots-and-scoring/), [counters and timers](/build/events/#more-examples),
`variable_player`, `event_player`. Some don't, usually because they need to remember a list, choose between options,
or decide something that depends on several things at once. For those, a mode can have Python code. The config still
does what it does well, and the code only does the part config can't.

This page builds a **mystery award**: the scoop gives a random award that the player hasn't had yet, and once they've
had them all, the list starts over. After an award, the mystery is unlit for 5 seconds.

{{< tip >}}
**Verified.** The machine and code on this page were run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart
virtual platform. The behaviour below is from those runs, and `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## Connecting code to a mode

A mode's config names its class with `code:`:

```yaml
mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 200
  code: mystery.Mystery
```

MPF puts the machine folder on Python's import path when it starts (`MachineController._set_machine_path`), then
tries `code:` as a full import path. If that fails, it looks in the mode's own `code` folder: `mystery.Mystery` means
the class `Mystery` in `modes/mystery/code/mystery.py` (`ModeController._load_mode_code`). The built-in modes use the
full form, for example `mpf.modes.carousel.code.carousel.Carousel`.

The class extends MPF's `Mode`. Everything the config sets up (its `variable_player`, `show_player`, devices and so
on) still works; the class adds to it.

## The code

`modes/mystery/code/mystery.py`:

```python
import random

from mpf.core.mode import Mode
from mpf.core.utility_functions import Util


class Mystery(Mode):

    def mode_init(self):
        # Once, when MPF loads the mode at startup.
        settings = self.config.get("mode_settings", {})
        self.awards = Util.string_to_list(settings.get("awards", "points"))
        self.relight_ms = settings.get("relight_ms", 5000)

    def mode_start(self, **kwargs):
        # Each time the mode starts. Handlers added here are removed when it stops.
        self.lit = True
        self.add_mode_event_handler("s_scoop_active", self.scoop_hit)

    def scoop_hit(self, **kwargs):
        if not self.lit:
            return
        collected = [a for a in (self.player["mystery_collected"] or "").split(",") if a]
        choices = [a for a in self.awards if a not in collected] or self.awards
        if len(choices) == len(self.awards):
            collected = []
        award = random.choice(choices)
        collected.append(award)
        self.player["mystery_collected"] = ",".join(collected)
        self.machine.events.post("mystery_award", award=award)
        self.lit = False
        self.delay.add(ms=self.relight_ms, callback=self.relight)

    def relight(self):
        self.lit = True
        self.machine.events.post("mystery_lit")

    def mode_stop(self, **kwargs):
        # Each time the mode stops. Its handlers and delays are already gone.
        self.machine.events.post("mystery_stopped", collected=self.player["mystery_collected"])
```

`modes/mystery/config/mystery.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 200
  code: mystery.Mystery

mode_settings:
  awards: small_points, big_points, extra_time
  relight_ms: 5000

variable_player:
  mystery_award{award=="small_points"}:
    score: 5000
  mystery_award{award=="big_points"}:
    score: 25000
  mystery_award{award=="extra_time"}:
    mystery_extra_time: 1
```

The code decides **which** award; the config decides **what each award does**, with conditions on the event's
`award` argument. Changing an award's value, or adding a show for it, needs no code.

## The lifecycle

| Method | When it runs | Use it for |
|---|---|---|
| `mode_init(self)` | Once, when MPF loads the mode at startup | Reading settings, building lookup tables |
| `mode_will_start(self, **kwargs)` | Each start, before the mode is active | Rarely needed |
| `mode_start(self, **kwargs)` | Each start, once the mode is active | Adding handlers, resetting per-start state |
| `mode_stop(self, **kwargs)` | Each stop | Saving state, posting a summary event |

All four are empty in `Mode`, so a class only defines the ones it needs (`mpf/core/mode.py`). In the test run, the
awards list that `mode_init` builds was already there before the first game started, and `mode_start` ran at the start
of each ball (`mode_mystery_started`).

## Handlers and delays that clean up

**`self.add_mode_event_handler(event, handler)`** adds an event handler that MPF removes when the mode stops. Its
priority is the mode's priority plus the optional `priority` argument, so a higher mode's handlers run first, as
config players do. Every handler needs `**kwargs`, since events carry arguments.

**`self.delay`** is the mode's delay manager: `self.delay.add(ms=..., callback=...)` calls back later, and
`self.delay.reset(...)` with a `name` restarts a named delay. When the mode stops, MPF clears all its delays
(`Mode.stop`). In the test run, a ball that drained 2 seconds after an award ended with the mystery unlit, and
`mystery_lit` was never posted: the delay died with the mode, and the next ball's `mode_start` lit it again.

Handlers added with `self.machine.events.add_handler` instead are **not** removed; that's for code that should keep
listening after the mode stops (see [machine-wide custom code](/architecture/custom-code/)).

## The player and the machine

- **`self.player`** is the current player while a game mode runs. `self.player["name"]` reads a player variable, `0`
  if it was never set, and assigning to it sets one. A change to a number or string posts `player_<name>`, so config
  and displays can react, as with any player variable. `mystery_collected` above is a string of names for that reason.
- **`self.machine`** reaches everything else: `self.machine.events.post(...)`, devices by type and name
  (`self.machine.switches["s_scoop"].state`, `self.machine.shots["left_ramp"]`), `self.machine.game`, and machine
  variables with `self.machine.variables.get_machine_var(...)`.
- **`self.config`** is the mode's config file as a dictionary. A `mode_settings:` section is a good place for your own
  settings, as above. MPF passes it through as YAML read it: `awards` arrived as one string,
  `"small_points, big_points, extra_time"`, which is why the code splits it with `Util.string_to_list`, MPF's own helper
  for comma-separated lists. `relight_ms: 5000` arrived as the number 5000.

{{< note >}}
**An unset player variable reads as `0`, not as an empty string.** In the first version, the code called
`.split(",")` on `self.player["mystery_collected"]` and stopped with `'int' object has no attribute 'split'` on the
first scoop. `or ""` turns the `0` into an empty string.
{{< /note >}}

## What happened in the test run

The award is random, so the test replaced `random.choice` with one that picks the first remaining award, in the order
of `mode_settings`. Everything else is as MPF ran it.

| Step | Score | `mystery_collected` | Events |
|---|---|---|---|
| Ball 1 starts | 0 | (unset, reads `0`) | `mode_mystery_started` |
| Scoop | 5,000 | `small_points` | `mystery_award` with `award: small_points`, `player_mystery_collected` |
| Scoop again at once | 5,000 | `small_points` | Nothing: unlit |
| 5 s later | | | `mystery_lit` |
| Scoop | 30,000 | `small_points,big_points` | `mystery_award` with `big_points` |
| Scoop, 5 s later | 30,000 | `small_points,big_points,extra_time` | `extra_time`: `mystery_extra_time` became 1 |
| Scoop, 5 s later | 35,000 | `small_points` | All three collected: the list started over |
| Scoop, 5 s later, then the ball drains 2 s after it | 60,000 | `small_points,big_points` | `mystery_stopped`; no `mystery_lit`, the delay was cleared |
| Ball 2 starts | | | `mode_mystery_started`: lit again |
| Scoop | 60,000 | `small_points,big_points,extra_time` | `extra_time`: the list carried over from ball 1 |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - mystery

machine:
  balls_installed: 2

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_trough2:
    number:
  s_scoop:
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

The mode's two files are above: `modes/mystery/code/mystery.py` and `modes/mystery/config/mystery.yaml`.
