---
title: "Writing config files"
weight: 4
---

MPF config files and show files are YAML, with a few deliberate differences from standard YAML. This page covers the
differences (from `docs/overview/yaml.rst` in the MPF repo), how settings are typed, and how events are written in
configs. Type behavior comes from `mpf/core/config_validator.py`.

## YAML differences

MPF avoids YAML's habit of guessing types for ambiguous unquoted values:

| You write | Standard YAML reads it as | MPF reads it as |
|---|---|---|
| `+1` | the integer `1` | the **string** `+1` (a leading plus means "change by", in places that support it) |
| `050505` (three or more digits, leading zero) | an octal number | the **string** `050505` (so color codes survive) |
| `on`, `off` | booleans | **strings** (so you can name a show `on`) |
| `123e45` (digits and one `e`) | a number in exponent form | the **string** `123e45` (could be a hex color) |

`true`, `false`, `yes` and `no` are still booleans.

## Booleans

For settings typed `bool`, the validator also accepts the strings `false`, `f`, `no`, `disable`, `off` and `true`, `t`,
`yes`, `enable`, `on` (any case). Anything else raises a "Cannot convert value to boolean" error.

## Times

Settings typed `ms` take a number of milliseconds or a string with a unit. From `Util.string_to_ms`:

| Written | Meaning |
|---|---|
| `200` or `200ms` | 200 milliseconds (no unit means ms) |
| `2s` or `2sec` | 2000 ms |
| `1m` | 60,000 ms |
| `1h`, `1d` | hours, days |
| `None` | 0 |

Settings typed `secs` use the same strings but give seconds; a bare number such as `2` means 2 seconds there.

## Lists

A setting typed `list` accepts a comma-separated string or a YAML list:

```yaml
ball_switches: s_trough1, s_trough2, s_trough3
```

is the same as

```yaml
ball_switches:
  - s_trough1
  - s_trough2
  - s_trough3
```

An empty element in a list is an error ("List contains an empty element").

## Required settings

In the [config reference](/reference/config/), a **required** default means the setting must be present. If it is
missing you get an error of the form `Required setting "x:" is missing from section "y:" in your config.`

## Device names

A setting typed `machine(<collection>)` must name a device that exists in your config. For example,
`ball_switches: s_trough1` requires a switch named `s_trough1`. A typo gives an error saying the device was not found
in that section.

## Event handlers

Settings ending in `_events` (like `start_events`, `stop_events`, `enable_events`) say *when* something should happen.
They are typed `event_handler:ms`: a mapping of event name to a delay. You can write them three ways, and all three
become the same internal mapping (`Util.event_config_to_dict`):

```yaml
mode:
  start_events: ball_starting                   # one event, no delay
  stop_events: ball_will_end, tilt              # several events, no delay
```

```yaml
drop_target_banks:
  left_bank:
    reset_events:
      game_started.1: 3s                        # event name: delay
      drop_target_bank_left_bank_down: 1s
```

(Second example adapted from `drop_targets/config/test_drop_targets.yaml` and `test_multiple_drop_resets_on_startup.yaml`
in the test suite.) A plain list or comma string gives every event a delay of 0.

The event name syntax that the engine understands (from `EventManager.get_event_and_condition_from_string`):

- **Condition:** `event_name{current_player.score>1000}` handles the event only when the condition is true.
- **Priority:** `event_name.10` adds 10 to the handler's priority (as in `game_started.1` above).
- Event names cannot contain spaces.

Settings starting with `events_when_...` do the opposite: they list events that MPF **posts** when something happens.
The test suite also uses a `|` delay form there, for example `events_when_activated: test_active|100ms, test_active2`
on a switch. That form is not part of the `*_events` handler settings above, so check the setting's type in the
[reference](/reference/config/) rather than assuming.

## Merging several files

If you load more than one machine config (`mpf game -c config.yaml,extra.yaml`), the files are merged with later ones
winning. Mode configs are merged the same way with the built-in mode config of the same name, if there is one.

## Comments and the version header

Start every file with `#config_version=6`. Lines starting with `#` are comments, as in standard YAML.
