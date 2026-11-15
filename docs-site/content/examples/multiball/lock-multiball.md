---
title: "Lock-based multiball"
weight: 2
summary: "A target lights the lock, three locked balls start a three-ball multiball, a ramp adds a ball, and two players share one physical lock."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** The lock is a VUK that holds up to three balls. It starts unlit; hitting the lock target lights it, and
a ball entering the VUK while it is lit is locked, and the lock goes out again. Locking the third ball starts a
three-ball multiball with the three locked balls. During the multiball, the ramp adds a fourth ball once. When a
multiball takes the balls out of the VUK, every player's locks start over.

**What it uses.** A [multiball lock](/build/multiball/#the-lock) with enable and disable events, a
[multiball](/build/multiball/#the-multiball) with `add_a_ball_events`, a mode that runs for the length of the
multiball, and a lock count reset for all players.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart virtual platform; the ball counts and
events below are from that run.
{{< /tip >}}

## How it works

### Lighting the lock

```yaml
multiball_locks:
  vuk_lock:
    lock_devices: bd_lock
    balls_to_lock: 3
    balls_to_replace: 2
    enable_events: s_lock_target_active
    disable_events: multiball_lock_vuk_lock_locked_ball
    reset_all_counts_events: multiball_main_mb_started
```

The lock is only enabled after the lock target is hit, and `disable_events` turns it off again after each ball it
locks, so every lock has to be lit first. While it is off, a ball entering the VUK is kicked straight back out.

In the test run, a ball into the VUK before the target was hit was ejected at once (no lock, no score); after the
target it was locked, and another ball into the VUK, without hitting the target again, was ejected.

A lit lock is lost when the ball ends: the lock is a device in the `base` mode, which stops at the end of every ball,
and it starts disabled again with the next ball because it has `enable_events`.

`balls_to_replace: 2`, together with `eject_all_events: multiball_main_mb_started` on the VUK, makes the third lock
release all three locked balls instead of serving a ball from the trough. See
[Releasing all three balls](/build/multiball/#releasing-all-three-balls).

### Starting the multiball and adding a ball

```yaml
multiballs:
  main_mb:
    ball_count: 3
    ball_locks: bd_lock
    start_events: multiball_lock_vuk_lock_full
    shoot_again: 10s
    add_a_ball_events: add_a_ball
```

The third lock fills the lock and starts the multiball with the three balls in the VUK. `add_a_ball_events` adds one
more ball, from the trough, each time `add_a_ball` is posted while the multiball runs.

The add-a-ball shot lives in a `main_mb` mode that starts and stops with the multiball, so the ramp only adds a ball
during it, and a two-state profile makes it work once per multiball:

```yaml
mode:
  start_events: multiball_main_mb_started
  stop_events: multiball_main_mb_ended
  priority: 200

shot_profiles:
  once:
    states:
      - name: lit
      - name: collected

shots:
  add_a_ball_shot:
    switch: s_ramp
    profile: once
    reset_events: mode_main_mb_started

event_player:
  add_a_ball_shot_lit_hit: add_a_ball
```

### Two players, one VUK

Locked balls are counted per player (`locked_ball_counting_strategy: virtual_only`, the default), but the VUK is
shared. In the test run, player 1 locked a ball and drained, leaving that ball in the VUK. Then:

- **Player 2 lit the lock and shot a ball into the VUK.** It counted as player 2's first lock. The VUK now held two
  balls but only needed to keep one (each player had 1 locked), so instead of serving a new ball from the trough, the
  lock kicked a ball back out of the VUK to player 2.
- **Player 2 locked two more balls** and started the multiball with the three balls in the VUK, including the one
  player 1 had locked.
- **`reset_all_counts_events`** set every player's count back to 0 when the multiball started, so on player 1's next
  ball, player 1 had no locks, matching the empty VUK, and started over.

{{< warn >}}
**Reset every player's count, not only the current player's.** With `reset_count_for_current_player_events` instead,
player 1 came back with 1 lock while the VUK was empty. Two more locks then started player 1's multiball, and MPF
counted 3 balls in play while only 2 were on the playfield: the multiball took two balls from the VUK, which was all
it had, and `balls_to_replace: 2` meant no ball came from the trough for the third lock. If players should keep their
locks, use a [virtual lock](/build/multiball/#physical-and-virtual-locks) instead, which doesn't hold balls.
{{< /warn >}}

## What happened in the test run

| Step | Player | Score | Trough | VUK | Balls in play | Locked | What happened |
|---|---|---|---|---|---|---|---|
| Game starts (2 players) | 1 | 0 | 3 | 0 | 1 | 0 | |
| Ball into the VUK, lock not lit | 1 | 0 | 3 | 0 | 1 | 0 | Ejected straight back out |
| Lock target, ball into the VUK | 1 | 5,000 | 2 | 1 | 1 | 1 | `locked_ball` with `total_balls_locked: 1`; a new ball from the trough |
| Ball into the VUK again | 1 | 5,000 | 2 | 1 | 1 | 1 | Not lit: ejected |
| Lock target, then the ball drains | 2 | 0 | 2 | 1 | 1 | 0 | Player 1's ball stays in the VUK. The lit lock is lost: player 2's ball starts with it off. |
| Lock target, ball into the VUK | 2 | 5,000 | 2 | 1 | 1 | 1 | Locked; the VUK kicked a ball back out instead of the trough serving one |
| Lock target, ball into the VUK | 2 | 10,000 | 1 | 2 | 1 | 2 | Locked; a new ball from the trough |
| Lock target, ball into the VUK | 2 | 15,000 | 1 | 3 → 0 | 3 | 0 | `full`, `multiball_main_mb_started` with `balls: 3`; all three balls from the VUK, the trough kept its ball |
| Ramp | 2 | 16,000 | 0 | 0 | 4 | 0 | `add_a_ball`: a fourth ball |
| Ramp again | 2 | 17,000 | 0 | 0 | 4 | 0 | Only the ramp's 1,000 |
| Three drains, after the 10 s `shoot_again` | 2 | 17,000 | 3 | 0 | 1 | 0 | `multiball_main_mb_ball_lost` each time, and `multiball_main_mb_ended` on the third |
| The last ball drains | 1 | 5,000 | 3 | 0 | 1 | 0 | Ball 2: player 1's lock was reset by player 2's multiball |
| Lock target, ball into the VUK | 1 | 10,000 | 2 | 1 | 1 | 1 | Player 1 starts over |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - main_mb

machine:
  balls_installed: 4

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
  s_trough4:
    number:
  s_lock1:
    number:
  s_lock2:
    number:
  s_lock3:
    number:
  s_lock_target:
    number:
    tags: playfield_active
  s_ramp:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:
  c_lock_eject:
    number:

ball_devices:
  bd_trough:
    ball_switches: s_trough1, s_trough2, s_trough3, s_trough4
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 2s
    tags: trough, drain, home
  bd_lock:
    ball_switches: s_lock1, s_lock2, s_lock3
    eject_coil: c_lock_eject
    eject_targets: playfield
    eject_timeouts: 3s
    eject_all_events: multiball_main_mb_started

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

virtual_platform_start_active_switches: s_trough1, s_trough2, s_trough3, s_trough4
```

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

multiball_locks:
  vuk_lock:
    lock_devices: bd_lock
    balls_to_lock: 3
    balls_to_replace: 2
    enable_events: s_lock_target_active
    disable_events: multiball_lock_vuk_lock_locked_ball
    reset_all_counts_events: multiball_main_mb_started

multiballs:
  main_mb:
    ball_count: 3
    ball_locks: bd_lock
    start_events: multiball_lock_vuk_lock_full
    shoot_again: 10s
    add_a_ball_events: add_a_ball

variable_player:
  multiball_lock_vuk_lock_locked_ball:
    score: 5000
  s_ramp_active:
    score: 1000
```

`modes/main_mb/config/main_mb.yaml`:

```yaml
#config_version=6

mode:
  start_events: multiball_main_mb_started
  stop_events: multiball_main_mb_ended
  priority: 200

shot_profiles:
  once:
    states:
      - name: lit
      - name: collected

shots:
  add_a_ball_shot:
    switch: s_ramp
    profile: once
    reset_events: mode_main_mb_started

event_player:
  add_a_ball_shot_lit_hit: add_a_ball
```
