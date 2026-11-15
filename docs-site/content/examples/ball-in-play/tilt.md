---
title: "Tilt with warnings"
weight: 3
summary: "Two warnings from the plumb bob, a tilt on the third that ends the ball with dead flippers and no bonus, and a slam tilt that ends the game."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** The plumb bob gives the player two warnings; the third hit tilts. A swinging bob that touches several
times within 300 ms counts once. A tilt ends the ball at once: the flippers go dead, nothing scores, and the end-of-ball
bonus is skipped. Warnings are cleared for each ball. After a tilt, the next ball waits until the bob has been still
for 5 seconds. The slam tilt switch on the coin door ends the whole game.

**What it uses.** MPF's built-in `tilt` mode, with switch tags, and the built-in `bonus` mode (see the
[end-of-ball bonus](/examples/scoring/end-of-ball-bonus/) example) to show what a tilt skips.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the events and times below are from that run.
{{< /tip >}}

## How it works

The [Tilt guide](/build/tilt/) explains the `tilt` mode in full: its switches, warnings and debounce, what a tilt shuts
off, and its settings and events. This example uses it as it comes, with MPF's default settings. Three things make up
the rule:

- **`tilt` and `bonus` in the `modes:` list.** Both come with MPF; neither needs a config file of its own here, apart
  from the bonus entries.

  ```yaml
  modes:
    - base
    - bonus
    - tilt
  ```

- **Two tagged switches.** The plumb bob has the `tilt_warning` tag and the coin door's slam switch has `slam_tilt`:

  ```yaml
  switches:
    s_plumb_bob:
      number:
      tags: tilt_warning
    s_slam_tilt:
      number:
      tags: slam_tilt
  ```

- **The defaults:** `warnings_to_tilt: 3` (two warnings, then a tilt), a 300 ms
  [tilt debounce](/build/tilt/#tilt-debounce), and a 5 s `settle_time`. To change one, see
  [Changing a built-in mode](/build/modes/#changing-a-built-in-mode), which uses `warnings_to_tilt: 2` as its example.

The mode's events, `tilt_warning`, `tilt` and `tilt_clear`, are what lights, sounds and slides would use; see
[Showing it to the player](/build/tilt/#showing-it-to-the-player).

## What happened in the test run

The test run was a two-player game.

| Time | Step | Player | Score | Warnings | What happened |
|---|---|---|---|---|---|
| 0 s | Two ramps | 1 | 2,000 | 0 | |
| 0.1 s | Plumb bob | 1 | 2,000 | 1 | `tilt_warning` with `warnings_remaining: 2`, `tilt_warning_1` |
| 0.2 s | Plumb bob again | 1 | 2,000 | 1 | Within 300 ms: not counted |
| 1.3 s | Plumb bob | 1 | 2,000 | 2 | `tilt_warning` with `warnings_remaining: 1`, `tilt_warning_2` |
| 2.4 s | Plumb bob | 1 | 2,000 | | `tilt`: the flipper was disabled and the ball ended |
| 2.5 s | Ramp | 1 | 2,000 | | Nothing scored |
| 4.6 s | Plumb bob (still swinging) | 1 | 2,000 | | |
| 4.6 s | The ball drains | 1 | 2,000 | | The game waits for the bob to settle |
| 9.6 s | | 2 | 0 | | 5 s after the last bob hit: `tilt_clear`, then player 2's ball started. No `bonus_start` for player 1. |
| 12.8 s | Ramp, plumb bob | 2 | 1,000 | 1 | |
| 13.8 s | The ball drains | 2 | 6,000 | 0 | The bonus counted (5,000 for one ramp), and player 2's warning was cleared |
| 23.9 s | Slam tilt, on player 1's second ball | 1 | 2,000 | | `slam_tilt`, `tilt` |
| 24.9 s | The ball drains | | | | `tilt_clear`, `ball_ended`, `game_ended`: player 2 never played ball 2 |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - bonus
  - tilt

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
  s_left_flipper:
    number:
  s_ramp:
    number:
    tags: playfield_active
  s_plumb_bob:
    number:
    tags: tilt_warning
  s_slam_tilt:
    number:
    tags: slam_tilt

coils:
  c_trough_eject:
    number:
  c_left_flipper:
    number:
    default_pulse_ms: 30
    default_hold_power: 0.25

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

flippers:
  left_flipper:
    main_coil: c_left_flipper
    activation_switch: s_left_flipper

virtual_platform_start_active_switches: s_trough1, s_trough2
```

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

variable_player:
  s_ramp_active:
    score: 1000
    ramps: 1
```

`modes/bonus/config/bonus.yaml`:

```yaml
#config_version=6

mode_settings:
  display_delay_ms: 1s
  bonus_entries:
    - entry: ramps
      text: RAMPS
      score: 5000
      player_score_entry: ramps
      reset_player_score_entry: true
```
