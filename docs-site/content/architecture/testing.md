---
title: "Testing your machine"
weight: 4
summary: "Automated tests for your own machine with MPF's test classes: simulated time, pressing switches, draining balls, checking scores, modes and events, and the traps to know about."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

Every rule on this site was checked by a test that starts MPF, plays a game in simulated time and checks what
happened. You can do the same for your own machine. A test that plays a three-ball game with a ball save runs in a
fraction of a second, so you can check every rule after every change instead of playing it by hand.

{{< tip >}}
**Verified.** The machine and the test file on this page were run as a separate process, exactly as below, on MPF
0.82.0.dev0. `docs-site/verify/test_guides.py` repeats that run.
{{< /tip >}}

## Which test class

MPF's tests are Python `unittest` tests built on classes in `mpf/tests/`. For your own machine, use
**`MpfGameTestCase`**: it starts MPF with your machine folder and has helpers for starting and playing a game.

{{< warn >}}
**`mpf test` and `MpfMachineTestCase` need the old media controller.** `mpf test`, which runs tests written as text
files, imports Kivy, and `MpfMachineTestCase` imports `mpfmc`; both belong to MPF-MC, the Kivy-based media controller
that GMC replaces. With GMC and no MPF-MC installed, `mpf test` stopped with `ModuleNotFoundError: No module named
'kivy'`, and a test built on `MpfMachineTestCase` with `No module named 'mpfmc'` (`mpf/commands/test.py`,
`mpf/tests/MpfMachineTestCase.py`). `MpfGameTestCase` has neither import.
{{< /warn >}}

## A test file

Put tests in a `tests` folder in the machine folder. This one tests the machine at the end of the page:

`tests/test_rules.py`:

```python
import os

from mpf.tests.MpfGameTestCase import MpfGameTestCase


class MachineTestCase(MpfGameTestCase):
    """Run this machine folder on the smart virtual platform."""

    def get_machine_path(self):
        # the folder above tests/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def get_config_file(self):
        return "config.yaml"

    def get_platform(self):
        return "smart_virtual"


class TestRules(MachineTestCase):

    def test_ramp_scores_1000(self):
        self.start_game()
        self.hit_and_release_switch("s_ramp")
        self.advance_time_and_run(1)
        self.assertPlayerVarEqual(1000, "score")

    def test_ball_save(self):
        self.mock_event("ball_save_start_save_saving_ball")
        self.start_game()
        self.advance_time_and_run(5)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertEventCalled("ball_save_start_save_saving_ball")
        self.assertBallNumber(1)

    def test_drain_after_the_save_ends_the_ball(self):
        self.start_game()
        self.advance_time_and_run(20)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertBallNumber(2)
        self.assertModeRunning("base")

    def test_two_players_take_turns(self):
        self.start_two_player_game()
        self.assertPlayerCount(2)
        self.advance_time_and_run(20)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(1)
```

The three methods of `MachineTestCase` point MPF at your machine:

- **`get_machine_path`** is the machine folder. MPF's own default is a folder inside MPF, so this must be overridden;
  an absolute path is used as it is.
- **`get_config_file`** is the machine config's file name, in `config/`.
- **`get_platform`** picks the [smart virtual platform](/architecture/platforms/#the-virtual-platforms), which
  moves balls between devices. MPF's test default is the plain virtual platform, which doesn't.

Every test class for the machine then extends `MachineTestCase`. Each test method starts a fresh MPF, so tests don't
affect each other.

## Running the tests

From the machine folder:

```bash
python -m unittest discover -s tests
```

In the test runs this printed a dot per test, then `Ran 4 tests in` well under a second (0.3 to 0.4 s) and `OK`. The
four tests play over a minute of game time between them; simulated time is why that's so quick.

With `-v`, unittest lists each test by name, and MPF's test class also turns on MPF's full log at `DEBUG` level in the
console (`MpfTestCase.setUp`, when the verbosity is above 1). That's a lot of output, but it's exactly what you want
when a test fails and you need to see what MPF did.

## Simulated time

Nothing happens in a test until it advances the clock. **`self.advance_time_and_run(seconds)`** runs MPF for that many
seconds of game time, instantly: ball ejects, timers, delays and shows all move on. A test that checks something right
after pressing a switch usually needs a short `advance_time_and_run` first, for the events to be handled.

## The helpers

From `MpfTestCase` and `MpfGameTestCase` (`mpf/tests/`):

| Helper | What it does |
|---|---|
| `start_game()` | Presses `s_start` and checks a one-player game started. `MpfGameTestCase` adds an `s_start` switch tagged `start` to the config if yours lacks it. |
| `start_two_player_game()`, `add_player()` | Start with two players, or add one. |
| `hit_and_release_switch(name)` | Presses and releases a switch at once, as a ball rolling over it. |
| `hit_switch_and_run(name, seconds)`, `release_switch_and_run(name, seconds)` | Holds or releases a switch, then advances time; for drop targets, held flipper buttons and balls resting on a switch. |
| `drain_all_balls()`, `drain_one_ball()` | Puts balls into the trough, as drains. |
| `post_event(name)` | Posts an event, as if something in MPF had. |
| `mock_event(name)` | Starts recording an event; then `assertEventCalled(name)` or `assertEventCalledWith(name, arg=value)`. |
| `assertPlayerVarEqual(value, name)`, `assertMachineVarEqual(value, name)` | Check a player or machine variable. |
| `assertBallNumber(n)`, `assertPlayerNumber(n)`, `assertPlayerCount(n)`, `assertBallsInPlay(n)` | Check the game's state. |
| `assertModeRunning(name)`, `assertModeNotRunning(name)` | Check a mode. |
| `assertLightColor(name, color)`, `assertSwitchState(name, state)` | Check a light or a switch. |

For anything else, `self.machine` is the whole running machine, as in [mode code](/architecture/mode-code/):
`self.machine.game.player.score`, `self.machine.ball_devices["bd_trough"].balls`, and so on.

## Things to know

- **After a tilt, `drain_all_balls()` drains nothing.** It drains as many balls as the game has in play, and a tilt
  sets that to 0. Add the ball to the trough directly:
  `self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_trough"])`
  (see [Tilt](/build/tilt/)).
- **Startup errors are test results too.** A test can check that a broken config is refused: decorate the method
  with `@expect_startup_error()` (from `mpf.tests.MpfTestCase`) and read `self.startup_error`.
- **Tests don't write your data files.** `MpfTestCase` replaces MPF's data manager, so machine variables and high
  scores set during a test aren't saved to `data/` (`TestMachineController.create_data_manager` in
  `mpf/tests/MpfTestCase.py`).
- **Several machine folders in one test run.** MPF caches the classes it loads for mode code by their `code:` name
  (`Util.string_to_class` uses `lru_cache`), and Python caches the imported modules. Tests for one machine never notice.
  A test run that starts two different machine folders whose modes have the same `code:` name gets the first one's
  class for both; clear `Util.string_to_class.cache_clear()` and the `modes.*` entries in `sys.modules` between them.
  This site's own tests do that.

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base

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

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

ball_saves:
  start_save:
    active_time: 10s
    enable_events: mode_base_started
    timer_start_events: balldevice_bd_trough_ball_eject_success

variable_player:
  s_ramp_active:
    score: 1000
```

The test file is above, as `tests/test_rules.py`.
