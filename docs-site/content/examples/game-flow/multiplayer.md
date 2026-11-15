---
title: "Multiplayer game flow"
weight: 3
summary: "Adding players, taking turns, and which progress belongs to each player: lit lanes, counters and player variables, against machine-wide values."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** Up to four players. Pressing start during the first ball adds a player; after that it does nothing.
Players take turns, one ball each. Three lanes light as they are hit, and lighting all three scores 10,000 and adds
1 to the player's lane completions. Each player keeps their own lit lanes and completions from turn to turn, so a
player who lit two lanes finds them still lit on their next ball, while the next player starts with none. A
machine-wide count of ramp shots, for all players and games, is kept as well.

**What it uses.** MPF's game and player handling, [shots and a shot group](/build/shots-and-scoring/#shot-groups),
player variables, and a machine variable.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the events and values below are from that run.
{{< /tip >}}

## How it works

### Adding players and taking turns

Nothing needs to be configured for this; it's MPF's built-in `game` mode. The first press of start starts a game with
one player, and each later press adds one, up to `max_players` (MPF's default is 4, set under `game:` in the machine
config, with `balls_per_game`, default 3).

Players can only be added while the current player is on ball 1 (`Game.request_player_add`), so during the first
round of turns. In the test run, three presses of start on ball 1 made a three-player game, each
posting `player_added`, and a press on player 1's second ball did nothing.

When a player's ball ends, the next player's turn begins. Each turn posts:

| Event | Arguments |
|---|---|
| `player_turn_started` | `number`, the player's number, from 1, and `player` |
| `ball_started` | `ball` and `player` |

`current_player` in a condition or a `score:` value always means the player whose turn it is.

### What each player keeps

Anything stored in a player variable belongs to that player:

- **Player variables:** `score`, and any variable a `variable_player` entry creates, such as `lanes_completed` below.
- **Shot states:** each shot's state is kept in a player variable (`shot_lane_left` and so on), so lit lanes are per
  player and survive the end of the ball.
- **Counters and other logic blocks with `persist_state: true`** (see
  [Drop target bank and extra ball](/examples/ball-in-play/drop-targets-extra-ball/#lighting-and-collecting-the-extra-ball)).
- **Multiball lock counts** (see [Lock-based multiball](/examples/multiball/lock-multiball/#two-players-one-vuk)).

Physical things aren't per player. A drop target bank is reset at the start of every ball, so a player doesn't find
their half-cleared bank waiting for them, and balls sitting in a lock are shared by everyone.

### The lanes

```yaml
shots:
  lane_left:
    switch: s_lane_left
  lane_center:
    switch: s_lane_center
  lane_right:
    switch: s_lane_right

shot_groups:
  lanes:
    shots: lane_left, lane_center, lane_right
    reset_events: lanes_lit_complete

variable_player:
  lanes_lit_complete:
    score: 10000
    lanes_completed: 1
```

### A machine-wide count

A machine variable is shared by everyone and kept across games. `variable_player` changes one with `action: add_machine`
(or `set_machine`):

```yaml
variable_player:
  s_ramp_active:
    score: 1000
    total_ramps:
      int: 1
      action: add_machine
```

In the test run, the count went on from player to player, and from one game into the next: 4 ramps in the first game,
and the first ramp of a new game made it 5. Whether a machine variable also survives a restart of MPF depends on it
being saved, which this example doesn't set up.

## What happened in the test run

| Step | Player, ball | Score | Lanes lit (L, C, R) | `lanes_completed` | `total_ramps` | What happened |
|---|---|---|---|---|---|---|
| Start | 1, 1 | 0 | none | | | `player_added`, `game_started`, `player_turn_started` with `number: 1`, `ball_started` |
| Start, start | 1, 1 | 0 | none | | | `player_added` twice: three players |
| Left and center lanes, ramp | 1, 1 | 1,000 | L, C | | 1 | |
| The ball drains | 2, 1 | 0 | none | | 1 | Player 2's turn: no lanes lit |
| All three lanes | 2, 1 | 10,000 | none | 1 | 1 | `lanes_lit_complete`; the lanes reset |
| Two ramps | 2, 1 | 12,000 | none | 1 | 3 | |
| The ball drains, player 3 hits the ramp, drains | 1, 2 | 1,000 | **L, C** | | 4 | Player 1's lanes are still lit |
| Start | 1, 2 | 1,000 | L, C | | 4 | Nothing: past ball 1 |
| Right lane | 1, 2 | 11,000 | none | 1 | 4 | `lanes_lit_complete` for player 1 |
| The remaining balls drain | | | | | 4 | `game_ended` after player 3's ball 3 |
| A new game, ramp | 1, 1 | 1,000 | none | | 5 | The machine variable carried over; the player variables didn't |

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
  s_lane_left:
    number:
    tags: playfield_active
  s_lane_center:
    number:
    tags: playfield_active
  s_lane_right:
    number:
    tags: playfield_active
  s_ramp:
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
  lanes:
    shots: lane_left, lane_center, lane_right
    reset_events: lanes_lit_complete

variable_player:
  lanes_lit_complete:
    score: 10000
    lanes_completed: 1
  s_ramp_active:
    score: 1000
    total_ramps:
      int: 1
      action: add_machine
```
