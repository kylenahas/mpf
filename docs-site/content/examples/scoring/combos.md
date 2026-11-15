---
title: "Combos"
weight: 2
summary: "Major shots made within 4 seconds of each other are combos, and each combo in a chain is worth more than the last."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** The left ramp, right ramp and orbit are the major shots, worth 1,000 each. Making a major shot within 4
seconds of the previous one is a combo: the first combo in a chain scores 10,000, the second 20,000, the third 30,000,
and so on. Every major shot starts the 4 seconds over. When 4 seconds pass without one, the chain ends and the next
combo is worth 10,000 again. Other switches don't affect the chain.

**What it uses.** [Switch tags](/build/switches-and-coils/#events-a-switch-posts) to treat three switches as one,
a short-lived [mode](/build/modes/) that runs while a combo is possible, a [timer](/build/events/#something-happens-over-time)
for the 4 seconds, and a player variable for the length of the chain.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the scores and times below are from that run.
{{< /tip >}}

## How it works

### One event for all major shots

The three switches have the tag `major_shot`:

```yaml
switches:
  s_left_ramp:
    number:
    tags: major_shot, playfield_active
  s_right_ramp:
    number:
    tags: major_shot, playfield_active
  s_orbit:
    number:
    tags: major_shot, playfield_active
```

Each of the three switches posts `sw_major_shot` and then `sw_major_shot_active` when it's hit (see
[events a switch posts](/build/switches-and-coils/#events-a-switch-posts)). The rest of the example only uses those
two events, so to make another shot a major shot, give its switch the tag. Why it needs both is explained
[below](#why-two-events).

### A mode for the combo window

A `combo` mode starts with a major shot and stops when its timer runs out:

```yaml
mode:
  start_events: sw_major_shot
  stop_events: timer_combo_window_complete
  priority: 200

timers:
  combo_window:
    start_value: 4
    end_value: 0
    direction: down
    start_running: true
    control_events:
      - event: sw_major_shot_active
        action: restart
```

The timer counts down from 4 once a second, and each major shot while the mode runs restarts it at 4. When it reaches
0, it posts `timer_combo_window_complete` and the mode stops. A major shot while the mode is already running doesn't
start it again: MPF ignores a start event for a running mode, so `combo_count` isn't reset.

### Scoring the chain

```yaml
variable_player:
  mode_combo_started:
    combo_count:
      int: 0
      action: set
  sw_major_shot_active:
    combo_count: 1
    score: current_player.combo_count * 10000
```

Each time the window opens, `combo_count` is set back to 0. Each major shot while the mode runs adds 1 and scores
10,000 times the new count. The lines run in the order they're written
([variable_player](/build/shots-and-scoring/#scoring-with-variable_player)), so `score` sees the count after the
increase.

In the test run, the major shot that started the mode didn't count as a combo: its `sw_major_shot_active` had already
been handled when the mode's `variable_player` was set up. The first combo is the second shot.

### Why two events

The mode starts on `sw_major_shot` but scores on `sw_major_shot_active`. Using `sw_major_shot` for both isn't allowed:
MPF refuses a mode whose `variable_player` uses one of the mode's own start events (see
[errors that only appear later](/build/debugging/#errors-that-only-appear-later)). In a first version that did, the
first major shot stopped MPF with:

```text
combo mode's variable_player: section contains a "sw_major_shot:" event which is also in the start_events: for the combo mode. Change the variable_player: sw_major_shot: event name to "mode_combo_started:"
```

The suggested `mode_combo_started` is for something that should happen once when the mode starts, like setting
`combo_count` to 0 above. For something that should happen on every later hit, use a second event posted by the same
switch, such as the tag's `_active` event or the switch's own `s_left_ramp_active`.

The `base` mode scores 1,000 for every major shot, combo or not:

```yaml
variable_player:
  sw_major_shot:
    score: 1000
```

## What happened in the test run

| After the previous step | Shot | Score | `combo_count` | What happened |
|---|---|---|---|---|
| | Left ramp | 1,000 | 0 | `mode_combo_started`: the window opens |
| 2 s | Right ramp | 12,000 | 1 | First combo: 10,000 |
| 3 s | Orbit | 33,000 | 2 | Second combo: 20,000. Within 4 s of the right ramp, though 5 s after the left ramp. |
| 1 s | Target | 33,100 | 2 | Not a major shot: 100, and the window isn't restarted |
| 2 s | Left ramp | 64,100 | 3 | Third combo: 30,000 |
| 4 s | | 64,100 | 3 | 4 s without a major shot: `timer_combo_window_complete`, `mode_combo_stopped` |
| 1 s | Right ramp | 65,100 | 0 | The window opens again |
| 1 s | Right ramp | 76,100 | 1 | The same shot twice is a combo too: 10,000 |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - combo

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
  s_left_ramp:
    number:
    tags: major_shot, playfield_active
  s_right_ramp:
    number:
    tags: major_shot, playfield_active
  s_orbit:
    number:
    tags: major_shot, playfield_active
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
  sw_major_shot:
    score: 1000
  s_target_active:
    score: 100
```

`modes/combo/config/combo.yaml`:

```yaml
#config_version=6

mode:
  start_events: sw_major_shot
  stop_events: timer_combo_window_complete
  priority: 200

timers:
  combo_window:
    start_value: 4
    end_value: 0
    direction: down
    start_running: true
    control_events:
      - event: sw_major_shot_active
        action: restart

variable_player:
  mode_combo_started:
    combo_count:
      int: 0
      action: set
  sw_major_shot_active:
    combo_count: 1
    score: current_player.combo_count * 10000
```
