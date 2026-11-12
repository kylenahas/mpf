---
title: "Modes"
weight: 5
summary: "What a mode is, when it starts and stops, priority, mode-only config, and MPF's built-in modes."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

A **mode** is a bundle of config that is only active while the mode runs. A skill shot, a multiball, a hurry-up,
attract mode and the game itself are all modes. While a mode runs, its config players, shots, timers and other
mode devices are active; when it stops, they go away.

{{< tip >}}
**Verified.** The machine on this page (machine config and all four mode files) was run on MPF 0.82.0.dev0 with
`MpfGameTestCase` on the smart virtual platform. `docs-site/verify/test_guides.py` reads the files from this page and
repeats every check below.
{{< /tip >}}

## Where modes live

Each mode is a folder in your machine folder, and the machine config lists the modes to load:

```text
my_machine/
  config/config.yaml          modes: [base, skillshot, hurry_up, lamp_test]
  modes/
    base/config/base.yaml
    skillshot/config/skillshot.yaml
    ...
```

The file must be at `modes/<name>/config/<name>.yaml`. A listed mode without one stops MPF at startup with
"No config found for mode 'bonus_round'. MPF expects the config at 'modes/bonus_round/config/bonus_round.yaml' inside
your machine folder."

Every mode file has a `mode:` section that says when it runs. The rest of the file is ordinary config (players, shots,
timers and so on) that is only active while the mode runs. Whether a section is allowed in a mode file is listed as
**Valid in** on its [reference page](/reference/config/).

## Starting and stopping

| Setting | Default | What it does |
|---|---|---|
| `start_events` | none | Events that start the mode. |
| `stop_events` | none | Events that stop it. |
| `priority` | `100` | Higher runs "on top" (see below). |
| `game_mode` | `true` | The mode can only run during a game. |
| `stop_on_ball_end` | `true` | Stop the mode when the ball ends. |
| `restart_on_next_ball` | `false` | If the mode was running when the ball ended, start it again on that player's next ball. |
| `events_when_started`, `events_when_stopped` | none | Events to post when the mode has started or stopped. |
| `use_wait_queue` | `false` | Hold up the event that started the mode until the mode stops (for queue events such as `ball_ending`). |

Rules from `mpf/core/mode.py`:

- A **game mode** started outside a game is ignored, with the log warning "Can only start mode ... during a game.
  Aborting start." In the test run, posting `start_hurry_up` in attract mode did nothing.
- A game mode must stop at ball end. `game_mode: true` with `stop_on_ball_end: false` stops MPF with "All game modes
  need to stop at ball end" (error 1). A mode that should outlive the ball sets both to `false`.
- Starting a mode that is already running does nothing.

MPF posts these events as a mode changes state, so other config can react:
`mode_<name>_will_start`, `mode_<name>_starting`, `mode_<name>_started`, `mode_<name>_will_stop`,
`mode_<name>_stopping`, `mode_<name>_stopped`.

### Priority

`priority` orders modes against each other. Event handlers that belong to a mode run at the mode's priority (plus any
priority of their own), and handlers run from highest to lowest (`Mode.add_mode_event_handler`). Lights, shows and
slides from a higher-priority mode cover those from lower-priority modes. Built-in modes use low numbers (`attract` is
10, `game` 20), so your game modes at 100 and up sit above them.

## An example machine

Four modes, each showing one pattern. The machine config is the trough from
[Your first machine](/get-started/first-machine/) with one ball, plus three playfield switches.

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - skillshot
  - hurry_up
  - lamp_test

machine:
  balls_installed: 1

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_upper_lane:
    number:
  s_left_sling:
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

### A mode for every ball

The `base` mode that `mpf init` creates runs for the whole of every ball. It is the place for scoring and rules that
are always on. Here it also starts the hurry-up when the target is hit.

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

event_player:
  s_target_active: start_hurry_up
```

`event_player` posts an event when another event happens. Because it is in the `base` mode file, it only works while
`base` runs, which is during a ball.

### A short-lived mode: skill shot

`modes/skillshot/config/skillshot.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_started
  stop_events: skillshot_made, s_left_sling_active
  priority: 200
  events_when_started: skillshot_lit

event_player:
  s_upper_lane_active: skillshot_made
```

The skill shot starts with each ball. It ends either when it is made (the upper lane posts `skillshot_made`, which is
also a stop event) or when the ball reaches the playfield and hits the slingshot first.

In the test run:

- In attract mode, hitting `s_upper_lane` posted nothing: the mode's `event_player` did not exist yet.
- When the ball started, `skillshot` was running and `skillshot_lit` was posted.
- Hitting `s_upper_lane` posted `skillshot_made` and stopped the mode. A second hit posted nothing.

### A mode that survives a drain: hurry-up

`modes/hurry_up/config/hurry_up.yaml`:

```yaml
#config_version=6

mode:
  start_events: start_hurry_up
  stop_events: hurry_up_collected
  priority: 300
  restart_on_next_ball: true
```

`restart_on_next_ball` keeps an unfinished hurry-up for the player. In the test run, the hurry-up was started by the
target on ball 1, stopped when ball 1 drained (because `stop_on_ball_end` is `true`), and started again on ball 2.
After `hurry_up_collected` was posted on ball 2, it did not come back on ball 3.

### A mode outside the game: lamp test

`modes/lamp_test/config/lamp_test.yaml`:

```yaml
#config_version=6

mode:
  start_events: start_lamp_test
  stop_events: stop_lamp_test
  game_mode: false
  stop_on_ball_end: false
```

With `game_mode: false`, the mode can run in attract mode. In the test run, `start_lamp_test` started it alongside
`attract`. Its priority was the default 100.

### What ran when

| Moment | Running modes (priority) |
|---|---|
| Boot | `attract` (10) |
| `start_lamp_test` in attract | `attract` (10), `lamp_test` (100) |
| Ball 1 starts | `game` (20), `base` (100), `skillshot` (200) |
| Upper lane hit | `game`, `base` |
| Target hit | `game`, `base`, `hurry_up` (300) |
| Ball 2 starts | `game`, `base`, `skillshot`, `hurry_up` |
| Sling hit, then `hurry_up_collected` | `game`, `base` |
| Ball 3 starts | `game`, `base`, `skillshot` |

## Built-in modes

MPF ships several modes in `mpf/modes/`. `attract` and `game` are always loaded (MPF's own `mpfconfig.yaml` lists
them). The others load when you add them to your `modes:` list, without needing a folder of your own:
`bonus`, `carousel`, `credits`, `high_score`, `match`, `service`, `tilt` and the service display modes. The
[built-in modes](/reference/builtin-modes/) reference lists their settings and events.

To change a built-in mode, create a file of the same name in your machine folder, for example
`modes/attract/config/attract.yaml`. MPF loads its own file first and then yours on top (`ConfigLoader._load_modes`),
so your file only needs the settings you change. The `attract.yaml` that `mpf init` creates works this way: it only
adds a `slide_player` entry.
