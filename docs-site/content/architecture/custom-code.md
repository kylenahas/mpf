---
title: "Machine-wide custom code"
weight: 3
summary: "Code that isn't tied to a mode: custom_code classes, when they load, handlers that stay for the life of the machine, and when to pick custom code over mode code."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

[Mode code](/architecture/mode-code/) lives and dies with its mode. Some code should run for as long as the machine is
on, in attract mode and between games: counting games, reacting to the coin door, or watching for the machine sitting
idle. That's what `custom_code:` is for.

This page builds a small `GameStats` class that counts finished games in a machine variable and posts
`attract_idle` when the machine has sat in attract mode for 30 seconds after a game.

{{< tip >}}
**Verified.** The machine and code on this page were run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart
virtual platform. The behaviour below is from those runs, and `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## Loading it

The machine config lists the classes to load, by import path:

```yaml
custom_code: machine_code.game_stats.GameStats
```

MPF puts the machine folder on Python's import path at startup, so `machine_code.game_stats.GameStats` is the class
`GameStats` in `machine_code/game_stats.py` in the machine folder. `custom_code:` takes a list, so several classes can
be loaded, separated by commas or as a YAML list (`MachineController._load_custom_code`).

{{< note >}}
**Don't call the folder `code`.** Python has a standard module called `code`, and it wins: in a test run with the
folder renamed to `code`, MPF stopped at startup with `No module named 'code.game_stats'; 'code' is not a package`. Any
other name works; this page uses `machine_code`.
{{< /note >}}

## The code

`machine_code/game_stats.py`:

```python
from mpf.core.custom_code import CustomCode


class GameStats(CustomCode):

    def on_load(self):
        # Called once, while MPF starts. These handlers stay for the life of the machine.
        self.machine.events.add_handler("game_started", self.game_started)
        self.machine.events.add_handler("game_ended", self.game_ended)

    def game_started(self, **kwargs):
        self.delay.remove("idle")

    def game_ended(self, **kwargs):
        played = (self.machine.variables.get_machine_var("games_played") or 0) + 1
        self.machine.variables.set_machine_var("games_played", played, persist=True)
        self.delay.reset(ms=30000, callback=self.idle, name="idle")

    def idle(self):
        self.machine.events.post("attract_idle", games_played=self.machine.variables.get_machine_var("games_played"))
```

- **`on_load`** is the only method MPF calls itself. It runs once, from the class's constructor, while MPF starts.
- **`self.machine`** is the whole machine, as in mode code. There's no `self.player`: outside a game there is none.
  During a game, `self.machine.game.player` is the current player.
- **`self.machine.events.add_handler`** adds a handler that is never removed automatically. That's what you want here,
  and why the class has no stop method.
- **`self.delay`** is a delay manager, as in a mode, but nothing clears it for you. A named delay can be replaced
  with `reset` or cancelled with `remove`, as above.
- **`set_machine_var(..., persist=True)`** marks the variable to be saved to disk and loaded at the next start, if
  `mpf: save_machine_vars_to_disk` is on, which is the default (`config_spec.yaml`). The test runs don't restart MPF,
  so the saving itself wasn't checked.

## When it loads

Custom code is created between `init_phase_3` and `init_phase_4` (`MachineController._run_init_phases`), after the
devices and modes are set up and before the machine resets into attract mode. So `on_load` can look up devices and
add handlers for any event, but the game hasn't started and no mode is running yet. In the test run, `GameStats` was
already loaded, with its handlers in place, before the first game started. See
[From boot to game](/architecture/boot-and-config/) for the whole startup order.

## Custom code or mode code?

| | Mode code | Custom code |
|---|---|---|
| Runs | While its mode runs | From startup until MPF stops |
| Handlers | `add_mode_event_handler`, removed when the mode stops | `machine.events.add_handler`, never removed |
| Delays | Cleared when the mode stops | Never cleared automatically |
| Player | `self.player` | `self.machine.game.player`, during a game |
| Config | The mode's own file, with its players and devices | None of its own |
| Good for | A rule: something that happens during play | The machine: counting, watching, connecting things |

Most code belongs in a mode. Reach for custom code when the code must run outside of games or across them.

## What happened in the test run

| Step | `games_played` | What happened |
|---|---|---|
| MPF has started, no game yet | not set | `GameStats` is loaded, with its two handlers |
| A one-ball game is played | 1 | `game_ended` added 1 and started the 30-second idle delay |
| 20 s later, another game starts | 1 | `game_started` cancelled the delay: no `attract_idle` |
| That game ends | 2 | A new 30-second delay |
| 30 s later | 2 | `attract_idle` with `games_played: 2` |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

custom_code: machine_code.game_stats.GameStats

machine:
  balls_installed: 1

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:

coils:
  c_trough_eject:
    number:

ball_devices:
  bd_trough:
    ball_switches: s_trough1
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 2s
    tags: trough, drain, home

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

game:
  balls_per_game: 1

virtual_platform_start_active_switches: s_trough1
```

`game: balls_per_game: 1` keeps the test games short. The code file is above, as `machine_code/game_stats.py`.
