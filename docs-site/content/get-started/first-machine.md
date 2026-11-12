---
title: "Your first machine"
weight: 3
summary: "A startable three-ball game on virtual hardware: start button, trough and playfield."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

The goal: a machine you can start a game on, using no hardware. You will add a start button, a trough that holds the
balls, and a playfield. Then you will swap the virtual hardware for a FAST controller.

{{< tip >}}
**Verified.** The config on this page was run on MPF 0.82.0.dev0 with `mpf game -X`, and driven through a full game
with MPF's own test harness (`MpfGameTestCase`): it boots into `attract`, a press of `s_start` starts a game, three
balls are served and drained, and the machine returns to `attract`.
{{< /tip >}}

## 1. Start from `mpf init`

```bash
mpf init first_machine
cd first_machine
```

You now have `config/config.yaml` listing the modes `attract` and `base` (see [the machine folder](/get-started/machine-folder/)).

## 2. Describe the hardware

Replace the contents of `config/config.yaml` with:

```yaml
#config_version=6

modes:
  - attract
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

coils:
  c_trough_eject:
    number:

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

ball_devices:
  bd_trough:
    ball_switches: s_trough1, s_trough2, s_trough3
    eject_coil: c_trough_eject
    eject_targets: playfield
    tags: trough, drain, home

virtual_platform_start_active_switches: s_trough1, s_trough2, s_trough3
```

What each part does:

- **`switches:`** each entry is a switch. `number:` is left empty because the virtual platform does not need one;
  with real hardware it holds the board's switch number (see below). `tags: start` marks the start button: the `game`
  config's `start_game_switch_tag` (default `start`) is the tag MPF watches to start a game, and `add_player_switch_tag`
  (also `start`) adds players.
- **`coils:`** a coil, which is how MPF drives solenoids and motors.
- **`playfields:`** a playfield with `tags: default` is the default one. `default_source_device` is the ball device
  that feeds it. See the [`playfields`](/reference/config/devices/playfields/) reference.
- **`ball_devices:`** the trough. `ball_switches` lists the switches that detect balls in it, `eject_coil` is the coil
  that ejects one, and `eject_targets` is where the ejected ball goes. The tags `trough`, `drain` and `home` tell MPF
  this device collects drained balls and is where balls rest at the start of a game.
- **`virtual_platform_start_active_switches:`** switches that start out *active* on the virtual platforms
  (`mpf/platforms/virtual.py`). Without it the virtual trough starts empty (the log shows `BCH: Initial count: 0`) and
  there is no ball to start a game with. Real hardware ignores this setting: there the switches report the real balls.

{{< note >}}
`ball_switches` and `eject_coil` appear as placeholders (`ignore`, with a "deprecated" comment) in the top-level
`ball_devices` entry of `config_spec.yaml`, but they are the normal way to configure a trough. MPF copies them into the
counter and ejector sub-configs (`ball_device_counter_ball_switches`, `ball_device_ejector_pulse`) and validates them
there. The [`ball_devices` reference](/reference/config/devices/ball-devices/) lists them in full.
{{< /note >}}

## 3. The base mode

The `base` mode created by `mpf init` already starts on `ball_starting` and stops on `ball_will_end`. You do not need
to change it yet. You also do not need to list the `game` mode: MPF's own `mpfconfig.yaml` already has
`modes: [attract, game]`, and your list is added to it.

## 4. Run it

```bash
mpf game -X
```

`-X` runs every device on the **smart virtual** platform (`mpf/platforms/smart_virtual.py`). It simulates what the
hardware would do: when the trough pulses its eject coil, a ball leaves the trough. Use it for this machine.

`-x` uses the plain **virtual** platform, which accepts the config but does not move balls. With this config the game
starts, but the trough never ejects, so the first ball never reaches the playfield.

What to expect:

- The console shows the version, the machine path and the loaded config files, then MPF starts the `attract` mode.
- Errors name a **section and a setting**, for example a missing required setting or a device name that is not defined.
  Fix the file and restart. The [config errors](/reference/errors/) page explains the messages.
- Logs go to the `logs/` folder of the machine. Each run writes a new file.

## 5. Press start without hardware

MPF itself has no keyboard input for switches (the text UI only displays state). To watch a game start with nothing
else installed, let the built-in switch player press the start button for you. Add this to `config/config.yaml`:

```yaml
switch_player:
  steps:
    - time: 2s
      switch: s_start
      action: hit
```

Run `mpf game -X` again. Two seconds after the machine is reset (`start_event` defaults to `machine_reset_phase_3`),
the switch player hits `s_start`, and the log shows `game_started`, `ball_started` and the trough ejecting a ball.
With no switch on the playfield, MPF counts the ball as on the playfield when the trough's eject timeout passes:
**10 seconds** by default (`eject_timeouts`, `mpf/devices/ball_device/ball_device.py`).

Steps run in order; `time` is the wait before each step and `action` is `activate`, `deactivate` or `hit`
(`mpf/plugins/switch_player.py`). Remove the section when you have a real start button.

{{< note >}}
Tools such as the MPF monitor and the media controller (separate packages) can toggle switches interactively. They
are not covered here yet.
{{< /note >}}

## 6. From virtual to FAST

Keep the same device names and rules and change only where the hardware numbers come from. A FAST version of the same
machine adds a `hardware:` section and a `fast:` section, and swaps the empty `number:` values for board addresses.
You can keep `virtual_platform_start_active_switches` for testing with `-X`. See
[Connecting FAST hardware](/build/fast-hardware/).
