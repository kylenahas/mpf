---
title: "Connecting FAST hardware"
weight: 1
---

This page covers the FAST Pinball platform (`fast` in `mpfconfig.yaml`, class
`mpf.platforms.fast.fast.FastHardwarePlatform`). MPF supports many other platforms through the same `hardware:` section,
so the rest of your config (modes, shots, ball devices, flippers) does not change when you change hardware. Only
`hardware:`, the platform section and the device `number:` values do.

{{< warn >}}
Everything here is taken from the source and from MPF's FAST test configs
(`mpf/tests/machine_files/fast/config/*.yaml`, mostly `neuron.yaml`). Nothing has been tested against real hardware by
the documentation tooling. Treat it as a map of what MPF accepts.
{{< /warn >}}

## The `hardware:` section

The `hardware` spec has one setting per device type, and each lists which platform handles it. `platform` is the
default for anything not listed:

```yaml
hardware:
  platform: fast
```

With `platform: fast` every device uses the FAST platform. You only need the per-type keys (`coils`, `switches`,
`lights`, `dmd`, ...) when you mix platforms, for example `lights: fadecandy`. Valid keys are in the
[`hardware` reference](/reference/config/sections/hardware/). The value `default` means "use `platform`".

## The `fast:` section

```yaml
fast:
  net:
    port: com3
    controller: neuron
    io_loop:
      io3208:
        model: FP-I/O-3208
        order: 1
      io1616:
        model: FP-I/O-1616
        order: 2
```

From `config_spec.yaml` (`fast_net`, `fast_io_loop`):

| Setting | Meaning | Default |
|---|---|---|
| `port` | Serial port(s). A list is accepted. | `auto` |
| `controller` | **Required.** One of `neuron`, `nano`, `sys11`, `wpc89`, `wpc95`. | none |
| `io_loop` | Named I/O boards on the loop, each with a `model` and an `order` (1 to 9, the position on the loop). | none |
| `baud` | Serial speed. | `921600` |
| `watchdog` | Watchdog interval. | `500ms` |
| `mute_unconfigured_switches` | Ignore switch changes for switches that are not in your config. | `false` |
| `debug`, `console_log`, `file_log` | Logging for the FAST connection. | `false`, `none`, `basic` |

The `io_loop` names (like `io3208`) are labels you choose. You use them in device numbers.

`fast:` can also contain `exp` (the expansion bus, with its `boards:`; each board can list `breakouts:` and
`led_ports:`), `aud`, `seg`, `dmd`, `emu` and `rgb`. See the [`fast:` reference](/reference/config/sections/fast/) and the
[`fast_exp_board`](/reference/config/shared/fast-exp-board/) settings. These were not part of the Neuron test config
this page follows.

## Device numbers on FAST

The test config shows the format: the I/O board label, a dash, and the channel on that board.

```yaml
switches:
  s_flipper_left:
    number: io3208-1
  s_start:
    number: io3208-6
    tags: start

coils:
  c_flipper_left_main:
    number: io1616-1
  c_flipper_left_hold:
    number: io1616-2
    allow_enable: true
```

The test config comments each board with the range of driver and switch numbers it provides, for example
`io3208` as "drivers 0-8, switches 0-31". Check your own board's model against that comment style when choosing channels.

## FAST-specific per-device settings

Under a device's `platform_settings:`:

| Device | Setting | Source spec |
|---|---|---|
| `switches` | `debounce_open`, `debounce_close` | `fast_switches` |
| `coils` | `recycle_ms`, `pwm2_ms` | `fast_coils` |

Switch debounce can also be set with the platform-neutral `debounce:` setting, for example `debounce: quick` (seen in the
test config as `debounce: auto`, `quick`, `normal`). The test configs show the numeric `platform_settings` forms as well.

## Flippers

Flippers are platform-neutral devices; they point at coils and switches. This is the dual-wound example from the FAST
test config:

```yaml
flippers:
  f_dual_wound:
    main_coil: c_flipper_main
    hold_coil: c_flipper_hold
    activation_switch: s_flipper
```

For a single-wound flipper omit `hold_coil`. `eos_switch` plus `use_eos: true` is used when the flipper has an
end-of-stroke switch.

## Mixed setups

The FAST test config includes a switch with `platform: smart_virtual` next to FAST switches. Any switch, coil or light can
name its own `platform`, as long as that platform appears in the `hardware:` section.

## Next steps

Back to platform-neutral topics: ball devices, shots, shows.
