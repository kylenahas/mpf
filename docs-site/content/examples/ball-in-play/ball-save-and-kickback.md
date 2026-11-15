---
title: "Ball save, kickback and outlanes"
weight: 1
summary: "A ball save at the start of every ball, three targets that light a kickback in the left outlane, and outlanes that still score."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** Every ball starts with a 10-second ball save. Three standup targets light as they are hit; lighting all
three lights the kickback in the left outlane and scores 25,000. A lit kickback fires the ball back once and then goes
out until the targets are completed again. The right outlane has no kickback, but while the ball save is on, a ball
entering it is saved at once instead of at the drain. Both outlanes score 5,000.

**What it uses.** A [ball save](/build/ball-saves-and-extra-balls/#ball-saves) with an early save, a
[kickback](/build/flippers-and-autofire/#kickbacks), and [shots and a shot group](/build/shots-and-scoring/#shot-groups)
for the targets.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the events and scores below are from that run.
{{< /tip >}}

## How it works

### The ball save

The `base` mode runs for every ball, so its ball save is switched on at the start of each one:

```yaml
ball_saves:
  start_save:
    active_time: 10s
    hurry_up_time: 3s
    grace_period: 2s
    enable_events: mode_base_started
    timer_start_events: balldevice_bd_trough_ball_eject_success
    early_ball_save_events: s_right_outlane_active
```

The 10 seconds start once the ball has reached the playfield (`timer_start_events`), not while it is still being
served. `hurry_up_time` posts `ball_save_start_save_hurry_up` 3 seconds before the end, for a faster blinking light,
and `grace_period` keeps saving for 2 seconds after the time is up, for a ball that was already on its way down.
`balls_to_save` is 1 by default, so the save is used up after one save.

`early_ball_save_events` saves the ball as soon as it enters the right outlane: the new ball is served while the old
one is still rolling to the drain. The left outlane isn't in the list, because that's where the kickback is.

{{< note >}}
**Don't early-save an outlane that has a lit kickback.** In a first version, both outlanes were in
`early_ball_save_events`. With the kickback lit and the ball save on, a ball in the left outlane was fired back by the
kickback **and** saved early, so there were two balls on the playfield in a one-ball game. Without the early save, the
left outlane is still covered: a ball the kickback can't save goes on to the drain, where the ball save catches it.
{{< /note >}}

### Lighting the kickback

The three targets are shots in a group. Each starts `unlit` and becomes `lit` when hit (the built-in `default`
profile); when all three are lit, the group posts `kickback_targets_lit_complete`:

```yaml
shots:
  kick_target_1:
    switch: s_kick_target_1
  kick_target_2:
    switch: s_kick_target_2
  kick_target_3:
    switch: s_kick_target_3

shot_groups:
  kickback_targets:
    shots: kick_target_1, kick_target_2, kick_target_3
    reset_events: kickback_targets_lit_complete
```

The kickback itself is in the machine config, since it is a device wired to a switch and a coil:

```yaml
kickbacks:
  left_kickback:
    coil: c_kickback
    switch: s_left_outlane
    enable_events: kickback_targets_lit_complete
    disable_events: kickback_left_kickback_fired, ball_will_end, service_mode_entered
```

When it's enabled, the kickback is a hardware rule: the outlane switch fires the coil directly, without waiting for
MPF. Each time it fires, it posts `kickback_left_kickback_fired`, and `disable_events` turns it off on that event, so it
fires once. `ball_will_end` and `service_mode_entered` are the defaults, repeated because `disable_events` replaces
them (see [kickbacks](/build/flippers-and-autofire/#kickbacks)). A lit kickback is therefore lost when the ball ends.

### Scoring

```yaml
variable_player:
  s_kick_target_1_active:
    score: 1000
  s_kick_target_2_active:
    score: 1000
  s_kick_target_3_active:
    score: 1000
  kickback_targets_lit_complete:
    score: 25000
  s_left_outlane_active:
    score: 5000
  s_right_outlane_active:
    score: 5000
```

## What happened in the test run

| Step | Score | Ball | Kickback | What happened |
|---|---|---|---|---|
| Game starts, ball reaches the playfield | 0 | 1 | off | `ball_save_start_save_timer_start` |
| Targets 1, 1, 2 | 3,000 | 1 | off | Targets 1 and 2 lit. A lit target still scores when hit again. |
| Target 3 | 29,000 | 1 | **lit** | `kickback_targets_lit_complete`; the three targets went back to unlit |
| Left outlane | 34,000 | 1 | off | `kickback_left_kickback_fired`; the ball stays in play |
| Left outlane again | 39,000 | 1 | off | Nothing fires; the ball goes on to the drain |
| Drain, during the save | 39,000 | 1 | off | `saving_ball` with `early_save: False`; the save is used up |
| Drain, 20 seconds later | 39,000 | 2 | off | Ball 2 starts with a new save |
| Right outlane | 44,000 | 2 | off | `saving_ball` with `early_save: True`; a new ball is served at once, so 3 seconds later there were 2 balls on the playfield |
| The outlane ball drains | 44,000 | 2 | off | The ball doesn't end |
| Targets 1, 2, 3 | 72,000 | 2 | **lit** | |
| Drain, save over | 72,000 | 3 | off | The lit kickback was lost when ball 2 ended |
| Left outlane | 77,000 | 3 | off | Nothing fires |

In the first version, with `s_left_outlane_active` also in `early_ball_save_events`, the left outlane with the kickback
lit posted both `kickback_left_kickback_fired` and `saving_ball`, and 3 seconds later there were 2 balls on the
playfield with 1 ball in play.

The left outlane switch has no `playfield_active` tag, because it belongs to the kickback (see
[switches that report the ball themselves](/build/flippers-and-autofire/#switches-that-report-the-ball-themselves)).

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
  s_kick_target_1:
    number:
    tags: playfield_active
  s_kick_target_2:
    number:
    tags: playfield_active
  s_kick_target_3:
    number:
    tags: playfield_active
  s_left_outlane:
    number:
  s_right_outlane:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:
  c_kickback:
    number:
    default_pulse_ms: 30

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

kickbacks:
  left_kickback:
    coil: c_kickback
    switch: s_left_outlane
    enable_events: kickback_targets_lit_complete
    disable_events: kickback_left_kickback_fired, ball_will_end, service_mode_entered

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
    hurry_up_time: 3s
    grace_period: 2s
    enable_events: mode_base_started
    timer_start_events: balldevice_bd_trough_ball_eject_success
    early_ball_save_events: s_right_outlane_active

shots:
  kick_target_1:
    switch: s_kick_target_1
  kick_target_2:
    switch: s_kick_target_2
  kick_target_3:
    switch: s_kick_target_3

shot_groups:
  kickback_targets:
    shots: kick_target_1, kick_target_2, kick_target_3
    reset_events: kickback_targets_lit_complete

variable_player:
  s_kick_target_1_active:
    score: 1000
  s_kick_target_2_active:
    score: 1000
  s_kick_target_3_active:
    score: 1000
  kickback_targets_lit_complete:
    score: 25000
  s_left_outlane_active:
    score: 5000
  s_right_outlane_active:
    score: 5000
```
