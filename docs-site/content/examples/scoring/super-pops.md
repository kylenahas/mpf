---
title: "Pop bumpers and super pops"
weight: 4
summary: "Pop bumpers score a value that rises every 25 hits; every 100 hits starts 20 seconds of super pops at double value."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** Three pop bumpers score the pop value, 100 to start. Every 25 pop hits raise it by 100. Every 100 pop
hits start **super pops**: for 20 seconds, each pop scores double. The pop value and the count toward the next level
belong to the player and carry over from ball to ball.

**What it uses.** [Pop bumpers](/build/flippers-and-autofire/#slingshots-and-pop-bumpers) as autofire coils, a switch
tag, two [counters](/build/events/#something-was-hit-n-times) that keep their count across balls, and a timed
[mode](/build/modes/).

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the scores below are from that run.
{{< /tip >}}

## How it works

### The bumpers

Each pop bumper is an autofire coil: its switch fires its coil directly, without waiting for MPF. All three switches
have the tag `pop`, so the rules below use `sw_pop` for any of them:

```yaml
switches:
  s_pop_left:
    number:
    tags: pop
  s_pop_right:
    number:
    tags: pop
  s_pop_bottom:
    number:
    tags: pop

autofire_coils:
  pop_left:
    coil: c_pop_left
    switch: s_pop_left
  pop_right:
    coil: c_pop_right
    switch: s_pop_right
  pop_bottom:
    coil: c_pop_bottom
    switch: s_pop_bottom
```

The switches don't have the `playfield_active` tag (see
[switches that report the ball themselves](/build/flippers-and-autofire/#switches-that-report-the-ball-themselves)).

### The pop value and its levels

```yaml
player_vars:
  pop_value:
    initial_value: 100
```

```yaml
counters:
  pop_level:
    count_events: sw_pop
    count_complete_value: 25
    events_when_complete: pop_level_up
    disable_on_complete: false
    persist_state: true

variable_player:
  sw_pop:
    score: current_player.pop_value
  pop_level_up:
    pop_value: 100
```

Each pop scores the current value. The `pop_level` counter completes on every 25th pop: it resets itself
(`reset_on_complete` is `true` by default), and `disable_on_complete: false` keeps it counting for the next 25.
`persist_state: true` keeps its count in the player ([counters](/build/events/#something-was-hit-n-times)), so 20 pops
on one ball and 5 on the next still make a level.

The pop that completes a level still scores the old value: the `sw_pop` scoring is handled first, and
`pop_level_up` is an event the counter posts afterwards. In the test run, the 25th pop scored 100 and the 26th 200.

### Super pops

A second counter starts super pops every 100 pops:

```yaml
counters:
  super_pops_count:
    count_events: sw_pop
    count_complete_value: 100
    events_when_complete: start_super_pops
    disable_on_complete: false
    persist_state: true
```

The `super_pops` mode runs for 20 seconds and scores each pop a second time:

```yaml
mode:
  start_events: start_super_pops
  stop_events: timer_super_pops_time_complete
  priority: 200

timers:
  super_pops_time:
    start_value: 20
    end_value: 0
    direction: down
    start_running: true

variable_player:
  sw_pop:
    score: current_player.pop_value
```

Both the `base` entry and this one score `sw_pop`, so during super pops a pop scores the value twice. The mode stops
at the end of the ball like any game mode, so super pops still running at a drain are lost.

## What happened in the test run

| Step | Ball | Score | Pop value | Level count | Super pops count | What happened |
|---|---|---|---|---|---|---|
| 24 pops | 1 | 2,400 | 100 | 24 | 24 | |
| 25th pop | 1 | 2,500 | 200 | 0 | 25 | `pop_level_up`; this pop scored 100 |
| 26th pop | 1 | 2,700 | 200 | 1 | 26 | |
| 40 pops, then the ball drains | 2 | 5,500 | 200 | 15 | 40 | Both counts carried over to ball 2 |
| 10 more pops (50) | 2 | 7,500 | 300 | 0 | 50 | `pop_level_up` |
| 99 pops | 2 | 24,600 | 400 | 24 | 99 | |
| 100th pop | 2 | 25,000 | 500 | 0 | 0 | `pop_level_up`, `start_super_pops`, `mode_super_pops_started`; this pop scored 400 |
| 101st pop | 2 | 26,000 | 500 | 1 | 1 | Super pops: 2 × 500 |
| 20 s after super pops started | 2 | 26,000 | 500 | 1 | 1 | `mode_super_pops_stopped` |
| Pop | 2 | 26,500 | 500 | 2 | 2 | Back to 500 |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - super_pops

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
  s_pop_left:
    number:
    tags: pop
  s_pop_right:
    number:
    tags: pop
  s_pop_bottom:
    number:
    tags: pop

coils:
  c_trough_eject:
    number:
  c_pop_left:
    number:
    default_pulse_ms: 20
  c_pop_right:
    number:
    default_pulse_ms: 20
  c_pop_bottom:
    number:
    default_pulse_ms: 20

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

autofire_coils:
  pop_left:
    coil: c_pop_left
    switch: s_pop_left
  pop_right:
    coil: c_pop_right
    switch: s_pop_right
  pop_bottom:
    coil: c_pop_bottom
    switch: s_pop_bottom

player_vars:
  pop_value:
    initial_value: 100

virtual_platform_start_active_switches: s_trough1, s_trough2
```

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

counters:
  pop_level:
    count_events: sw_pop
    count_complete_value: 25
    events_when_complete: pop_level_up
    disable_on_complete: false
    persist_state: true
  super_pops_count:
    count_events: sw_pop
    count_complete_value: 100
    events_when_complete: start_super_pops
    disable_on_complete: false
    persist_state: true

variable_player:
  sw_pop:
    score: current_player.pop_value
  pop_level_up:
    pop_value: 100
```

`modes/super_pops/config/super_pops.yaml`:

```yaml
#config_version=6

mode:
  start_events: start_super_pops
  stop_events: timer_super_pops_time_complete
  priority: 200

timers:
  super_pops_time:
    start_value: 20
    end_value: 0
    direction: down
    start_running: true

variable_player:
  sw_pop:
    score: current_player.pop_value
```
