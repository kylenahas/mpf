---
title: "Playfield multiplier"
weight: 5
summary: "A target lights 2x scoring for 30 seconds; hitting it again stacks to 3x and restarts the clock."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** Hitting the multiplier target lights 2x playfield scoring for 30 seconds: every shot scores double.
Hitting the target again while it runs raises it to 3x, the most it goes, and starts the 30 seconds over. When the
time runs out, or the ball ends, scoring goes back to 1x.

**What it uses.** A player variable that every score is multiplied by, a timed [mode](/build/modes/) that sets it,
and a [timer](/build/events/#something-happens-over-time) restarted by each hit.

MPF has no built-in playfield multiplier. It's a player variable, `pf_mult`, and each scoring entry multiplies by it.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the scores and times below are from that run.
{{< /tip >}}

## How it works

### Scoring with the multiplier

```yaml
player_vars:
  pf_mult:
    initial_value: 1
```

Every score in the machine uses it:

```yaml
variable_player:
  s_ramp_active:
    score: 1000 * current_player.pf_mult
  s_target_active:
    score: 100 * current_player.pf_mult
```

{{< note >}}
**Only scores that multiply by `pf_mult` are multiplied.** Any `score:` that's just a number, in any mode, scores 1x
whatever the multiplier is. When you add a mode, a bonus or a jackpot, decide whether it should be multiplied and
write it that way.
{{< /note >}}

### The multiplier mode

The multiplier target has the tag `mult`, so it posts `sw_mult` and then `sw_mult_active`. The mode starts on the first
and stacks on the second (a mode's `variable_player` can't use the mode's own start event; see
[Combos](/examples/scoring/combos/#why-two-events)):

```yaml
mode:
  start_events: sw_mult
  stop_events: timer_mult_time_complete
  priority: 200

timers:
  mult_time:
    start_value: 30
    end_value: 0
    direction: down
    start_running: true
    control_events:
      - event: sw_mult_active
        action: restart

variable_player:
  mode_multiplier_started:
    pf_mult:
      int: 2
      action: set
  sw_mult_active{current_player.pf_mult<3}:
    pf_mult: 1
```

- The first hit starts the mode, which sets `pf_mult` to 2.
- A hit while the mode runs adds 1, but only while it's below 3, and restarts the 30-second timer.
- The mode stops when the timer runs out, and at the end of the ball like any game mode.

In the test run, a third hit at 3x left it at 3x but still restarted the timer: the mode ran until 30 seconds after
that hit, 50 seconds after the first.

### Back to 1x

The `base` mode sets `pf_mult` back to 1 in two places:

```yaml
variable_player:
  mode_base_started:
    pf_mult:
      int: 1
      action: set
  mode_multiplier_stopped:
    pf_mult:
      int: 1
      action: set
```

`mode_multiplier_stopped` covers the time running out during the ball. `mode_base_started` covers the end of a ball:
the multiplier mode does stop then, but so does `base`, and in the test run `base` had stopped first, so its
`mode_multiplier_stopped` entry never ran.

{{< note >}}
**A reset only on `mode_multiplier_stopped` isn't enough.** In a first version without the `mode_base_started` entry,
a ball that drained during 2x left `pf_mult` at 2, and the first ramp on the next ball scored 2,000. The machine config
isn't an option for the reset either: a `variable_player` there can't change player variables, and MPF stops at startup
with `CFE-variable_player-1` ("Section not valid outside of game modes").
{{< /note >}}

## What happened in the test run

| Time | Step | Score | `pf_mult` | What happened |
|---|---|---|---|---|
| 0 s | Ramp | 1,000 | 1 | |
| 0.1 s | Multiplier target | 1,000 | 2 | `mode_multiplier_started` |
| 0.3 s | Ramp, target | 3,200 | 2 | 2,000 + 200 |
| 20.4 s | Multiplier target | 3,200 | 3 | Stacked; the 30 s start over |
| 20.5 s | Ramp | 6,200 | 3 | 3,000 |
| 20.6 s | Multiplier target | 6,200 | 3 | Already 3x; the 30 s start over again |
| 49.7 s | Ramp | 9,200 | 3 | 29 s after the last target hit: still 3x |
| 51.2 s | | 9,200 | 1 | `mode_multiplier_stopped` |
| 51.3 s | Ramp | 10,200 | 1 | |
| 51.4 s | Multiplier target, then the ball drains | 10,200 | 1 | Ball 2 starts at 1x |
| | Ramp on ball 2 | 11,200 | 1 | |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - multiplier

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
  s_mult_target:
    number:
    tags: mult, playfield_active
  s_ramp:
    number:
    tags: playfield_active
  s_target:
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

player_vars:
  pf_mult:
    initial_value: 1

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
    score: 1000 * current_player.pf_mult
  s_target_active:
    score: 100 * current_player.pf_mult
  mode_base_started:
    pf_mult:
      int: 1
      action: set
  mode_multiplier_stopped:
    pf_mult:
      int: 1
      action: set
```

`modes/multiplier/config/multiplier.yaml`:

```yaml
#config_version=6

mode:
  start_events: sw_mult
  stop_events: timer_mult_time_complete
  priority: 200

timers:
  mult_time:
    start_value: 30
    end_value: 0
    direction: down
    start_running: true
    control_events:
      - event: sw_mult_active
        action: restart

variable_player:
  mode_multiplier_started:
    pf_mult:
      int: 2
      action: set
  sw_mult_active{current_player.pf_mult<3}:
    pf_mult: 1
```
