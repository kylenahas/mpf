---
title: "Polishing the game"
weight: 12
summary: "The details that make a machine feel finished: a ball save timed from the plunge, hurry-up and grace periods with a shoot-again light, early saves, multiball saves, and ball search that leaves a cradled ball alone."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

A machine can have all its rules working and still feel like a prototype. Production games have a layer of small
courtesies on top: the ball save doesn't tick away while the ball sits in the shooter lane, a light warns that it's
about to run out, a ball that drains a moment too late is still saved, and a ball cradled on a flipper doesn't set off
the coils. This page builds that layer for a machine with a plunger lane, two flippers and a two-ball multiball.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart virtual
platform. The times and light patterns below are from those runs, and `docs-site/verify/test_guides.py` repeats the
checks.
{{< /tip >}}

## A ball save that feels fair

```yaml
ball_saves:
  start_save:
    active_time: 10s
    hurry_up_time: 3s
    grace_period: 3s
    enable_events: mode_base_started
    timer_start_events: balldevice_bd_plunger_ball_eject_success
    early_ball_save_events: s_left_outlane_active, s_right_outlane_active
```

The [ball saves guide](/build/ball-saves-and-extra-balls/#ball-saves) explains each setting. These are the choices that
make it feel right.

### Start the clock at the plunge

The save is switched on when the ball starts, but its 10 seconds only start once the ball has left the plunger lane
and reached the playfield (`timer_start_events: balldevice_bd_plunger_ball_eject_success`). A player who takes their
time at the plunger, or waits for a skill shot, doesn't lose any of the save.

In the test run, the ball waited 20 seconds in the lane: `ball_save_start_save_enabled` was posted at the start of the
ball, but nothing else until the launch button was pressed. The timer started when the ball reached the playfield.

{{< note >}}
Use the eject success of the device that puts the ball on the playfield: the plunger lane here, the trough if it ejects
straight to the playfield. Not `playfield_active`, which can be skipped (see the
[ball saves guide](/build/ball-saves-and-extra-balls/#the-timeline)).
{{< /note >}}

### Warn before it runs out, and forgive a late drain

`hurry_up_time: 3s` posts `ball_save_start_save_hurry_up` 3 seconds before the save ends, and `grace_period: 3s` keeps
saving for 3 seconds after it has officially ended. The usual way to show this is a shoot-again light that flashes
while the save is on, flashes faster in the hurry-up, and goes out when the time is up. The grace period then saves a
ball that was already on its way down when the light went out: the player is never told the save is over and then
loses the ball anyway.

```yaml
show_player:
  ball_save_start_save_timer_start:
    save_light:
      show: flash
      show_tokens:
        light: l_shoot_again
  ball_save_start_save_hurry_up:
    save_light:
      show: flash
      speed: 4
      show_tokens:
        light: l_shoot_again
  ball_save_start_save_grace_period:
    save_light: stop
  ball_save_start_save_disabled:
    save_light: stop
```

`save_light` is a name for this use of the built-in `flash` show (`show: flash`), so the later entries can replace or
stop it. Playing it again with `speed: 4` replaces the slow flash with a fast one. `ball_save_start_save_grace_period`
is posted when the 10 seconds are up, and the light goes out there; the `disabled` entry covers a save that ends
another way, such as being used.

Sampled every quarter second from when the timer started, in the test run (`#` on, `.` off):

```text
0 s                         7 s hurry   10 s grace  13 s
###....####....####....#####.#.#.#.#.#..................
```

A drain about 11 seconds after the timer started, with the light already out, was saved
(`ball_save_start_save_saving_ball`). A drain about 14 seconds after, past the grace period, ended the ball.

### Save it before it drains

`early_ball_save_events` saves the ball as soon as it enters an outlane, so the new ball is on its way before the old
one reaches the trough. In the test run, the right outlane during the save posted `saving_ball` with
`early_save: True`. If an outlane has a kickback, leave it out of this list; see
[Ball save, kickback and outlanes](/examples/ball-in-play/ball-save-and-kickback/#the-ball-save).

### Launch the saved ball for the player

A saved ball goes back through the plunger lane, and `auto_launch` (default `true`) fires it without waiting for the
launch button. In the test run, the saved ball left the lane on its own. Only the ball served at the start of each
ball waits for the player (see [the plunger lane](/build/ball-devices/#the-plunger-lane)).

## A multiball save

A multiball has its own save, `shoot_again`, with the same two courtesies:

```yaml
multiballs:
  main_mb:
    ball_count: 2
    start_events: s_scoop_active
    shoot_again: 10s
    hurry_up_time: 3s
    grace_period: 3s
```

It posts `multiball_main_mb_hurry_up` 7 seconds in and `multiball_main_mb_grace_period` at 10 seconds, so the same kind
of `show_player` entries can drive a light. In the test run, a drain 11.5 seconds into the multiball was still saved
(`multiball_main_mb_shoot_again`), and the next drain, after the grace period, ended the multiball.

## Ball search that leaves the player alone

A ball can get stuck on a production machine: wedged behind a post, or resting on a dead switch. Ball search fires
coils to free it after no playfield switch has been hit for a while. It's off by default, so turn it on:

```yaml
playfields:
  playfield:
    default_source_device: bd_plunger
    tags: default
    enable_ball_search: true
```

The defaults already handle the case that matters most to the player: holding the ball on a flipper to aim a shot.
MPF's own config defines a `flipper_cradle` timed switch, posted when a switch tagged `left_flipper` or `right_flipper`
has been held for 3 seconds, and the playfield's `ball_search_block_events` defaults to `flipper_cradle`. So tag the
flipper buttons:

```yaml
switches:
  s_left_flipper:
    number:
    tags: left_flipper
  s_right_flipper:
    number:
    tags: right_flipper
```

In the test run:

- After 16 seconds with no switch hit, ball search had started (`ball_search_started`, `ball_search_phase_1`), and the
  next target hit stopped it (`ball_search_stopped`).
- With the left flipper button held for 30 seconds, `flipper_cradle` was posted and no search started.
- After the button was released, the search started 15 seconds later (`ball_search_timeout`), not at once.
- While the ball waited 20 seconds in the plunger lane, no search started: there was no ball on the playfield.

The [ball devices guide](/build/ball-devices/#ball-search) has the search phases and the other settings.

## More polish elsewhere

| Courtesy | Where |
|---|---|
| Let the player skip a long bonus count with both flipper buttons | [End-of-ball bonus](/examples/scoring/end-of-ball-bonus/) (`flipper_cancel`) |
| Don't let a swinging plumb bob tilt the next ball | [Tilt](/build/tilt/#what-a-tilt-does) (`settle_time`) |
| Count a swinging plumb bob as one warning | [Tilt](/build/tilt/#warnings) (`multiple_hit_window`) |
| A multiball that releases all its locked balls at once | [Multiball and ball locks](/build/multiball/#releasing-all-three-balls) |
| Keep an unfinished hurry-up for the player's next ball | [Modes](/build/modes/#a-mode-that-survives-a-drain-hurry-up) (`restart_on_next_ball`) |


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
  s_plunger_lane:
    number:
  s_launch:
    number:
    tags: launch
  s_left_flipper:
    number:
    tags: left_flipper
  s_right_flipper:
    number:
    tags: right_flipper
  s_left_sling:
    number:
  s_left_outlane:
    number:
    tags: playfield_active
  s_right_outlane:
    number:
    tags: playfield_active
  s_target:
    number:
    tags: playfield_active
  s_scoop:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:
  c_plunger:
    number:
    default_pulse_ms: 30
  c_left_flipper:
    number:
    default_pulse_ms: 30
    default_hold_power: 0.25
  c_right_flipper:
    number:
    default_pulse_ms: 30
    default_hold_power: 0.25
  c_left_sling:
    number:
    default_pulse_ms: 20

lights:
  l_shoot_again:
    number:

ball_devices:
  bd_trough:
    ball_switches: s_trough1, s_trough2, s_trough3
    eject_coil: c_trough_eject
    eject_targets: bd_plunger
    tags: trough, drain, home
  bd_plunger:
    ball_switches: s_plunger_lane
    eject_coil: c_plunger
    player_controlled_eject_event: sw_launch
    eject_targets: playfield
    eject_timeouts: 3s

playfields:
  playfield:
    default_source_device: bd_plunger
    tags: default
    enable_ball_search: true

flippers:
  left_flipper:
    main_coil: c_left_flipper
    activation_switch: s_left_flipper
  right_flipper:
    main_coil: c_right_flipper
    activation_switch: s_right_flipper

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
    hurry_up_time: 3s
    grace_period: 3s
    enable_events: mode_base_started
    timer_start_events: balldevice_bd_plunger_ball_eject_success
    early_ball_save_events: s_left_outlane_active, s_right_outlane_active

show_player:
  ball_save_start_save_timer_start:
    save_light:
      show: flash
      show_tokens:
        light: l_shoot_again
  ball_save_start_save_hurry_up:
    save_light:
      show: flash
      speed: 4
      show_tokens:
        light: l_shoot_again
  ball_save_start_save_grace_period:
    save_light: stop
  ball_save_start_save_disabled:
    save_light: stop

multiballs:
  main_mb:
    ball_count: 2
    start_events: s_scoop_active
    shoot_again: 10s
    hurry_up_time: 3s
    grace_period: 3s

variable_player:
  s_target_active:
    score: 100
```
