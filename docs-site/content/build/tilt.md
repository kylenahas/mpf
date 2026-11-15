---
title: "Tilt"
weight: 11
summary: "MPF's tilt mode: warning, tilt and slam tilt switches, what a tilt shuts off, multiball, ball saves and extra balls, settle time, and changing the settings."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

A tilt is how a pinball machine punishes a player who shakes or lifts it too hard: the ball in play is lost, and with
it any bonus. MPF does this with a built-in `tilt` mode. This page covers what the mode does, switch by switch, and
how a tilt interacts with ball saves, multiballs and extra balls. For a complete rule built on it, see the
[Tilt with warnings](/examples/ball-in-play/tilt/) example.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart virtual
platform. The behaviour described below is from those runs, and `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## Turning tilt on

The `tilt` mode comes with MPF, but like the other built-in modes it only runs if it's in the `modes:` list:

```yaml
modes:
  - base
  - tilt
```

It isn't a game mode: it starts when the machine starts (`start_events: machine_reset_phase_3`) and runs all the time,
in attract mode too, at priority 1000000 (`mpf/modes/tilt/config/tilt.yaml`).

## The switches

The mode finds its switches by tag. A machine can have any number of each.

```yaml
switches:
  s_plumb_bob:
    number:
    tags: tilt_warning
  s_playfield_tilt:
    number:
    tags: tilt
  s_slam_tilt:
    number:
    tags: slam_tilt
```

| Tag | Usually | What a hit does during a game |
|---|---|---|
| `tilt_warning` | The plumb bob, and sometimes a ball roll tilt | A warning. The hit that reaches the warning limit tilts instead. |
| `tilt` | A switch that should never close in normal play | Tilts at once, without warnings. |
| `slam_tilt` | The coin door slam switch | Tilts and ends the whole game. |

Outside a game, the mode ignores warning and tilt switches. A slam tilt switch still posts `slam_tilt`, but there's
no game to end. In the test run, hitting all three in attract mode posted only `slam_tilt`.

## Warnings

Each warning adds 1 to the player variable `tilt_warnings` and posts two events:

| Event | Arguments |
|---|---|
| `tilt_warning` | `warnings`, the count so far, and `warnings_remaining` |
| `tilt_warning_1`, `tilt_warning_2`, ... | none; the number is in the name |

With the default `warnings_to_tilt: 3`, the first two hits are warnings and the third tilts. A swinging plumb bob
can close several times from one nudge; the [tilt debounce](#tilt-debounce) makes those count as one warning.

Warnings belong to the player and go back to 0 when the ball ends (`reset_warnings_events: ball_will_end`). A drain
that a ball save catches doesn't end the ball, so the warnings stay: in the test run, a player with two warnings
drained during the ball save, got the ball back, and tilted on the next hit of the bob. After a drain with the save
over, ball 2 started with 0 warnings, and the next hit was warning 1.

### Tilt debounce

After a nudge, the plumb bob swings and can touch its ring several times in quick succession. The tilt debounce
ignores warning-switch hits that come too soon after the last warning, so one nudge is one warning. MPF calls the
setting `multiple_hit_window`, and its default is 300 ms.

To change it, add the tilt mode's config to your machine as `modes/tilt/config/tilt.yaml`, with only the setting you
change (see [Changing a built-in mode](/build/modes/#changing-a-built-in-mode)):

```yaml
#config_version=6

tilt:
  multiple_hit_window: 500ms
```

The window is measured from the last hit that **counted** as a warning, not from the last hit of the switch
(`Tilt._tilt_warning_switch_handler`). With 500 ms in the test run:

| Bob hits at | Warnings | Why |
|---|---|---|
| 0 s | 1 | |
| 0.4 s | 1 | 0.4 s after the last warning: ignored |
| 0.8 s | 2 | 0.8 s after the last warning, although only 0.4 s after the previous hit |

With the default 300 ms, the hit at 0.4 s would have been the second warning.

A longer window forgives more swinging but also lets a player nudge twice in quick succession with only one warning.
The debounce only applies to switches tagged `tilt_warning`. A warning sent with `tilt_warning_events` always counts,
and so does a hit of a `tilt` or `slam_tilt` switch. The value is read when the tilt mode starts, so restart MPF after
changing it.

## What a tilt does

In the test run, a hit of the `tilt` switch did all of this at once:

1. **Posts `tilt`** and marks the game as tilted.
2. **Ends the ball straight away.** The mode calls the game's end of ball, which posts `ball_will_end`, so every
   mode that stops at the end of the ball stops now. Their scoring stops with them: a target hit after the tilt scored
   nothing.
3. **Turns the flippers and autofire coils off.** Their default `disable_events` include `ball_will_end`, so a
   flipper button or slingshot did nothing after the tilt.
4. **Turns the ball save off**, for the same reason (`ball_saves` `disable_events`). A tilt during the ball save
   wasn't saved.
5. **Skips the bonus.** The built-in `bonus` mode does nothing when the game is tilted (`Bonus.mode_start`); see
   [the example](/examples/ball-in-play/tilt/#what-happened-in-the-test-run).
6. **Waits for every ball on the playfield to drain.** The ball doesn't end until all of them are back in the trough.
7. **Waits for the plumb bob to settle.** After the last ball drains, the mode waits until `settle_time` (5 s) has
   passed since the last hit of a warning switch, so a still-swinging bob can't tilt the next ball.
8. **Posts `tilt_clear`**, then the ball ends as usual and the next one starts.

The flippers and autofire coils come back on with the next ball (`enable_events: ball_started`).

### Tilting during a multiball

All the balls in play have to drain before the ball ends. In the test run, a tilt during a two-ball multiball left
both balls on the playfield. The first drain ended the multiball (`multiball_main_mb_ended`), but the game stayed
tilted, still waiting, ten seconds later. Only the second drain posted `tilt_clear` and started the next ball.

### Extra balls

A tilt ends the ball, not the turn. In the test run, a player who had an extra ball and tilted played the extra ball
next: the same player, ball 1 again.

A slam tilt also forfeits extra balls: the game ends after the ball (`Game._run`). In the test run, a player
with an extra ball waiting hit the slam tilt, and the drain posted `ball_ended` and `game_ended`, with no extra ball.

## The settings

The mode's settings are in its own config, `mpf/modes/tilt/config/tilt.yaml`, and the `tilt:` section of MPF's config
spec:

| Setting | Default | What it does |
|---|---|---|
| `warnings_to_tilt` | `3` | The hit that brings the player's warnings to this number tilts. |
| `multiple_hit_window` | `300ms` | The [tilt debounce](#tilt-debounce): warning-switch hits this soon after the last warning are ignored. |
| `settle_time` | `5s` | After a tilt, the next ball waits until no warning switch has been hit for this long. |
| `reset_warnings_events` | `ball_will_end` | When the player's warnings go back to 0. |
| `tilt_warnings_player_var` | `tilt_warnings` | The player variable that counts warnings. |
| `tilt_warning_switch_tag`, `tilt_switch_tag`, `slam_tilt_switch_tag` | `tilt_warning`, `tilt`, `slam_tilt` | The tags the mode looks for. |
| `tilt_events`, `tilt_warning_events`, `tilt_slam_tilt_events` | none | Events that tilt, warn or slam tilt like a switch hit would. A warning from an event isn't debounced (`Tilt.mode_start`). |

To change them, add `modes/tilt/config/tilt.yaml` to your machine with a `tilt:` section holding only what you
change; see [Changing a built-in mode](/build/modes/#changing-a-built-in-mode), which does this with
`warnings_to_tilt: 2`.

## Showing it to the player

Use the events above for lights, sounds and screens: `tilt_warning` for a "WARNING" flash, `tilt` for the tilt
display, and `tilt_clear` to remove it. MPF's own `tilt.yaml` already has `slide_player` entries for a media
controller: a `tilt` slide with the text `WARNING` on the first warning, `DANGER` on the second, and `TILT` on a tilt,
removed on `tilt_clear`.


## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - tilt

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
  s_left_flipper:
    number:
  s_left_sling:
    number:
  s_target:
    number:
    tags: playfield_active
  s_scoop:
    number:
    tags: playfield_active
  s_eb_target:
    number:
    tags: playfield_active
  s_plumb_bob:
    number:
    tags: tilt_warning
  s_playfield_tilt:
    number:
    tags: tilt
  s_slam_tilt:
    number:
    tags: slam_tilt

coils:
  c_trough_eject:
    number:
  c_left_flipper:
    number:
    default_pulse_ms: 30
    default_hold_power: 0.25
  c_left_sling:
    number:
    default_pulse_ms: 20

ball_devices:
  bd_trough:
    ball_switches: s_trough1, s_trough2, s_trough3
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 2s
    tags: trough, drain, home

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

flippers:
  left_flipper:
    main_coil: c_left_flipper
    activation_switch: s_left_flipper

autofire_coils:
  left_sling:
    coil: c_left_sling
    switch: s_left_sling

virtual_platform_start_active_switches: s_trough1, s_trough2, s_trough3
```

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

ball_saves:
  start_save:
    active_time: 10s
    enable_events: mode_base_started
    timer_start_events: balldevice_bd_trough_ball_eject_success

multiballs:
  main_mb:
    ball_count: 2
    start_events: s_scoop_active
    shoot_again: 0s

extra_balls:
  target_eb:
    award_events: s_eb_target_active

variable_player:
  s_target_active:
    score: 100
```
