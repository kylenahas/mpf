---
title: "Drop target bank and extra ball"
weight: 2
summary: "A bank of three drop targets worth more each time it's cleared; the third clear lights an extra ball at the scoop."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** A bank of three drop targets. Each target scores 500. Knocking down the whole bank scores the bank
value, 5,000 the first time and 5,000 more each time after, and the bank pops back up a second later. The third time a
player clears the bank lights the extra ball at the scoop, and hitting the scoop collects it: when the ball drains, the
same player shoots again. Clears count across balls, and a player can earn one extra ball per game.

**What it uses.** [Drop targets and a drop target bank](/build/events/#a-drop-target-bank-is-complete), a player
variable for the growing value, a [counter](/build/events/#something-was-hit-n-times) that keeps its count across balls,
and an [extra ball](/build/ball-saves-and-extra-balls/#extra-balls).

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the scores and events below are from that run.
{{< /tip >}}

## How it works

### The bank

Each drop target is a device with its own switch, and the bank groups them and owns the reset coil. Both go in the
machine config:

```yaml
drop_targets:
  dt_left:
    switch: s_dt_left
  dt_center:
    switch: s_dt_center
  dt_right:
    switch: s_dt_right

drop_target_banks:
  main_bank:
    drop_targets: dt_left, dt_center, dt_right
    reset_coils: c_dt_reset
    reset_on_complete: 1s
```

When the last target goes down, the bank posts `drop_target_bank_main_bank_down`. `reset_on_complete: 1s` fires the
reset coil a second later, and when the targets are up again the bank posts `drop_target_bank_main_bank_up`. The bank
also resets at the start of every ball (`reset_events` defaults to `machine_reset_phase_3, ball_starting`), so a
half-cleared bank doesn't carry over to the next ball.

### A value that grows

The bank value is a player variable, so each player has their own:

```yaml
player_vars:
  bank_value:
    initial_value: 5000
```

```yaml
variable_player:
  sw_drop_target:
    score: 500
  drop_target_bank_main_bank_down:
    score: current_player.bank_value
    bank_value: 5000
```

`sw_drop_target` is posted when any switch tagged `drop_target` is hit, so one entry scores all three targets.

The clear both scores the value and raises it. The lines run in the order they're written, so `score` uses the value
from before the increase: in the test run, the first clear scored 5,000 and the next one 10,000.

{{< note >}}
**Don't raise the value on `drop_target_bank_main_bank_up`.** It looks like a tidy place for it, once the bank has
reset. But the bank also posts `_up` when it resets at the start of a ball with a target still down. In a first version
that did this, a ball that drained with one target down raised the value from 15,000 to 20,000 without a clear.
{{< /note >}}

The drop targets' switches have the `drop_target` tag but not `playfield_active`: like a kickback, a drop target
already tells the playfield the ball is there, and MPF stops at startup with `CFE-drop_target-1` if its switch has the
tag.

### Lighting and collecting the extra ball

A counter counts clears and lights the extra ball on the third:

```yaml
counters:
  bank_clears:
    count_events: drop_target_bank_main_bank_down
    count_complete_value: 3
    events_when_complete: light_bank_extra_ball
    persist_state: true

extra_balls:
  bank_eb:
    group: main
    light_events: light_bank_extra_ball
```

The counter is in the `base` mode, which stops at the end of every ball. `persist_state: true` stores its count in the
player, so two clears on one ball and one on the next still light the extra ball. When it completes, the counter resets
and disables itself (the defaults), and with `persist_state` it stays disabled for the rest of that player's game.

The group in the machine config collects it at the scoop and holds the limit:

```yaml
extra_ball_groups:
  main:
    award_lit_events: s_scoop_active
    max_per_game: 1
```

## What happened in the test run

| Step | Score | Ball | Bank value | Events |
|---|---|---|---|---|
| Left and center targets | 1,000 | 1 | 5,000 | `drop_target_bank_main_bank_mixed` after each |
| Right target: the bank is clear | 6,500 | 1 | 10,000 | `drop_target_bank_main_bank_down` |
| A second later | 6,500 | 1 | 10,000 | The reset coil fired; `drop_target_bank_main_bank_up` |
| Second clear | 18,000 | 1 | 15,000 | |
| Left target, then the ball drains | 18,500 | 2 | 15,000 | The bank reset when ball 2 started |
| Scoop, nothing lit | 18,500 | 2 | 15,000 | Nothing |
| Third clear, on ball 2 | 35,000 | 2 | 20,000 | `light_bank_extra_ball`, `extra_ball_group_main_lit_awarded`, `extra_ball_group_main_lit` |
| The ball drains without collecting it | 35,000 | 3 | 20,000 | `extra_ball_group_main_lit` again when ball 3 started: a lit extra ball is kept |
| Scoop | 35,000 | 3 | 20,000 | `extra_ball_awarded`; `extra_balls` is 1 |
| The ball drains | 35,000 | 3 | 20,000 | `ball_started` with `ball: 3` and `is_extra_ball: True` |
| Fourth clear | 56,500 | 3 | 25,000 | Nothing lit: the counter stays disabled |

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
  s_dt_left:
    number:
    tags: drop_target
  s_dt_center:
    number:
    tags: drop_target
  s_dt_right:
    number:
    tags: drop_target
  s_scoop:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:
  c_dt_reset:
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

drop_targets:
  dt_left:
    switch: s_dt_left
  dt_center:
    switch: s_dt_center
  dt_right:
    switch: s_dt_right

drop_target_banks:
  main_bank:
    drop_targets: dt_left, dt_center, dt_right
    reset_coils: c_dt_reset
    reset_on_complete: 1s

extra_ball_groups:
  main:
    award_lit_events: s_scoop_active
    max_per_game: 1

player_vars:
  bank_value:
    initial_value: 5000

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

counters:
  bank_clears:
    count_events: drop_target_bank_main_bank_down
    count_complete_value: 3
    events_when_complete: light_bank_extra_ball
    persist_state: true

extra_balls:
  bank_eb:
    group: main
    light_events: light_bank_extra_ball

variable_player:
  sw_drop_target:
    score: 500
  drop_target_bank_main_bank_down:
    score: current_player.bank_value
    bank_value: 5000
```
