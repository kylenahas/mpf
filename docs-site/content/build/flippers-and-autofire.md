---
title: "Flippers, slingshots and pop bumpers"
weight: 4
summary: "Flippers (single and dual wound, EOS), autofire coils for slingshots and pop bumpers, and kickbacks."
verified: "MPF 0.82.0.dev0, virtual and smart virtual platforms"
---

Flippers, slingshots and pop bumpers must react the instant a switch closes. Going through MPF's event loop (as in
[wiring a switch to a coil](/build/switches-and-coils/#wiring-a-switch-to-a-coil)) is too slow for them. Instead,
these devices write a **hardware rule** to the controller, such as "when this switch closes, pulse that coil". The
controller then fires the coil on its own, and MPF only turns the rule on and off.

{{< tip >}}
**Verified.** The complete config at the end of this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase`. The
virtual platforms record hardware rules but do not fire coils from them, so the test checks which rules are written
and when. `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## When the rules are active

Flippers and autofire coils have the same defaults (`config_spec.yaml`):

| Setting | Default |
|---|---|
| `enable_events` | `ball_started` |
| `disable_events` | `ball_will_end`, `service_mode_entered` |

So in attract mode there are no rules and the flipper buttons do nothing. When a ball starts, every rule is written;
when the ball ends, they are removed. Kickbacks are the exception: `enable_events` has no default, so a kickback
stays off until you enable it.

## Flippers

### Single-wound flipper

One coil, pulsed at full power and then held at reduced power while the button is down:

```yaml
coils:
  c_left_flipper:
    number:
    default_pulse_ms: 30
    default_hold_power: 0.25

flippers:
  left_flipper:
    main_coil: c_left_flipper
    activation_switch: s_left_flipper
```

The rule written is `pulse_on_hit_and_enable_and_release`: pulse on press, then hold, then off on release. The hold
needs a hold power on the coil (`default_hold_power`, `max_hold_power` or `allow_enable`). Without one, MPF stops when
the first ball starts with "Cannot enable driver with hold_power 0.0" (checked in the test run).

### Dual-wound flipper with an EOS switch

Two windings: a strong main (power) winding and a weak hold winding. The **EOS** (end of stroke) switch closes when
the flipper is fully up.

```yaml
coils:
  c_right_flipper_main:
    number:
    default_pulse_ms: 30
  c_right_flipper_hold:
    number:
    allow_enable: true

flippers:
  right_flipper:
    main_coil: c_right_flipper_main
    hold_coil: c_right_flipper_hold
    activation_switch: s_right_flipper
    eos_switch: s_right_flipper_eos
    use_eos: true
```

Two rules are written:

- The hold coil: pulse and hold while the button is down (`pulse_on_hit_and_enable_and_release`).
- The main coil: pulse on press, and cut off when the EOS switch closes or the button is released
  (`pulse_on_hit_and_release_and_disable`, on both the button and the EOS switch).

`allow_enable: true` on the hold coil is right here because a hold winding is designed to stay on.

Without `use_eos: true` (or with no EOS switch), the main coil is simply pulsed for `default_pulse_ms`. With
`repulse_on_eos_open: true`, MPF pulses again if the EOS switch opens while the button is held, for example when a
ball knocks the flipper down; `eos_active_ms_before_repulse` (default 500 ms) is how long EOS must have been closed
first. If the platform cannot do this in hardware, MPF does it in software (`SoftwareEosRepulseManager` in
`mpf/core/platform_controller.py`).

### Other flipper settings

| Setting | What it does |
|---|---|
| `main_coil_overwrite`, `hold_coil_overwrite` | Override `pulse_ms`, `pulse_power`, `hold_power` or `recycle` for this flipper only, without changing the coil. |
| `power_setting_name` | Multiply the main coil's pulse by an operator setting (from `settings:`), for adjustable flipper strength. The base is `main_coil_overwrite: pulse_ms`, or if that is not set, `mpf: default_pulse_ms` (10 ms), **not** the coil's `default_pulse_ms` (`Flipper._get_pulse_ms`). Set `main_coil_overwrite: pulse_ms` when you use it. |
| `sw_flip_events`, `sw_release_events` | Flip from software, as if the button were pressed or released. |
| `include_in_ball_search` | Default `false`. Set `true` to let ball search flip this flipper. |

## Slingshots and pop bumpers

Both are **autofire coils**: when the switch closes, pulse the coil.

```yaml
autofire_coils:
  left_slingshot:
    coil: c_left_sling
    switch: s_left_sling
  pop_bumper:
    coil: c_pop
    switch: s_pop
```

- The pulse length is the coil's `default_pulse_ms`; `coil_overwrite: {pulse_ms: ...}` changes it for this device only.
- Recycle (the controller's cool-down before the coil can fire again) is **on** unless the coil sets
  `default_recycle: false` or `coil_overwrite` sets `recycle: false` (`AutofireCoil.enable`).
- `reverse_switch: true` fires when the switch *opens*, for opto switches.
- `coil_pulse_delay` delays the pulse after the switch closes, on platforms that support it.
- Each hit tells the playfield a ball is there, so **do not** tag these switches `playfield_active` (see
  [below](#switches-that-report-the-ball-themselves)).

### Stopping a stuck pop bumper

A ball trapped against a pop bumper can fire it over and over. Three settings switch the device off for a while when
that happens:

```yaml
autofire_coils:
  pop_bumper:
    coil: c_pop
    switch: s_pop
    timeout_watch_time: 1s
    timeout_max_hits: 10
    timeout_disable_time: 2s
```

`timeout_max_hits` hits within `timeout_watch_time` disable the device for `timeout_disable_time`, then it turns back
on (`AutofireCoil._hit`).

{{< warn >}}
**Does not work as configured in MPF 0.82.0.dev0.** `timeout_watch_time` is converted from milliseconds to seconds
twice (`mpf/devices/autofire.py`, `_initialize` and `_hit`), so the window is 1000 times shorter than written. In the
test run, 12 hits 50 ms apart did not disable the pop bumper; only hits at the same instant did. MPF's own test
(`test_Autofire.py::test_timeout`) sends all hits at the same instant, so it does not catch this.
{{< /warn >}}

## Kickbacks

A kickback is an autofire coil in an outlane that is lit and unlit by the game. It posts
`kickback_<name>_fired` each time it fires (`mpf/devices/kickback.py`), which you can use to turn it off:

```yaml
kickbacks:
  left_kickback:
    coil: c_kickback
    switch: s_left_outlane
    enable_events: ball_started, light_kickback
    disable_events: kickback_left_kickback_fired, ball_will_end, service_mode_entered
```

In the test run, the kickback was on when the ball started, fired once and removed its rule, and came back on when
`light_kickback` was posted. Setting `disable_events` replaces the default list, so `ball_will_end` and
`service_mode_entered` are repeated here.

## Switches that report the ball themselves

Some devices tell the playfield a ball is there each time their switch is hit, so their switches must **not** have
the `playfield_active` tag. With the tag, MPF stops at startup with "Remove the redundant 'playfield_active' tag from
that switch". The error code names the device type:

| Device | Error code |
|---|---|
| `autofire_coils` (slingshots, pop bumpers) | `CFE-autofire-1` |
| `kickbacks` | `CFE-kickback-1` |
| `drop_targets` | `CFE-drop_target-1` |

Each was checked in a test run with the tag added: the kickback in
[Ball save, kickback and outlanes](/examples/ball-in-play/ball-save-and-kickback/), the drop targets in
[Drop target bank and extra ball](/examples/ball-in-play/drop-targets-extra-ball/), and the pop bumpers in
[Pop bumpers and super pops](/examples/scoring/super-pops/). Other tags, such as `drop_target` or `pop` for `sw_` events,
are fine.

## The complete config

```yaml
#config_version=6

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
  s_right_flipper:
    number:
  s_right_flipper_eos:
    number:
  s_left_sling:
    number:
  s_pop:
    number:
  s_left_outlane:
    number:

coils:
  c_trough_eject:
    number:
  c_left_flipper:
    number:
    default_pulse_ms: 30
    default_hold_power: 0.25
  c_right_flipper_main:
    number:
    default_pulse_ms: 30
  c_right_flipper_hold:
    number:
    allow_enable: true
  c_left_sling:
    number:
    default_pulse_ms: 15
  c_pop:
    number:
    default_pulse_ms: 20
  c_kickback:
    number:
    default_pulse_ms: 40

ball_devices:
  bd_trough:
    ball_switches: s_trough1
    eject_coil: c_trough_eject
    tags: trough, drain, home

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

flippers:
  left_flipper:
    main_coil: c_left_flipper
    activation_switch: s_left_flipper
  right_flipper:
    main_coil: c_right_flipper_main
    hold_coil: c_right_flipper_hold
    activation_switch: s_right_flipper
    eos_switch: s_right_flipper_eos
    use_eos: true

autofire_coils:
  left_slingshot:
    coil: c_left_sling
    switch: s_left_sling
  pop_bumper:
    coil: c_pop
    switch: s_pop
    timeout_watch_time: 1s
    timeout_max_hits: 10
    timeout_disable_time: 2s

kickbacks:
  left_kickback:
    coil: c_kickback
    switch: s_left_outlane
    enable_events: ball_started, light_kickback
    disable_events: kickback_left_kickback_fired, ball_will_end, service_mode_entered

virtual_platform_start_active_switches: s_trough1
```

What the test run showed:

1. In attract mode no hardware rules are written.
2. When the ball starts, these rules are written:

   | Switch | Coil | Rule |
   |---|---|---|
   | `s_left_flipper` | `c_left_flipper` | pulse on hit, enable, release |
   | `s_right_flipper` | `c_right_flipper_hold` | pulse on hit, enable, release |
   | `s_right_flipper`, `s_right_flipper_eos` | `c_right_flipper_main` | pulse on hit, release, disable on EOS |
   | `s_left_sling` | `c_left_sling` | pulse on hit |
   | `s_pop` | `c_pop` | pulse on hit |
   | `s_left_outlane` | `c_kickback` | pulse on hit |

3. A hit on `s_left_outlane` fires the kickback, which disables itself; `light_kickback` turns it back on.
4. Without `default_hold_power` on `c_left_flipper`, the game stops at `ball_started` with "Cannot enable driver with
   hold_power 0.0".
