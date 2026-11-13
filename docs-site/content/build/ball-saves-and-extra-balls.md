---
title: "Ball saves and extra balls"
weight: 10
summary: "Ball saves (timer, hurry-up, grace period, early saves) and extra balls (lighting, collecting, limits, shoot again)."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

Two ways to give the player another chance. A **ball save** replaces a ball that drains soon after it was put into
play, so the ball does not end. An **extra ball** lets the player shoot the same ball number again after the ball
ends.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase`. All timings and events
below are from that run, and `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## Ball saves

```yaml
ball_saves:
  start_save:
    active_time: 10s
    hurry_up_time: 3s
    grace_period: 2s
    enable_events: ball_started
    timer_start_events: balldevice_bd_trough_ball_eject_success
    early_ball_save_events: s_left_outlane_active
```

| Setting | Default | What it does |
|---|---|---|
| `enable_events` | none | When the save is switched on. |
| `active_time` | `0` | How long the save lasts once its timer starts. `0` means no time limit: it stays on until disabled or used up. |
| `timer_start_events` | none | When the timer starts. Without it, the timer starts as soon as the save is enabled. |
| `hurry_up_time` | `0` | Posts `ball_save_<name>_hurry_up` this long before the time runs out, to start a "hurry" light show. |
| `grace_period` | `0` | Keeps saving for this long after the time runs out, while the light is already off. |
| `balls_to_save` | `1` | How many drains to save before switching off. `-1` is unlimited. |
| `only_last_ball` | `false` | Save only when one ball is in play (not during multiball). |
| `early_ball_save_events` | none | Save as soon as this event happens, before the ball reaches the drain (an outlane switch). |
| `auto_launch` | `true` | Launch the saved ball automatically instead of waiting for the player. |
| `disable_events` | `ball_will_end`, `service_mode_entered` | When to switch off. |

### The timeline

`timer_start_events: balldevice_bd_trough_ball_eject_success` starts the clock when the ball has left the trough
and reached the playfield, confirmed either by the first playfield switch or by the trough's eject timeout. Use the
eject success of whichever device feeds the playfield (the plunger lane, if you have one), so the clock does not run
while the ball sits in the shooter lane. In the test run, the first playfield switch was hit 2 seconds after the start:

| Time | Event |
|---|---|
| 0 s | `ball_started`, `ball_save_start_save_enabled` |
| 2 s (first playfield switch, eject confirmed) | `ball_save_start_save_timer_start` |
| 9 s (`active_time` − `hurry_up_time`) | `ball_save_start_save_hurry_up` |
| 12 s (`active_time` over) | `ball_save_start_save_grace_period` |
| 14 s (`grace_period` over) | `ball_save_start_save_disabled` |

{{< warn >}}
**Do not start the timer on `playfield_active`.** It looks like the obvious choice, but the playfield only posts
`playfield_active` when a switch is hit while it believes no ball is on it (`Playfield._playfield_switch_hit`). If the
eject is confirmed by the eject timeout first, no `playfield_active` follows, the timer never starts, and the save
lasts for the whole ball. In the test run with `timer_start_events: playfield_active` and the first switch hit 5
seconds after the start (after the 3 s eject timeout), the timer never started, and a drain 18 seconds into the ball
was still saved. With the eject success event, the timer started at 3.1 s and the save ended at 15.1 s.
{{< /warn >}}

### Saving a ball

A drain while the save is on posts `ball_save_<name>_saving_ball` with `balls` and `early_save`, and serves a new
ball. The drained ball does not count: the ball save handles `ball_drain` before the game does and lowers its `balls`
argument (see [relay events](/architecture/how-events-work/#relay-passing-a-changing-value-along)).

In the test run, a drain 2 seconds after the timer started posted `saving_ball` with `balls: 1`, the ball number stayed
at 2, and the save switched itself off (`balls_to_save: 1` used up). The next drain ended the ball.

### Early saves

With `early_ball_save_events`, the save acts when the ball enters an outlane, so the new ball is already on its way
when the old one reaches the trough. In the test run, hitting `s_left_outlane` posted `saving_ball` with
`early_save: True` and served a ball at once (two balls on the playfield, one in play). When the outlane ball then
drained, the ball did not end.

### Saves in modes

A ball save is valid in machine and mode configs. Starting a mode can switch one on: give it
`enable_events: mode_<name>_started`. [Multiballs](/build/multiball/#the-multiballs-ball-save) have their own
save, `shoot_again`.

## Extra balls

An extra ball is **lit** by one shot and **collected** by another; collecting adds one to the player variable
`extra_balls`. When the ball ends and `extra_balls` is above 0, the same player shoots the same ball number again
(`Game._award_extra_ball` in `mpf/modes/game/code/game.py`).

Two devices work together:

- **`extra_ball_groups:`** (machine config) holds the limits and the "collect" event, shared by all extra balls in the
  group.
- **`extra_balls:`** (mode config) are the individual ways to light or award one.

```yaml
extra_ball_groups:
  main:
    award_lit_events: s_eb_collect_active
    max_per_game: 1
```

```yaml
extra_balls:
  target_eb:
    group: main
    light_events: s_eb_target_active
```

In the test run:

1. Hitting `s_eb_target` posted `extra_ball_target_eb_lit`, `extra_ball_group_main_lit_awarded` and
   `extra_ball_group_main_lit`.
2. Hitting `s_eb_collect` posted `extra_ball_group_main_unlit`, `extra_ball_group_main_awarded` and
   `extra_ball_awarded`; `extra_balls` became 1.
3. When ball 3 drained, `ball_started` was posted again with `ball: 3` and `is_extra_ball: True`, and `extra_balls`
   went back to 0.

| Event | When | Use it for |
|---|---|---|
| `extra_ball_group_<name>_lit_awarded` | An extra ball was lit during play | The "extra ball is lit" show. Despite the name, nothing is collected yet. |
| `extra_ball_group_<name>_lit` | Lit during play, **and** again at the start of each turn while still lit | Turning the lit light on |
| `extra_ball_group_<name>_unlit` | No longer lit | Turning the light off |
| `extra_ball_awarded` | An extra ball was collected | The "extra ball!" show |
| `extra_ball_award_disabled` | An award was refused (a limit was reached) | Scoring points instead |

`award_events` on an `extra_balls:` entry (instead of `light_events`) awards directly, without lighting. Lit extra
balls are remembered for the next turn (`lit_memory: true` on the group): in a test run without the group limit, an
extra ball that was lit but not collected was lit again (`extra_ball_group_main_lit`) when the next ball started.

### Limits

{{< warn >}}
**Put the limit on the group.** An `extra_balls:` entry has `max_per_game: 1` by default, but in MPF 0.82.0.dev0
it only counts awards made through that entry's `award_events`. Lighting it and collecting it through the group does
not count, although the source says lighting does (`ExtraBall.light`). In the test run without a group limit, the
player lit and collected three extra balls in a row. With `max_per_game: 1` on the group, the second light was refused
(`extra_ball_award_disabled`, `extra_ball_target_eb_award_disabled` and `extra_ball_group_main_award_disabled`), the
second collect found nothing lit (`extra_ball_group_main_award_disabled`), and `extra_balls` stayed at 1.
{{< /warn >}}

The group also has `max_per_ball` and `max_lit`.

{{< note >}}
When a collect reaches the group's limit, MPF 0.82.0.dev0 also sets a player variable literally named
`extra_ball_group_{}_num_lit` (the group name is missing; `ExtraBallGroup.award` in
`mpf/devices/extra_ball_group.py`), which posts an event `player_extra_ball_group_{}_num_lit`. It is harmless, but it
shows up in the log.
{{< /note >}}

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base

machine:
  balls_installed: 3

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_trough2:
    number:
  s_trough3:
    number:
  s_target:
    number:
    tags: playfield_active
  s_left_outlane:
    number:
  s_eb_target:
    number:
  s_eb_collect:
    number:

coils:
  c_trough_eject:
    number:

ball_devices:
  bd_trough:
    ball_switches: s_trough1, s_trough2, s_trough3
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 3s
    tags: trough, drain, home

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

extra_ball_groups:
  main:
    award_lit_events: s_eb_collect_active
    max_per_game: 1

virtual_platform_start_active_switches: s_trough1, s_trough2, s_trough3
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
    enable_events: ball_started
    timer_start_events: balldevice_bd_trough_ball_eject_success
    early_ball_save_events: s_left_outlane_active

extra_balls:
  target_eb:
    group: main
    light_events: s_eb_target_active
```
