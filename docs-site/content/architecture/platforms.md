---
title: "Platforms and hardware rules"
weight: 8
summary: "How MPF talks to hardware: platforms, choosing them per device type, hardware rules that fire flippers and slingshots without waiting for MPF, and what the virtual and smart virtual platforms do."
verified: "MPF 0.82.0.dev0, virtual and smart virtual platforms"
---

MPF doesn't talk to coils and switches directly. A **platform** does: a Python class that knows one kind of hardware,
such as FAST's controllers, and turns MPF's requests ("pulse this coil for 20 ms") into what that hardware
understands. This page explains how platforms are chosen, what a **hardware rule** is, and what the two virtual
platforms used for testing do and don't do.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase`, once on the virtual and
once on the smart virtual platform; the rules and ball movements below are from those runs. No real hardware was
used. `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## Choosing a platform

The `hardware:` section names the platform:

```yaml
hardware:
  platform: fast
```

The default is `virtual` (`config_spec.yaml`). The names map to classes in MPF's own config, under `mpf: platforms:`
in `mpfconfig.yaml` (`fast: mpf.platforms.fast.fast.FastHardwarePlatform`, and so on).

A machine can mix platforms. `hardware:` has a setting per kind of device (`switches`, `coils`, `lights`,
`servo_controllers`, `segment_displays`, ...), each `default` unless set, and a single device can name its own with a
`platform:` setting (`MachineController.get_platform_sections`). For example, lights on a separate LED controller
while everything else is on FAST:

```yaml
hardware:
  platform: fast
  lights: fadecandy
```

The command line overrides all of it: `mpf game -x` uses the virtual platform for every device, and `-X` the smart
virtual platform. That's how a machine configured for real hardware runs on a computer with no hardware attached.

[Connecting FAST hardware](/build/fast-hardware/) covers the FAST platform's own settings.

## Hardware rules

Flippers and slingshots have to react within a few milliseconds. Waiting for a switch change to travel to the
computer, through MPF and back to the coil would be too slow, so MPF doesn't do it that way. When a flipper or an
autofire coil is enabled, MPF writes a **hardware rule** into the controller: "when this switch closes, fire this coil
like this". The controller then fires the coil on its own. MPF still sees the switch change and can score it, but the
coil doesn't wait for it.

The kinds of rule, and which device uses each (`PlatformController` in `mpf/core/platform_controller.py`;
`AutofireCoil.enable` and `Flipper.enable` in `mpf/devices/`):

| Rule | What the controller does | Used by |
|---|---|---|
| `pulse_on_hit` | Fire once when the switch closes. | Autofire coils: slingshots, pop bumpers; kickbacks |
| `delayed_pulse_on_hit` | Fire once, after a delay. | Autofire coils with `coil_pulse_delay` |
| `pulse_on_hit_and_enable_and_release` | Pulse, then hold at reduced power until the switch opens. | A single-wound flipper; the hold coil of a dual-wound flipper |
| `pulse_on_hit_and_release` | Pulse, and stop if the switch opens first. | A dual-wound flipper's main coil |
| `pulse_on_hit_and_release_and_disable` | Pulse until an end-of-stroke switch closes. | A dual-wound flipper's main coil with `use_eos` |
| `pulse_on_hit_and_enable_and_release_and_disable` | Pulse until end-of-stroke, then hold. | A single-wound flipper with `use_eos` |

In the test runs, the machine below had no rules in attract mode. When the ball started, the single-wound flipper had
`pulse_on_hit_and_enable_and_release` and the slingshot `pulse_on_hit`. The devices put them there with
`enable_events: ball_started`, their default.

Turning a flipper or autofire coil off means removing its rule from the controller (`clear_hw_rule` in their `disable`
methods). That's what a [tilt](/build/tilt/#what-a-tilt-does) does to make the flipper buttons stop working.

## The virtual platforms

Two platforms have no hardware behind them. Both keep switch states, coil states and the rules in memory, so MPF can
run anywhere.

- **`virtual`** (`mpf game -x`) only records. A coil that's pulsed is marked as pulsed, and nothing else happens. A
  ball device's eject coil doesn't move a ball, so the ball never leaves.
- **`smart_virtual`** (`mpf game -X`) also acts out what the hardware would do (`mpf/platforms/smart_virtual.py`):
  pulsing a ball device's eject coil moves a ball to the target device and updates both devices' switches, a drop
  target bank's reset coil raises its targets, and score reels advance.

Neither platform runs hardware rules: they store the rule, but pressing the flipper button doesn't fire the flipper
coil.

In the test runs, the trough's eject coil was pulsed on both platforms. On `virtual`, 5 seconds later the trough still
had both balls and the playfield none; on `smart_virtual`, one ball had moved to the playfield. On both, closing the
slingshot switch left its coil `disabled`: the rule was there, but nothing ran it.

For testing rules, the smart virtual platform is the one to use: a game can't get past the first ball without balls
moving. The [testing guide](/architecture/testing/#a-test-file) sets it with `get_platform`.

## Writing a platform

A platform for new hardware is a class that implements the interfaces in `mpf/platforms/interfaces/` for what the
hardware can do (switches, drivers, lights, servos, ...) and the rule methods above, and is added to `mpf: platforms:`
under a name. The existing platforms in `mpf/platforms/` are the best reference; the virtual platform is the smallest
complete one. This wasn't exercised for this page.

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

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
  s_left_flipper:
    number:
  s_left_sling:
    number:

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
    ball_switches: s_trough1, s_trough2
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

virtual_platform_start_active_switches: s_trough1, s_trough2
```
