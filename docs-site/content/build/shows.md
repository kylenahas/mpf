---
title: "Lights and shows"
weight: 8
summary: "Lights, show steps and timing, show files and tokens, show_player options, and lighting shots from their state."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

A **show** is a list of timed steps. Each step can set lights, post events, pulse coils and more. Shows are how MPF
does light effects: attract mode sweeps, flashing a target when it is hit, lighting a lane when its shot is lit.

{{< tip >}}
**Verified.** The machine on this page (machine config, show file and base mode) was run on MPF 0.82.0.dev0 with
`MpfGameTestCase`. Light colors and timings below are from that run, and `docs-site/verify/test_guides.py` repeats
the checks.
{{< /tip >}}

## Lights

```yaml
lights:
  l_target:
    number:
  l_lane1:
    number:
    tags: lane_lights
```

`number` is the light's address on your hardware (empty on the virtual platforms). Other settings cover RGB channels,
`type`, `default_on_color` (default white) and `fade_ms`; see the [`lights` reference](/reference/config/devices/lights/).

Colors can be names (`red`, `blue`, `white`), hex (`ff8000`), `on` (the light's `default_on_color`) or `off`.

## Show steps

A show is a list of steps. Each step has a timing key and one or more sections:

```yaml
shows:
  attract_sweep:
    - duration: 500ms
      lights:
        l_lane1: white
        l_lane2: off
    - duration: 500ms
      lights:
        l_lane1: off
        l_lane2: white
```

### Timing

Use **either** `duration` on every step, **or** `time` on every step (from `Show._get_duration` in
`mpf/assets/show.py`):

| Key | Meaning |
|---|---|
| `duration: 500ms` | How long this step lasts. `-1` holds the step until the show is advanced or stopped. |
| `time: 1s` | When this step starts, from the start of the show. |
| `time: +1s` | When this step starts, relative to the previous step. |
| none | The step lasts 1 second. |

With `time`, end the show with a last step that has only a `time:`; it marks the end of the show (the
`start_pulse` show below does this). A step with `duration` followed by a step with `time` is an error ("Found invalid
'time' entry in step after ... which contains a duration", error 8).

### Sections

The section names in a step are the config players' show names: `lights`, `events`, `coils`, `flashers`, `shows`,
`segment_displays` and others (`show_section` in each player in `mpf/config_players/`). A light can be faded by
adding `-f` and a time to its color:

```yaml
- time: 0
  lights:
    (light): blue-f200ms
```

In the test run, the light was half blue (`00007f`) 100 ms into that step and full blue at 200 ms.

## Show files and tokens

A show can live in the `shows:` section of a config (as above) or in its own file in a `shows/` folder of your machine
(or of a mode), named after the show. A show file starts with `#show_version=6` and is just the list of steps.

`shows/flash_light.yaml`:

```yaml
#show_version=6
- duration: 250ms
  lights:
    (light): red
- duration: 250ms
  lights:
    (light): off
```

`(light)` is a **token**: a placeholder filled in when the show is played, with `show_tokens`. One show can then flash
any light.

## Playing shows

`show_player:` plays and stops shows on events. The short form names a show; the long form adds settings:

```yaml
show_player:
  mode_attract_started: attract_sweep
  mode_attract_stopped:
    attract_sweep: stop
  s_target_active:
    flash_light:
      loops: 2
      show_tokens:
        light: l_target
      events_when_completed: target_flash_done
```

| Setting | Default | What it does |
|---|---|---|
| `loops` | `-1` | How many times to **repeat**. `-1` repeats forever, `0` plays once, `2` plays three times. |
| `show_tokens` | none | Values for the show's tokens. |
| `priority` | `0` | Added to the mode's priority; a higher show covers lights set by a lower one. |
| `speed` | `1` | Playback speed multiplier. |
| `action` | `play` | Also `stop`, `pause`, `resume`, `advance`, `step_back`, `update`, `queue`. The short form `show: stop` sets this. |
| `events_when_played`, `events_when_completed`, `events_when_looped`, ... | none | Events to post as the show plays. |

In the test run:

- `attract_sweep` alternated the two lane lights every 0.5 s in attract mode and stopped when the game started.
- A target hit flashed `l_target` red three times (250 ms on, 250 ms off), then posted `target_flash_done` and left the
  light off.

{{< warn >}}
**Shows repeat forever unless you set `loops`.** In the test run, `start_pulse` without `loops` turned `l_start` blue
again every 2 seconds for as long as the ball lasted. With `loops: 0` it played once and the light stayed off.
{{< /warn >}}

A show played from a mode stops when the mode stops, and its lights go back to whatever is underneath.

MPF's own `mpfconfig.yaml` defines three shows you can use with a `light` (or `lights`, `led`, `leds`) token:
`on`, `off` (both hold until stopped) and `flash` (one second on, one second off).

## Lighting shots

The shot profiles from [shots and scoring](/build/shots-and-scoring/) name a show for each state; MPF's default
profile uses the `off` and `on` shows above. Give the shot the token, and its light follows its state:

```yaml
shots:
  lane1:
    switch: s_lane1
    show_tokens:
      light: l_lane1
```

In the test run, `l_lane1` was off at the start of the game, turned white when the lane was hit, and was still white on
ball 2, because the shot's state belongs to the player.

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base

machine:
  balls_installed: 1

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_target:
    number:
  s_lane1:
    number:
  s_lane2:
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

lights:
  l_target:
    number:
  l_lane1:
    number:
    tags: lane_lights
  l_lane2:
    number:
    tags: lane_lights
  l_start:
    number:

shows:
  attract_sweep:
    - duration: 500ms
      lights:
        l_lane1: white
        l_lane2: off
    - duration: 500ms
      lights:
        l_lane1: off
        l_lane2: white

show_player:
  mode_attract_started: attract_sweep
  mode_attract_stopped:
    attract_sweep: stop

virtual_platform_start_active_switches: s_trough1
```

`shows/flash_light.yaml` is the show file above.

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
    show_tokens:
      light: l_lane1
  lane2:
    switch: s_lane2
    show_tokens:
      light: l_lane2

show_player:
  s_target_active:
    flash_light:
      loops: 2
      show_tokens:
        light: l_target
      events_when_completed: target_flash_done
  ball_started:
    start_pulse:
      loops: 0
      show_tokens:
        light: l_start

shows:
  start_pulse:
    - time: 0
      lights:
        (light): blue-f200ms
    - time: 1s
      lights:
        (light): off
      events: start_pulse_done
    - time: 2s
```
