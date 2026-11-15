---
title: "Shots and scoring"
weight: 7
summary: "Scoring with variable_player, shots and their states, shot profiles, shot groups with lane change, and blocking scores from lower modes."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

Scoring in MPF is a player variable called `score` that config adds to when events happen. **Shots** turn switch
hits into richer events: a shot remembers a state (unlit, lit, ...), advances when hit, and posts an event that names
both the shot and its state, so different states can score differently.

{{< tip >}}
**Verified.** The machine on this page (machine config and both mode files) was run on MPF 0.82.0.dev0 with
`MpfGameTestCase`. Every score and state below is from that run, and `docs-site/verify/test_guides.py` repeats it.
{{< /tip >}}

## Scoring with variable_player

`variable_player:` changes player variables when events are posted. Each key is an event; under it, each player
variable and the amount to add:

```yaml
variable_player:
  s_left_sling_active:
    score: 10
  ramp_super_hit:
    score: 25000
    ramp_supers: 1
```

- `score` is just a player variable. Any other name (`ramp_supers` above) creates or changes a player variable of
  that name; MPF posts `player_<name>` whenever one changes.
- A value can be a placeholder expression such as `current_player.ramps * 10`, from MPF's tests
  (`variable_player/modes/mode2/config/mode2.yaml`).
- Several variables under one event change in the order they're written. A `score:` line after an increase sees the
  new value, and one before it sees the old value. In test runs, the [Combos](/examples/scoring/combos/#scoring-the-chain)
  example increases its count and then scores it, and the
  [Drop target bank](/examples/ball-in-play/drop-targets-extra-ball/#a-value-that-grows) example scores the bank value
  and then raises it.
- The long form sets more options:

```yaml
variable_player:
  test_set_100:
    test1:
      int: 100
      action: set
```

| `action` | Effect |
|---|---|
| `add` (default) | Add to the player variable. |
| `set` | Set the player variable. |
| `add_machine`, `set_machine` | Change a machine variable instead (shared by all players). |

`int`, `float` or `string` gives the value and its type. `player: 2` targets a specific player instead of the current
one.

Scoring only happens during a game: there is no current player in attract mode.

### Blocking lower modes

When several running modes score the same event, all of them score. Add `|block` (or `block: true` in the long form) in
a higher-priority mode to stop lower-priority modes from changing that variable for that event:

```yaml
variable_player:
  s_left_sling_active:
    score: 20|block
```

In the test run, the slingshot scored 10 from the `base` mode. While a priority-300 `double_scoring` mode with the
entry above was running, it scored 20 (not 30); after that mode stopped, it scored 10 again.

## Shots

A shot is one or more switches plus a state. Shots are valid in mode configs only, and they only react during a game.

```yaml
shots:
  lane1:
    switch: s_lane1
```

With no `profile:`, a shot uses MPF's `default` profile from `mpfconfig.yaml`, with two states: `unlit` and `lit`.
A hit **advances** the shot to the next state. At the last state it stays there unless the profile has `loop: true`.

### Events a hit posts

Every hit posts four events (`Shot.hit`), all named after the state the shot was in **when it was hit**, before it
advances:

| Event | Example (lane1 hit while unlit) |
|---|---|
| `<shot>_hit` | `lane1_hit` |
| `<shot>_<state>_hit` | `lane1_unlit_hit` |
| `<shot>_<profile>_hit` | `lane1_default_hit` |
| `<shot>_<profile>_<state>_hit` | `lane1_default_unlit_hit` |

Each carries `profile`, `state` and `advancing` arguments. So `lane1_unlit_hit` scores the first hit and
`lane1_lit_hit` scores every later one.

Shot states are saved per player (player variable `shot_<name>`), so they survive the end of the ball and each player
has their own.

### Custom profiles

A shot profile lists the states a shot moves through. Define profiles in the machine config (or a mode) and point a
shot at one with `profile:`:

```yaml
shot_profiles:
  ramp_levels:
    states:
      - name: off
      - name: lit
      - name: super

shots:
  ramp:
    switch: s_ramp
    profile: ramp_levels

variable_player:
  ramp_off_hit:
    score: 1000
  ramp_lit_hit:
    score: 5000
  ramp_super_hit:
    score: 25000
    ramp_supers: 1
```

In the test run, the ramp scored 1000, 5000, 25000, 25000 on four hits and moved `off` → `lit` → `super`, then stayed
at `super`. Each state can also name a `show` to run while the shot is in it (for its light); MPF's default profile
uses the `off` and `on` shows that way.

| Profile setting | Default | What it does |
|---|---|---|
| `states` | required | The states, in order. |
| `loop` | `false` | After the last state, go back to the first. |
| `advance_on_hit` | `true` | Advance on every hit. Set `false` to advance only with `advance_events`. |
| `block` | `false` | When a shot with this profile handles a hit, lower-priority shots (in lower-priority modes) on the same switch ignore it (`Shot.event_hit`). |
| `rotation_pattern` | `R` | Default direction for `rotate_events` on shot groups. |

## Shot groups

A shot group watches several shots: a bank of lanes or targets.

```yaml
shot_groups:
  top_lanes:
    shots: lane1, lane2, lane3
    rotate_left_events: s_left_flipper_active
    rotate_right_events: s_right_flipper_active
    reset_events: top_lanes_lit_complete
```

- **`<group>_hit`** is posted when any member is hit (in the test run, every lane hit scored 100 through
  `top_lanes_hit`).
- **`<group>_complete`** and **`<group>_<state>_complete`** are posted when all members reach the same state
  (`ShotGroup._check_for_complete`).
- **Lane change.** `rotate_left_events` and `rotate_right_events` shift the states one place along the group. In the
  test run, with lane1 lit, a left flipper press moved the lit lane to lane3 (it wraps around), and a right flipper
  press moved it back to lane1.
- **`reset_events`** puts every member back in its first state. Resetting on `top_lanes_lit_complete` relights the
  lanes for another round.

{{< warn >}}
**React to `<group>_lit_complete`, not `<group>_complete`.** At the start of every ball all lanes are `unlit`, which is
also "all in the same state": in the test run, `top_lanes_complete` and `top_lanes_unlit_complete` were posted as the
game started, before any lane was hit.
{{< /warn >}}

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - double_scoring

machine:
  balls_installed: 1

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
  s_left_sling:
    number:
    tags: playfield_active
  s_lane1:
    number:
  s_lane2:
    number:
  s_lane3:
    number:
  s_ramp:
    number:

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

shot_profiles:
  ramp_levels:
    states:
      - name: off
      - name: lit
      - name: super

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
  lane1:
    switch: s_lane1
  lane2:
    switch: s_lane2
  lane3:
    switch: s_lane3
  ramp:
    switch: s_ramp
    profile: ramp_levels

shot_groups:
  top_lanes:
    shots: lane1, lane2, lane3
    rotate_left_events: s_left_flipper_active
    rotate_right_events: s_right_flipper_active
    reset_events: top_lanes_lit_complete

variable_player:
  s_left_sling_active:
    score: 10
  top_lanes_hit:
    score: 100
  top_lanes_lit_complete:
    score: 5000
  ramp_off_hit:
    score: 1000
  ramp_lit_hit:
    score: 5000
  ramp_super_hit:
    score: 25000
    ramp_supers: 1
```

`modes/double_scoring/config/double_scoring.yaml`:

```yaml
#config_version=6

mode:
  start_events: start_double_scoring
  stop_events: stop_double_scoring
  priority: 300

variable_player:
  s_left_sling_active:
    score: 20|block
```

What the test run showed:

| Step | Score | Lanes (1, 2, 3) |
|---|---|---|
| Ball 1 starts | 0 | unlit, unlit, unlit |
| Slingshot | 10 | |
| Lane 1 (unlit → lit, +100) | 110 | lit, unlit, unlit |
| Lane 1 again (stays lit, +100) | 210 | lit, unlit, unlit |
| Left flipper (rotate left) | 210 | unlit, unlit, lit |
| Right flipper (rotate right) | 210 | lit, unlit, unlit |
| Lanes 2 and 3 (+100 each, all lit: +5000, reset) | 5410 | unlit, unlit, unlit |
| Ramp ×4 (+1000, +5000, +25000, +25000) | 61410 | ramp: `super`, `ramp_supers` 2 |
| Slingshot during `double_scoring` (+20, blocked base) | 61430 | |
| Slingshot after it stops (+10) | 61440 | |
| Ball 2 starts | 61440 | ramp still `super` |

Hitting a lane in attract mode, before the game, posted no shot events.
