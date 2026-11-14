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

### How tokens work

Any name in parentheses is a token, and you choose the names. A token can stand for a key (which light) or a value
(which color), and a show can have as many as it needs:

`shows/blink.yaml`:

```yaml
#show_version=6
- duration: 250ms
  lights:
    (light): (color)
- duration: 250ms
  lights:
    (light): off
```

Whoever plays the show supplies a value for each token under `show_tokens` (the [`show_player`](#playing-shows)
example below passes `light` and `color`). MPF copies the show's steps and swaps every `(light)` and `(color)` for
those values. The same show can run several times at once with different values, which is how every lane shot below
lights its own lamp from one `on` show.

A token can also be part of a longer name:

`shows/lane_number.yaml`:

```yaml
#show_version=6
- duration: -1
  lights:
    l_lane(num): green
```

Played with `num: 2`, this turned `l_lane2` green in the test run.

What happens when the tokens don't match:

| Mistake | Result in the test run |
|---|---|
| Passing a token the show doesn't use (a typo such as `colour`) | The show doesn't play: `Token mismatch while playing show "blink". Tokens expected: {'light', 'color'}. Tokens submitted: {'light', 'colour'}` (`Show.play`). |
| Leaving out a token used as a **light name** | No error. That line of the step is skipped, so nothing lights (`LightPlayer.play` ignores light names still in parentheses). |
| Leaving out a token used as a **color** | Error `Invalid color (color)`, code `CFE-light_player-1`. |

### Tags: many lights at once

`tags:` on a light is a list of labels you make up, comma-separated if there are several. The machine config on this
page gives both lane lights the tag `lane_lights`:

```yaml
lights:
  l_lane1:
    number:
    tags: lane_lights
  l_lane2:
    number:
    tags: lane_lights
```

Wherever a show names a light, it can name a tag instead, and the step then sets every light with that tag. MPF looks
for a light with that name first and only then for a tag (`LightPlayer._light_named_color`), so don't give a tag the
same name as a light. A name that is neither is an error: `Could not find a lights device with name or tag l_nope`, code
`CFE-light_player-101`.

A tag directly in a step:

```yaml
shows:
  lanes_orange:
    - duration: -1
      lights:
        lane_lights: orange
```

In the test run this turned `l_lane1` and `l_lane2` orange and left `l_target` alone.

A tag as a token value works the same way. This flashes both lane lights red with the `blink` show above:

```yaml
show_player:
  flash_lanes:
    blink:
      loops: 2
      show_tokens:
        light: lane_lights
        color: red
```

In the test run both lights flashed red together three times. Tags are the easy way to light a group (all the lane
lights, every light in a bank) without listing each one. Switches carry tags too, for a different job: see
[switch events](/build/switches-and-coils/#events-a-switch-posts).

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

MPF's own `mpfconfig.yaml` defines shows you can use with a `light` token (a light name or a tag):

| Show | Tokens | What it does |
|---|---|---|
| `on` | `light` | The light's `default_on_color`, held until stopped. |
| `off` | `light` | Off, held until stopped. |
| `flash` | `light` | One second on, one second off. |
| `led_color` | `light`, `color` | The color, held until stopped. |
| `flash_color` | `light`, `color` | One second in the color, one second off. |

These names are taken, so don't name your own show `flash_color` (or any of the others): MPF stops at startup with
`Duplicate show flash_color`.

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

The `shows/` folder holds the three show files above: `flash_light.yaml`, `blink.yaml` and `lane_number.yaml`.

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
