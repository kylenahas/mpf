---
title: "Multiball and ball locks"
weight: 9
summary: "Locking three balls with multiball_locks, physical and virtual locks, starting a multiball, its ball save, how it ends, and resetting the lock for the next round."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

A typical modern multiball: the player locks three balls, and locking the third starts a three-ball multiball with all
three coming out of the lock. MPF splits this into two devices:

- **`multiball_locks:`** counts balls the player locks, keeps them (or not) in a ball device, and serves a new ball
  each time.
- **`multiballs:`** puts balls into play, from locks first and then the trough, saves balls that drain early, and
  ends when only one ball is left.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart virtual
platform. Ball counts and events below are from that run, and `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## The lock

The lock is a normal ball device on the playfield, here a VUK with room for three balls. The machine has four balls:
three to lock and one more, so the player always has a ball while the first two are locked.

```yaml
ball_devices:
  bd_lock:
    ball_switches: s_lock1, s_lock2, s_lock3
    eject_coil: c_lock_eject
    eject_targets: playfield
    eject_timeouts: 3s
    eject_all_events: multiball_main_mb_started
```

The `multiball_locks:` device (mode configs only) turns it into a lock:

```yaml
multiball_locks:
  vuk_lock:
    lock_devices: bd_lock
    balls_to_lock: 3
    balls_to_replace: 2
    reset_count_for_current_player_events: multiball_main_mb_started
```

When a ball enters `bd_lock` while the lock is enabled:

1. The lock counts it for the current player and posts `multiball_lock_vuk_lock_locked_ball` with
   `total_balls_locked`.
2. It keeps the ball in the device, if that makes sense (see below), and asks the playfield for a replacement ball,
   so the player keeps playing.
3. When the count reaches `balls_to_lock`, it posts `multiball_lock_vuk_lock_full`.

In the test run, the first lock left two balls in the trough, one in the VUK and one on the playfield, and posted
`locked_ball` with `total_balls_locked: 1`. The second lock served another ball from the trough. The third posted
`full`, which starts the multiball.

### Releasing all three balls

Two settings make the third lock start the multiball with the three locked balls, and no ball from the trough:

- **`balls_to_replace: 2`** serves a replacement ball for the first two locks only. The third locked ball is the
  player's ball, and the multiball is about to release it, so no new ball is needed.
- **`eject_all_events: multiball_main_mb_started`** on the VUK empties it when the multiball starts. The multiball
  only takes `ball_count` minus the balls already in play from its locks (`Multiball.start`), and it counts the
  player's ball as in play even though that ball is now sitting in the VUK. So it takes two of the three locked
  balls, and this event releases the third.

{{< note >}}
**Without these two settings, one ball stays in the lock.** In a test run with neither, the third lock served a ball
from the trough as a replacement, and the multiball then released two of the three locked balls. Three balls were in
play, but one stayed in the VUK for the rest of the game.
{{< /note >}}

A lock with no `enable_events` is enabled whenever its mode runs. Without a running lock (in attract mode, or a mode
that does not have it), a ball entering `bd_lock` is simply ejected again, like any [saucer](/build/ball-devices/#saucers-and-kickers).

### Physical and virtual locks

The lock above is **physical**: the VUK holds the locked balls until the multiball. Many machines have a **virtual**
lock instead, where the device holds one ball at most, often a scoop. The lock counts each ball for the player and
kicks it straight back out, and the multiball takes its balls from the trough. A virtual lock also suits several
players sharing a lock, since there are no held balls for one player to take from another.

In MPF, a virtual lock is a `multiball_locks:` device on a ball device that can only hold one ball, with the default
settings:

```yaml
ball_devices:
  bd_scoop:
    ball_switches: s_scoop
    eject_coil: c_scoop_eject
    eject_targets: playfield
    eject_timeouts: 3s

multiball_locks:
  scoop_lock:
    lock_devices: bd_scoop
    balls_to_lock: 3
    reset_count_for_current_player_events: multiball_main_mb_started
```

MPF keeps a ball in the device only if there is room for it and for the rest of the lock
(`MultiballLock._lock_ball`). With room for one ball and three to lock, it keeps none. In a test run of this page's
machine with the VUK reduced to one switch, each of the three locks posted `locked_ball` and kicked the ball back out
with no new ball from the trough. The third posted `full` and started the multiball: the ball in the device and two
from the trough, three on the playfield.

{{< warn >}}
**Leave out `balls_to_replace` on a virtual lock.** With `balls_to_replace: 2` on a one-ball device, MPF stopped
with `KABOOM! We just added a ball to bd_trough which has a capacity of 4 but already had 4
ball(s)`: no replacement was served for the third lock, but the ball wasn't kept either, so MPF lost count of a ball. In the test run this happened when the last ball drained after the multiball.
{{< /warn >}}

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
of the ball. In the test run without `reset_count_for_current_player_events`, the lock showed 3 locked balls on ball
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
the VUK released all three balls (two taken by the multiball, the third by `eject_all_events`), and the trough kept
its ball. Three balls were in play.

### The multiball's ball save

During `shoot_again`, a drain does not reduce the balls in play. The multiball handles `ball_drain` (a
[relay event](/architecture/how-events-work/#relay-passing-a-changing-value-along)), posts
`multiball_main_mb_shoot_again` with the number of balls saved, and adds them back. In the test run, a drain 6
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
    ball_switches: s_trough1, s_trough2, s_trough3, s_trough4
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 3s
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
| Ball 1 on the playfield | 3 | 0 | 1 | 1 | 0 | 0 |
| First ball locked (new ball served) | 2 | 1 | 1 | 1 | 1 | 1000 |
| Second ball locked (new ball served) | 1 | 2 | 1 | 1 | 2 | 2000 |
| Third ball locked: multiball starts, no new ball | 1 | 3 → 0 | 3 | 3 | 0 | 3000 |
| Target during multiball | | | | 3 | | 3100 |
| Drain within `shoot_again` (replaced) | 1 | 0 | 3 | 3 | | |
| Drain after the window | 2 | 0 | 2 | 2 | | |
| Drain: one ball left, multiball ended | 3 | 0 | 1 | 1 | | |
| Last drain: ball 2 starts | | | | 1 | 0 | 3100 |
| Ball into the VUK on ball 2 | 2 | 1 | 1 | 1 | 1 | 4100 |
