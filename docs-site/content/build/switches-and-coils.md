---
title: "Switches and coils"
weight: 3
summary: "Switch types, the events switches post, coil pulse and hold settings, and wiring a switch to a coil in config."
verified: "MPF 0.82.0.dev0, virtual platform"
---

Switches are MPF's inputs and coils are its high-power outputs. Most of a machine's config is wiring one to the other
through **events**: a switch posts an event, and a device listens for it. This page covers the settings on both sides,
then wires them together without any code.

{{< tip >}}
**Verified.** The complete config at the end of this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the
virtual platform. Each behavior marked "in the test run" is checked by `docs-site/verify/test_guides.py`.
{{< /tip >}}

## Switches

```yaml
switches:
  s_start:
    number:
    tags: start
  s_coin_door:
    number:
    type: NC
  s_spinner:
    number:
    ignore_window_ms: 100ms
    events_when_activated: spinner_spin
```

| Setting | Default | What it does |
|---|---|---|
| `number` | required | The switch's address on your hardware. Its format depends on the platform (see [Connecting FAST hardware](/build/fast-hardware/)). The virtual platforms accept an empty value. |
| `type` | `NO` | `NC` (normally closed) inverts the switch: MPF reports it *active* when the circuit is open. Use it for switches that are closed at rest, such as many coin door and optical switches. |
| `debounce` | `auto` | `quick`, `normal` or `auto`. Passed to the hardware platform, which decides how each value maps to its own debounce timing. |
| `ignore_window_ms` | `0` | After the switch posts its events, it posts no more for this long. Only the switch's own events are limited; devices watching the switch directly still see every change. In the test run, five spinner hits 20 ms apart posted `spinner_spin` once; a hit a second later posted it again. |
| `events_when_activated` / `events_when_deactivated` | none | Extra events to post when the switch changes. |
| `tags` | none | Labels other devices look for (`start`, `playfield_active`) and that post `sw_<tag>` events. |

`NO`/`NC` handling is in `mpf/devices/switch.py`: the logical state is the hardware state flipped when the type is
`NC` (`switch_controller.py`). Everything else in MPF sees only the logical state.

### Events a switch posts

When a switch changes, MPF can post these events (`mpf/devices/switch.py`):

| Event | When |
|---|---|
| `<switch name>_active`, `<switch name>_inactive` | The switch became active or inactive. |
| `sw_<tag>`, `sw_<tag>_active` | A switch with that tag became active. |
| `sw_<tag>_inactive` | A switch with that tag became inactive. |
| each event in `events_when_activated` / `events_when_deactivated` | As configured. |

In the test run, pressing `s_action_button` posted both `s_action_button_active` and its configured `knock` event.

{{< note >}}
For speed, MPF only posts these events when something listens for them (a handler in your config or code), or when
the switch has `debug: true`. You will not see `s_start_active` in the log unless something uses it. The patterns
(`%_active`, `%_inactive`, `sw_%`) come from the `mpf:` section settings `switch_event_active`,
`switch_event_inactive` and `switch_tag_event`.
{{< /note >}}

### Switches held for a time

A `timed_switches:` device posts events when one or more switches have been in a state for a set time, and again
when they leave it. It is valid in machine and mode configs.

```yaml
timed_switches:
  left_flipper_held:
    switches: s_left_flipper
    time: 2s
    events_when_active: magnet_on
    events_when_released: magnet_off
```

In the test run, holding `s_left_flipper` for 1 s posted nothing; at 2 s `magnet_on` was posted, and releasing the
switch posted `magnet_off`. `switch_tags:` matches switches by tag instead of by name, and `state: inactive` times how
long a switch is *open*.

## Coils

A coil is any driver output: solenoids, flashers wired as coils, motors, the knocker.

```yaml
coils:
  c_knocker:
    number:
    default_pulse_ms: 25
    pulse_events: knock
  c_magnet:
    number:
    default_hold_power: 0.5
    max_hold_duration: 3s
    enable_events: magnet_on
    disable_events: magnet_off
```

There are three ways to fire a coil:

- **Pulse**: on for a short time, then off. Used for kickers, the knocker, ball ejects.
- **Enable**: on until disabled, usually at reduced power. Used for magnets, diverters held in place, flipper holds.
- **Timed enable**: an enable that turns itself off after `default_timed_enable_ms`.

### Pulse settings

| Setting | Default | What it does |
|---|---|---|
| `default_pulse_ms` | `mpf: default_pulse_ms` (10 ms) | How long a pulse lasts when nothing asks for a different time. |
| `default_pulse_power` | full power | Strength of the pulse, 0 to 1. |
| `max_pulse_ms`, `max_pulse_power` | no limit, 1.0 | Safety limits. A request above them raises an error instead of firing. |
| `default_recycle` | platform | Whether the hardware enforces a cool-down between pulses. |

In the test run, the knocker's driver reported `pulsed_25` after `knock`: the `default_pulse_ms` value.

### Hold settings

Holding a coil fully on can burn it out, so MPF will not enable a coil unless you say how. From
`Driver.get_and_verify_hold_power` (`mpf/devices/driver.py`):

| Setting | Effect |
|---|---|
| `default_hold_power: 0.5` | Enable holds at 50 % power. Also the highest hold power allowed, unless `max_hold_power` is set. |
| `max_hold_power` | Upper limit for any hold power requested. |
| `allow_enable: true` | Allows holding at full power (1.0). Only for coils designed to stay on. |
| none of these | Enabling the coil fails with "Cannot enable driver ... with hold_power 0.0". |
| `max_hold_duration: 3s` | MPF turns the coil off after this long, logs a warning and adds a technical alert ("Reached max_hold_duration"). |

In the test run, `c_magnet` was enabled when `magnet_on` was posted and turned off by itself 3 s later, while the
flipper button was still held. Set `max_hold_duration` on anything that could overheat if a mode forgets to disable it.

### Control events

Every coil accepts `pulse_events`, `enable_events`, `disable_events` and `timed_enable_events`. Each is an
[event handler setting](/get-started/config-files/#event-handlers): when one of the listed events is posted, MPF calls
the matching method on the coil. The [`coils` reference](/reference/config/devices/coils/#control-events) lists them.

### Power supplies

`psu` names the power supply a coil is on (default `default`). MPF uses it to space out pulses so that several coils do
not fire in the same instant. Only pulses whose caller allows a delay are moved, for example ball device ejects, up
to `eject_coil_max_wait_ms` (default 200 ms); pulses from `pulse_events` fire at once (`Driver._notify_psu_and_get_wait_ms`). See the
[`psus` reference](/reference/config/devices/psus/).

## Wiring a switch to a coil

Nothing more than events is needed. The switch posts an event; the coil listens for it:

```yaml
switches:
  s_action_button:
    number:
    events_when_activated: knock

coils:
  c_knocker:
    number:
    default_pulse_ms: 25
    pulse_events: knock
```

This goes through MPF's event loop, so it is fine for things like a knocker or a toy, but it is too slow for
slingshots, pop bumpers and flippers. For those, use `autofire_coils:` and `flippers:`, which program the rule into the
hardware controller so the coil fires without a round trip through MPF. They are covered in their own guide.

## The complete config

```yaml
#config_version=6

switches:
  s_start:
    number:
    tags: start
  s_action_button:
    number:
    events_when_activated: knock
  s_coin_door:
    number:
    type: NC
  s_spinner:
    number:
    ignore_window_ms: 100ms
    events_when_activated: spinner_spin
  s_left_flipper:
    number:
    tags: flipper_button

coils:
  c_knocker:
    number:
    default_pulse_ms: 25
    pulse_events: knock
  c_magnet:
    number:
    default_hold_power: 0.5
    max_hold_duration: 3s
    enable_events: magnet_on
    disable_events: magnet_off

timed_switches:
  left_flipper_held:
    switches: s_left_flipper
    time: 2s
    events_when_active: magnet_on
    events_when_released: magnet_off
```

What the test run showed:

1. `s_coin_door` (`type: NC`) reads inactive at boot: the virtual platform starts NC switches closed.
2. Pressing `s_action_button` posts `s_action_button_active` and `knock`; `c_knocker` pulses for 25 ms.
3. Five `s_spinner` hits in 100 ms post `spinner_spin` once.
4. Holding `s_left_flipper` posts `sw_flipper_button` at once and `magnet_on` after 2 s; `c_magnet` is enabled.
5. 3 s later `c_magnet` is disabled by `max_hold_duration`, though the button is still held.
6. Releasing the button posts `magnet_off`.

## Testing switches and coils

- Set `debug: true` on a switch or coil to log every change and pulse.
- Without hardware, use the [switch player](/get-started/first-machine/#5-press-start-without-hardware) to press
  switches on a schedule.
