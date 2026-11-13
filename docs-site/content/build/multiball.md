---
title: "Multiball and ball locks"
weight: 9
summary: "Locking balls with multiball_locks, starting a multiball, its ball save, how it ends, and resetting the lock for the next round."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

A typical multiball: the player locks two balls in a VUK, and locking the second starts a three-ball multiball. MPF
splits this into two devices:

- **`multiball_locks:`** counts balls the player locks, keeps them (or not) in a ball device, and serves a new ball
  each time.
- **`multiballs:`** puts balls into play, from locks first and then the trough, saves balls that drain early, and
  ends when only one ball is left.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart virtual
platform. Ball counts and events below are from that run, and `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## The lock

The lock is a normal ball device on the playfield, here a VUK with room for two balls:

```yaml
ball_devices:
  bd_lock:
    ball_switches: s_lock1, s_lock2
    eject_coil: c_lock_eject
    eject_targets: playfield
    eject_timeouts: 3s
```

The `multiball_locks:` device (mode configs only) turns it into a lock:

```yaml
multiball_locks:
  vuk_lock:
    lock_devices: bd_lock
    balls_to_lock: 2
    reset_count_for_current_player_events: multiball_main_mb_started
```

When a ball enters `bd_lock` while the lock is enabled:

1. The lock counts it for the current player and posts `multiball_lock_vuk_lock_locked_ball` with
   `total_balls_locked`.
2. It keeps the ball in the device, if that makes sense (see below), and asks the playfield for a replacement ball,
   so the player keeps playing.
3. When the count reaches `balls_to_lock`, it posts `multiball_lock_vuk_lock_full`.

In the test run, the first lock left the trough with one ball, one ball in the VUK and one on the playfield, and
posted `locked_ball` with `total_balls_locked: 1`. The second lock posted `full`.

A lock with no `enable_events` is enabled whenever its mode runs. Without a running lock (in attract mode, or a mode
that does not have it), a ball entering `bd_lock` is simply ejected again, like any [saucer](/build/ball-devices/#saucers-and-kickers).

### Counting per player

`locked_ball_counting_strategy` decides what "locked" means when several players share the same physical device
(`MultiballLock` in `mpf/devices/multiball_lock.py`):

| Strategy | Meaning |
|---|---|
| `virtual_only` (default) | Each player has their own count (a player variable). A ball is kept physically only while some player could still use it. |
| `physical_only` | The count is the number of balls physically in the device, the same for every player. |
| `min_virtual_physical` | The smaller of the player's own count and the balls physically in the device. |
| `no_virtual` | One count kept by the device itself, not per player. |

(`MultiballLock.locked_balls` and `_lock_ball`.) A `multiballs:` device with `ball_count_type: total` needs a
`ball_count` of at least 2 (error 1).

### Reset the count when the multiball starts

{{< warn >}}
**A full lock stays full until you reset it.** The count belongs to the player and survives the multiball and the end
of the ball. In the test run without `reset_count_for_current_player_events`, the lock showed 2 locked balls on ball
2, and a ball entering the VUK was just ejected again: no `locked_ball`, no score. With the setting above, the count
went back to 0 when the multiball started, and on ball 2 the first ball into the VUK was locked again.
{{< /warn >}}

`reset_all_counts_events` resets every player's count instead.

## The multiball

```yaml
multiballs:
  main_mb:
    ball_count: 3
    ball_locks: bd_lock
    start_events: multiball_lock_vuk_lock_full
    shoot_again: 10s
```

| Setting | Default | What it does |
|---|---|---|
| `ball_count` | required | Balls in play during the multiball. |
| `ball_count_type` | `total` | `total`: bring play up to `ball_count`. `add`: add `ball_count` balls to what is in play. |
| `ball_locks` | none | Devices to take balls from first; the rest come from the trough. |
| `start_events` | none | When to start. |
| `shoot_again` | `10s` | A ball save for the multiball: a drain within this time is replaced. |
| `add_a_ball_events` | none | Add one more ball while running (with its own `add_a_ball_shoot_again`). |

In the test run, `multiball_lock_vuk_lock_full` started the multiball: `multiball_main_mb_started` with `balls: 3`,
the VUK released both balls, and the trough supplied the rest. Three balls were in play.

### The multiball's ball save

During `shoot_again`, a drain does not reduce the balls in play. The multiball handles `ball_drain` (a
[relay event](/architecture/how-events-work/#relay-passing-a-changing-value-along)), posts
`multiball_main_mb_shoot_again` with the number of balls saved, and adds them back. In the test run, a drain 5
seconds into the multiball was replaced, and the playfield was back to three balls. At the end of the window MPF posts
`multiball_main_mb_shoot_again_ended`.

### How it ends

After the save window, each drain lowers the balls in play. The multiball posts `multiball_main_mb_ball_lost` for each
one, and `multiball_main_mb_ended` when only one ball is left. The ball itself continues. In the test run, the first
drain left two balls (no `ended`), the second left one and posted `multiball_main_mb_ended`, and the third ended the
ball as usual.

{{< warn >}}
**The event is `multiball_<name>_ball_lost`, not `multiball_<name>_lost_ball`.** MPF's own source documents it as
`multiball_(name)_lost_ball`, so that name appears in older documentation and in the
[events reference](/reference/events/#multiball-name-lost-ball), but MPF 0.82.0.dev0 posts `multiball_main_mb_ball_lost`.
In the test run, a handler for `multiball_main_mb_lost_ball` never ran.
{{< /warn >}}

Use `grace_period` and `hurry_up_time` for the last moments of the save window, and `restart_grace_period` to allow
a restart shot after the multiball ends.

## Scoring during the multiball

A condition on the multiball's state limits a score to the multiball:

```yaml
variable_player:
  multiball_lock_vuk_lock_locked_ball:
    score: 1000
  s_target_active{device.multiballs.main_mb.balls_live_target>0}:
    score: 100
```

`balls_live_target` is the number of balls the multiball is keeping in play, and 0 when it is not running. In the
test run, the target scored nothing before the multiball and 100 during it; each lock scored 1000.

## Holding a ball without a multiball

To hold a ball for a moment, for example while a show plays in a scoop, use `ball_holds:` instead. It holds balls in
its `hold_devices` while enabled and releases them on `release_one_events` or `release_all_events`. See the
[`ball_holds` reference](/reference/config/devices/ball-holds/).

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
  s_lock1:
    number:
  s_lock2:
    number:
  s_target:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:
  c_lock_eject:
    number:

ball_devices:
  bd_trough:
    ball_switches: s_trough1, s_trough2, s_trough3
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 3s
    tags: trough, drain, home
  bd_lock:
    ball_switches: s_lock1, s_lock2
    eject_coil: c_lock_eject
    eject_targets: playfield
    eject_timeouts: 3s

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

virtual_platform_start_active_switches: s_trough1, s_trough2, s_trough3
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
    balls_to_lock: 2
    reset_count_for_current_player_events: multiball_main_mb_started

multiballs:
  main_mb:
    ball_count: 3
    ball_locks: bd_lock
    start_events: multiball_lock_vuk_lock_full
    shoot_again: 10s

variable_player:
  multiball_lock_vuk_lock_locked_ball:
    score: 1000
  s_target_active{device.multiballs.main_mb.balls_live_target>0}:
    score: 100
```

What the test run showed:

| Step | Trough | VUK | Playfield | In play | Locked | Score |
|---|---|---|---|---|---|---|
| Ball 1 on the playfield | 2 | 0 | 1 | 1 | 0 | 0 |
| First ball locked (new ball served) | 1 | 1 | 1 | 1 | 1 | 1000 |
| Second ball locked: multiball starts | 0 | 0 | 2 → 3 | 3 | 0 | 2000 |
| Target during multiball | | | | 3 | | 2100 |
| Drain within `shoot_again` (replaced) | 0 | 0 | 3 | 3 | | |
| Drain after the window | 1 | 0 | 2 | 2 | | |
| Drain: one ball left, multiball ended | 2 | 0 | 1 | 1 | | |
| Last drain: ball 2 starts | | | | 1 | 0 | 2100 |
| Ball into the VUK on ball 2 | 1 | 1 | 1 | 1 | 1 | 3100 |
