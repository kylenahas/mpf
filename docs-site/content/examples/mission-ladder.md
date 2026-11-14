---
title: "Missions and a wizard mode"
weight: 3
summary: "Pick a mission with the slingshot, start it at the scoop, finish it against a clock; finishing every mission starts a wizard mode."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** The machine offers a list of missions. The slingshot changes which one is selected; the scoop starts the
selected one. Each mission is its own mode with its own goal and a 20-second clock: make the shots in time and the
mission is completed (worth 50,000), run out of time and it stops and can be tried again later. While a mission is
running the selection is locked. When every mission is completed, the wizard mode starts: every ramp and target is
worth 100,000, and the scoop ends it with a 1,000,000 award. Finishing the wizard resets the missions so the player
can go round again. Progress is kept per player across balls.

**What it uses.** **Achievements** (one per mission) and an **achievement group** (the selection), one
[mode](/build/modes/) per mission with a [counter and a timer](/build/events/#more-examples), and
[`|block`](/build/shots-and-scoring/#blocking-lower-modes) in the wizard mode.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the states and scores below are from that run.
{{< /tip >}}

## How it works

### Achievements: the state of each mission

An achievement is a device that remembers, for each player, where one goal stands: `enabled` (available),
`started`, `completed`, `stopped` (tried and failed) or `disabled`. It does not do anything itself. Its settings
connect it to events:

```yaml
achievements:
  ramps:
    complete_events: mission_ramps_won
    stop_events: mission_ramps_lost
    events_when_started: start_mission_ramps
    reset_events: wizard_finished
```

- `events_when_started: start_mission_ramps` starts the mission's mode (its `start_events`).
- The mission mode posts `mission_ramps_won` or `mission_ramps_lost`, which complete or stop the achievement.
- Each change posts `achievement_ramps_state_<state>`, used here to score the completion:
  `achievement_ramps_state_completed: {score: 50000}`.
- `reset_events: wizard_finished` makes the mission available again after the wizard mode.

Achievements are valid in mode configs; here they are in `base`, which runs for every ball. Their state is stored on
the player (`Achievement.state` in `mpf/devices/achievement.py`), so it carries from ball to ball.

### The achievement group: choosing a mission

```yaml
achievement_groups:
  missions:
    achievements: ramps, targets
    auto_select: true
    disable_random: true
    rotate_right_events: s_left_sling_active
    start_selected_events: s_scoop_active
    events_when_all_completed: start_wizard
```

| Setting | What it does here |
|---|---|
| `auto_select: true` | Always keep one available mission selected. |
| `disable_random: true` | Select the first available mission instead of a random one (`ramps` first in the test run). |
| `rotate_right_events` | Move the selection to the next available mission. |
| `start_selected_events` | Start the selected mission. |
| `events_when_all_completed` | Posted when every member is completed. |

While a member is `started`, the group disables itself (`disable_while_achievement_started`, default `true`), so the
slingshot and scoop do nothing until the mission ends, and it re-enables afterwards
(`enable_while_no_achievement_started`). A `stopped` mission can be selected and started again
(`restart_after_stop_possible`, default `true`); a `completed` one is skipped.

### One mode per mission

Each mission is a mode that starts on its `start_mission_...` event and stops on either result:

```yaml
mode:
  start_events: start_mission_ramps
  stop_events: mission_ramps_won, mission_ramps_lost
  priority: 200

counters:
  mission_ramp_count:
    count_events: s_ramp_active
    count_complete_value: 3
    events_when_complete: mission_ramps_won

timers:
  mission_ramps_clock:
    start_value: 20
    end_value: 0
    direction: down
    start_running: true

event_player:
  timer_mission_ramps_clock_complete: mission_ramps_lost
```

The counter and timer only exist while the mission runs, so each attempt starts with a fresh count and a full clock.
The targets mission is the same with `s_target_active` and two hits.

If the ball drains during a mission, the mode stops with the ball. In the test run, the achievement was then
`stopped` (and still selected) on the next ball; starting it again began from zero ramps.

### The wizard mode

```yaml
mode:
  start_events: start_wizard
  stop_events: wizard_finished
  priority: 300

event_player:
  s_scoop_active: wizard_finished

variable_player:
  s_ramp_active:
    score: 100000|block
  s_target_active:
    score: 100000|block
  wizard_finished:
    score: 1000000
```

The wizard runs at priority 300, above the missions (200) and `base` (100). `|block` makes its 100,000 replace any
lower mode's score for the same switch instead of adding to it. The scoop posts `wizard_finished`, which stops the
mode, scores 1,000,000 and resets both achievements.

## What happened in the test run

`*` marks the selected mission.

| Step | Score | ramps | targets | Mode running |
|---|---|---|---|---|
| Ball 1 starts | 0 | enabled\* | enabled | |
| Slingshot | 0 | enabled | enabled\* | |
| Slingshot | 0 | enabled\* | enabled | |
| Scoop: start the ramps mission | 0 | started | enabled | `mission_ramps` |
| Slingshot and scoop during the mission | 0 | started | enabled | `mission_ramps` (no change) |
| 20 seconds pass | 0 | stopped\* | enabled | |
| Scoop: try again | 0 | started | enabled | `mission_ramps` |
| Three ramps (3 × 5,000, then 50,000) | 65,000 | completed | enabled\* | |
| Ball 2 starts | 65,000 | completed | enabled\* | |
| Scoop: start the targets mission | 65,000 | completed | started | `mission_targets` |
| Two targets (2 × 5,000, then 50,000): all completed | 125,000 | completed | completed | `wizard` |
| Ramp during the wizard | 225,000 | | | `wizard` |
| Scoop: wizard finished (+1,000,000) | 1,225,000 | enabled\* | enabled | |
| Scoop: the ladder starts again | 1,225,000 | started | enabled | `mission_ramps` |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - mission_ramps
  - mission_targets
  - wizard

machine:
  balls_installed: 1

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_left_sling:
    number:
  s_scoop:
    number:
    tags: playfield_active
  s_ramp:
    number:
    tags: playfield_active
  s_target:
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

achievements:
  ramps:
    complete_events: mission_ramps_won
    stop_events: mission_ramps_lost
    events_when_started: start_mission_ramps
    reset_events: wizard_finished
  targets:
    complete_events: mission_targets_won
    stop_events: mission_targets_lost
    events_when_started: start_mission_targets
    reset_events: wizard_finished

achievement_groups:
  missions:
    achievements: ramps, targets
    auto_select: true
    disable_random: true
    rotate_right_events: s_left_sling_active
    start_selected_events: s_scoop_active
    events_when_all_completed: start_wizard

variable_player:
  achievement_ramps_state_completed:
    score: 50000
  achievement_targets_state_completed:
    score: 50000
```

`modes/mission_ramps/config/mission_ramps.yaml`:

```yaml
#config_version=6

mode:
  start_events: start_mission_ramps
  stop_events: mission_ramps_won, mission_ramps_lost
  priority: 200

counters:
  mission_ramp_count:
    count_events: s_ramp_active
    count_complete_value: 3
    events_when_complete: mission_ramps_won

timers:
  mission_ramps_clock:
    start_value: 20
    end_value: 0
    direction: down
    start_running: true

event_player:
  timer_mission_ramps_clock_complete: mission_ramps_lost

variable_player:
  s_ramp_active:
    score: 5000
```

`modes/mission_targets/config/mission_targets.yaml`:

```yaml
#config_version=6

mode:
  start_events: start_mission_targets
  stop_events: mission_targets_won, mission_targets_lost
  priority: 200

counters:
  mission_target_count:
    count_events: s_target_active
    count_complete_value: 2
    events_when_complete: mission_targets_won

timers:
  mission_targets_clock:
    start_value: 20
    end_value: 0
    direction: down
    start_running: true

event_player:
  timer_mission_targets_clock_complete: mission_targets_lost

variable_player:
  s_target_active:
    score: 5000
```

`modes/wizard/config/wizard.yaml`:

```yaml
#config_version=6

mode:
  start_events: start_wizard
  stop_events: wizard_finished
  priority: 300

event_player:
  s_scoop_active: wizard_finished

variable_player:
  s_ramp_active:
    score: 100000|block
  s_target_active:
    score: 100000|block
  wizard_finished:
    score: 1000000
```

To add a mission, add an achievement and a mode for it, and list the achievement in the group. The wizard starts only
when all of the group's achievements are completed.
