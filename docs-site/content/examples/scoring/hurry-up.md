---
title: "Hurry-up"
weight: 3
summary: "The scoop starts a value counting down from 200,000; the right ramp collects what's left before the 15 seconds run out."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** The scoop starts a hurry-up worth 200,000. The value drops by 5,000 every half second, and the right ramp
collects whatever is left. After 15 seconds, with the value down to 55,000, the hurry-up ends with nothing collected. The scoop
does nothing more while a hurry-up runs, and a hurry-up still running when the ball drains is lost.

**What it uses.** A short-lived [mode](/build/modes/), a [timer](/build/events/#something-happens-over-time) whose
ticks lower a player variable, and `event_player` to end the mode after the collect has scored.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the values and times below are from that run.
{{< /tip >}}

## How it works

### The mode and its clock

The `hurry_up` mode runs while the value counts down:

```yaml
mode:
  start_events: s_scoop_active
  stop_events: hurry_up_collected, timer_hurry_up_clock_complete
  priority: 300

timers:
  hurry_up_clock:
    start_value: 0
    end_value: 30
    tick_interval: 500ms
    start_running: true
```

The timer starts with the mode and counts from 0 to 30, one step every half second: 15 seconds in all. Each step
posts `timer_hurry_up_clock_tick` with the new count in `ticks`, except the last: reaching 30 posts
`timer_hurry_up_clock_complete` instead, which stops the mode (`Timer._post_tick_events`).

A scoop hit while the mode runs is ignored, because MPF doesn't start a mode that is already running. So the value
isn't reset to 200,000 by hitting the scoop again.

### The value

```yaml
variable_player:
  mode_hurry_up_started:
    hurry_up_value:
      int: 200000
      action: set
  timer_hurry_up_clock_tick{ticks>0}:
    hurry_up_value: -5000
```

`hurry_up_value` is a player variable, set to 200,000 each time the mode starts and lowered by 5,000 on each tick.
Two [details of a timer's ticks](/build/events/#something-happens-over-time) decide the numbers:

- MPF posts a tick with `ticks: 0` as soon as the timer starts. The `{ticks>0}` condition skips it, so the value starts
  at 200,000 whichever of the mode's handlers runs first.
- Step 30 posts only `_complete`, not a tick. So the value is lowered 29 times and the last value is 55,000, not
  50,000. That doesn't change what the player can collect, since it ends at that moment, but it matters if a display
  shows the value.

To show the value on a screen while it counts down, display the player variable `hurry_up_value`; with GMC, that's an
`MPFVariable` label (see [Showing scores and variables](/gmc/variables/)).

### Collecting it

```yaml
variable_player:
  s_right_ramp_active:
    score: current_player.hurry_up_value

event_player:
  s_right_ramp_active: hurry_up_collected
```

The right ramp scores the current value. `event_player` posts `hurry_up_collected` for the same hit, and that event
stops the mode. Events posted by `event_player` are handled after the event that caused them, so the score is added
before the mode stops. If the mode stopped on `s_right_ramp_active` itself, it would be a matter of which handler runs
first.

The `base` mode gives the scoop and right ramp their normal scores, so they score with or without a hurry-up.

## What happened in the test run

| Time | Step | Score | `hurry_up_value` | What happened |
|---|---|---|---|---|
| 0 s | Scoop | 500 | 200,000 | `mode_hurry_up_started` |
| 2.3 s | | 500 | 180,000 | 4 ticks so far |
| 2.4 s | Scoop again | 1,000 | 175,000 | Scores 500 in `base`; the value isn't reset |
| 4 s | Right ramp | 162,000 | 160,000 | Collected: 160,000 plus 1,000 from `base`; `hurry_up_collected`, `mode_hurry_up_stopped` |
| 5.1 s | Right ramp again | 163,000 | | Only the 1,000 from `base` |
| 5.2 s | Scoop | 163,500 | 200,000 | A new hurry-up, back at 200,000 |
| 19.9 s | | 163,500 | 55,000 | 14.7 s in: the last value |
| 20.4 s | | 163,500 | | 15 s in: `timer_hurry_up_clock_complete`, `mode_hurry_up_stopped` |
| 20.5 s | Right ramp | 164,500 | | Too late: only the 1,000 from `base` |
| 23.6 s | Scoop, then 3 s | 165,000 | 170,000 | Another hurry-up |
| 26.6 s | The ball drains | 165,000 | | `mode_hurry_up_stopped`: lost at the end of the ball |
| 26.7 s | Right ramp on ball 2 | 166,000 | | Only the 1,000 from `base` |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - hurry_up

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
  s_right_ramp:
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

In a real machine the scoop would be a [ball device](/build/ball-devices/#saucers-and-kickers); here it is a plain
switch to keep the example short.

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

variable_player:
  s_scoop_active:
    score: 500
  s_right_ramp_active:
    score: 1000
```

`modes/hurry_up/config/hurry_up.yaml`:

```yaml
#config_version=6

mode:
  start_events: s_scoop_active
  stop_events: hurry_up_collected, timer_hurry_up_clock_complete
  priority: 300

timers:
  hurry_up_clock:
    start_value: 0
    end_value: 30
    tick_interval: 500ms
    start_running: true

variable_player:
  mode_hurry_up_started:
    hurry_up_value:
      int: 200000
      action: set
  timer_hurry_up_clock_tick{ticks>0}:
    hurry_up_value: -5000
  s_right_ramp_active:
    score: current_player.hurry_up_value

event_player:
  s_right_ramp_active: hurry_up_collected
```
