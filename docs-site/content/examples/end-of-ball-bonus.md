---
title: "End-of-ball bonus"
weight: 1
summary: "Count shots during the ball, raise a bonus multiplier by completing three rollover lanes, and count it all up when the ball drains."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** During the ball, every ramp and target is counted. Three rollover lanes at the top light as the ball
rolls through them, and the flipper buttons move the lit lanes left and right (lane change). Lighting all three raises
the bonus multiplier, up to 5x, and turns the lanes off for another round. When the ball drains, the machine counts
the bonus up one line at a time (a fixed ball bonus, then so much per ramp and per target), multiplies it, and adds it
to the score. Pressing both flipper buttons speeds the count up. The counts start again from zero on the next ball;
the multiplier goes back to 1x.

**What it uses.** [`variable_player`](/build/shots-and-scoring/#scoring-with-variable_player) to count,
[shots and a shot group](/build/shots-and-scoring/#shot-groups) for the lanes, a
[condition](/build/events/#conditions) to cap the multiplier, the built-in **`bonus`** mode to do the counting, and
the built-in [`flipper_cancel`](/build/events/#both-flipper-buttons) event for the speed-up.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the timings and scores below are from that run.
{{< /tip >}}

## How it works

### Counting during the ball

The `base` mode adds to player variables as shots are made. `ramps` and `targets` exist only to be counted by the
bonus; nothing else reads them.

```yaml
variable_player:
  s_ramp_active:
    score: 500
    ramps: 1
  s_target_active:
    score: 100
    targets: 1
```

### The rollover lanes

Each lane is a shot with MPF's `default` profile (`unlit`, then `lit`), and a shot group holds the three:

```yaml
shots:
  lane_left:
    switch: s_lane_left
  lane_center:
    switch: s_lane_center
  lane_right:
    switch: s_lane_right

shot_groups:
  bonus_lanes:
    shots: lane_left, lane_center, lane_right
    rotate_left_events: s_left_flipper_active
    rotate_right_events: s_right_flipper_active
    reset_events: bonus_lanes_lit_complete
```

- A lane that is already lit stays lit when the ball rolls through it again, so the player uses lane change to move
  the lit lanes away from where the ball is going. In the test run, with the left lane lit, one left flipper press
  moved it to the right lane (it wraps around); the ball then went through the left and center lanes and completed the
  set.
- When all three are lit the group posts `bonus_lanes_lit_complete`. Its own `reset_events` turns them all off again
  on that event, ready for the next round.
- Lane states are saved per player, so lanes lit on one ball are still lit on that player's next ball.

The scoring reacts to the group's events:

```yaml
variable_player:
  bonus_lanes_hit:
    score: 100
  bonus_lanes_lit_complete:
    score: 5000
  bonus_lanes_lit_complete{current_player.bonus_multiplier<5}:
    bonus_multiplier: 1
```

Every lane scores 100 and every completed set 5000. The condition on the second `bonus_lanes_lit_complete` entry stops
the multiplier at 5: once it reaches 5 that handler no longer runs, but the 5000 still does. In the test run, six
completed sets on one ball left the multiplier at 5.

{{< warn >}}
**Use `bonus_lanes_lit_complete`, not `bonus_lanes_complete`.** All three lanes are `unlit` when the game starts and
again after every reset, which also counts as "all in the same state", so `bonus_lanes_complete` (and
`bonus_lanes_unlit_complete`) are posted then too.
{{< /warn >}}

`bonus_multiplier` needs a starting value of 1, set in the machine config:

```yaml
player_vars:
  bonus_multiplier:
    initial_value: 1
```

Without it, a player variable that was never set reads as 0, so the first completed set would only bring the
multiplier to 1x and the player would need two sets for 2x. (The bonus mode itself treats a missing `bonus_multiplier` as 1.)

### The bonus mode

`bonus` is one of MPF's [built-in modes](/reference/builtin-modes/). Listing it under `modes:` loads it; its own
config (`mpf/modes/bonus/config/bonus.yaml`) already makes it start on `ball_ending` and hold that
[queue event](/architecture/how-events-work/#queue-holding-things-up) until the count is done, so the next ball waits
for it. Your `modes/bonus/config/bonus.yaml` only supplies `mode_settings`:

| Setting | Here | Meaning |
|---|---|---|
| `bonus_entries` | three entries | One line of the bonus each. |
| `entry` | `ramps` | The entry's name, posted with each `bonus_entry` event. |
| `score` | `1000` | Points for this line, multiplied by the player variable in `player_score_entry` if there is one. |
| `player_score_entry` | `ramps` | The player variable to multiply by. |
| `reset_player_score_entry` | `true` | Set that variable back to 0 after counting it. |
| `skip_if_zero` | default `true` | Leave out lines worth 0. |
| `display_delay_ms` | `1s` | Time between lines. |
| `hurry_up_delay_ms` | `100ms` | Time between lines after `hurry_up_event` (default `flipper_cancel`). |
| `keep_multiplier` | default `false` | Keep `bonus_multiplier` for the next ball instead of resetting it to 1. |

For each line the mode posts `bonus_entry` with `entry`, `score`, `text`, `hits` and the running `bonus_score`; your
display or sound config reacts to that one event. After the lines come `entry: subtotal` and `entry: multiplier`
(only when the multiplier is above 1) and `entry: total`. The bonus is skipped entirely if the ball ended by tilt
(`Bonus.mode_start`).

## What happened in the test run

**Ball 1:** three ramps, two targets and one set of lanes, then a drain. The lanes went: left lane (lit), left lane
again (already lit, so 100 points and no change), a left flipper press (the lit lane moved to the right), then the
left and center lanes (set complete, multiplier 2x, all three off again). Score before the bonus: 7100.

| Time after drain | `bonus_entry` | `score` | `bonus_score` |
|---|---|---|---|
| 0.5 s | (`bonus_start`) | | |
| 1.5 s | `ball_bonus` | 1000 | 1000 |
| 2.5 s | `ramps` (3 hits) | 3000 | 4000 |
| 3.5 s | `targets` (2 hits) | 500 | 4500 |
| 4.5 s | `subtotal` | 4500 | |
| 5.5 s | `multiplier` | 2 | |
| 6.5 s | `total` | 9000 | |
| 7.5 s | (`ball_ended`, ball 2 starts) | | |

Score after the bonus: 16,100. `ramps` and `targets` were back to 0 and the multiplier back to 1.

**Ball 2:** one ramp and six sets of lanes (multiplier capped at 5), then a drain, with both flipper buttons pressed
1.2 seconds in. The next line came the moment both buttons were down, then the rest every 0.1 s: `ball_bonus` 1000,
`ramps` 1000 (the `targets` line was skipped, being 0), `subtotal` 2000, `multiplier` 5, `total` 10,000. Ball 3 started
0.5 s after the press. Score after the bonus: 58,400.

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - bonus

machine:
  balls_installed: 1

player_vars:
  bonus_multiplier:
    initial_value: 1

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_left_flipper:
    number:
    tags: left_flipper
  s_right_flipper:
    number:
    tags: right_flipper
  s_ramp:
    number:
    tags: playfield_active
  s_target:
    number:
    tags: playfield_active
  s_lane_left:
    number:
    tags: playfield_active
  s_lane_center:
    number:
    tags: playfield_active
  s_lane_right:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:

ball_devices:
  bd_trough:
    ball_switches: s_trough1
    eject_coil: c_trough_eject
    eject_targets: playfield
    tags: trough, drain, home

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

virtual_platform_start_active_switches: s_trough1
```

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

shots:
  lane_left:
    switch: s_lane_left
  lane_center:
    switch: s_lane_center
  lane_right:
    switch: s_lane_right

shot_groups:
  bonus_lanes:
    shots: lane_left, lane_center, lane_right
    rotate_left_events: s_left_flipper_active
    rotate_right_events: s_right_flipper_active
    reset_events: bonus_lanes_lit_complete

variable_player:
  s_ramp_active:
    score: 500
    ramps: 1
  s_target_active:
    score: 100
    targets: 1
  bonus_lanes_hit:
    score: 100
  bonus_lanes_lit_complete:
    score: 5000
  bonus_lanes_lit_complete{current_player.bonus_multiplier<5}:
    bonus_multiplier: 1
```

`modes/bonus/config/bonus.yaml`:

```yaml
#config_version=6

mode_settings:
  display_delay_ms: 1s
  hurry_up_delay_ms: 100ms
  bonus_entries:
    - entry: ball_bonus
      text: BALL BONUS
      score: 1000
    - entry: ramps
      text: RAMPS
      score: 1000
      player_score_entry: ramps
      reset_player_score_entry: true
    - entry: targets
      text: TARGETS
      score: 250
      player_score_entry: targets
      reset_player_score_entry: true
```
