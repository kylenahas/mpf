---
title: "Devices"
weight: 5
summary: "What a device is inside MPF: collections, machine-wide and mode devices, control events and their delays, the attributes you can use in conditions, and how to find them."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

Every entry under a device section of the config, a switch, a ball device, a shot, a counter, becomes a Python object
when MPF starts. This page explains those objects: where they live, when they're active, how `*_events` settings
control them, and which of their attributes a [condition](/build/events/#conditions) can read.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase` on the smart virtual
platform. The behaviour below is from those runs, and `docs-site/verify/test_guides.py` repeats the checks.
{{< /tip >}}

## Collections

Each device section is a **collection** on the machine, under the section's name: `self.machine.switches`,
`self.machine.ball_devices`, `self.machine.counters`, and so on, indexed by the device's name. In [mode
code](/architecture/mode-code/) or a [test](/architecture/testing/), `self.machine.counters["ramp_counter"]` is the
counter of that name. The same names appear in conditions as `device.counters.ramp_counter`.

## Machine-wide and mode devices

A device's class decides where it can be configured. Each page of the [config reference](/reference/config/) shows
it as **Valid in**.

- **Machine-wide devices** (classes based on `SystemWideDevice`) go in the machine config and are active for the life
  of the machine: switches, coils, lights, ball devices, flippers, the playfield.
- **Mode devices** (based on `ModeDevice`) go in a mode's config and are active while the mode runs: shots, timers,
  multiball locks.
- Some classes are both, so the device can go in either: counters and the other logic blocks, ball saves. A counter's
  class is based on both `SystemWideDevice` and `ModeDevice`.

A mode device's object is created when MPF starts, like any other. In the test run, `self.machine.counters
["ramp_counter"]`, defined in the `base` mode, already existed in attract mode, but its `value` was `None`: a counter
keeps its state in the player, and there was no player yet. When the first ball started, `value` was 0. Its control
events, such as `enable_events`, are added as [mode handlers](/architecture/mode-code/#handlers-and-delays-that-clean-up)
when the mode starts and removed when it stops (`Mode._setup_device_control_events`).

## Control events

Every device setting that ends in `_events`, such as `enable_events` or `reset_events`, is a **control event**. MPF
connects it to the device method with the same name, `event_enable` for `enable_events` and so on
(`DeviceManager.get_device_control_events`). Devices define these methods with an `@event_handler` decorator, which
also gives the handler its priority.

A control event can have a delay. Use the dictionary form, with the delay as the value:

```yaml
counters:
  ramp_counter:
    count_events: s_ramp_active
    count_complete_value: 3
    events_when_complete: ramp_jackpot_lit
    start_enabled: false
    enable_events:
      mode_base_started: 2s
```

The plain form, `enable_events: mode_base_started`, is the same with no delay (`Util.event_config_to_dict`). In the
test run, the counter above started disabled. A ramp about 1 second into the ball didn't count; a ramp 2.7 seconds in
did, and posted `logicblock_ramp_counter_hit`.

## Device attributes in conditions

`device.<collection>.<name>.<attribute>` in a condition reads one of the device's **monitored attributes**: the ones
its class lists in a `@DeviceMonitor(...)` decorator (`mpf/core/device_monitor.py`). Only those can be read, and when
one changes, MPF tells anything watching it, which is how a media controller can show device state. For example:

```yaml
event_player:
  s_target_active{device.counters.ramp_counter.value>=2}: target_lit_hit
```

In the test run, the target posted nothing after one counted ramp and `target_lit_hit` after two.

{{< warn >}}
**A wrong attribute name fails silently.** A counter's hit event has a `count` argument, but the counter's attribute is
`value`. In a test run with `device.counters.ramp_counter.count>=2` instead, MPF booted and ran without any error or
warning, and the target never posted `target_lit_hit`, even with two ramps counted. Reading a missing attribute raises
an error inside MPF (`Attribute count does not exist.`), but an event condition treats that as false
(`BaseTemplate.evaluate` in `mpf/core/placeholder_manager.py`). If a conditional entry never fires, check the
attribute against the table below.
{{< /warn >}}

The attributes of the common devices, from the `@DeviceMonitor` line of each class in `mpf/devices/`:

| Collection | Attributes |
|---|---|
| `switches` | `state`, `recycle_jitter_count`, `number` |
| `lights` | `color`, `address` |
| `ball_devices` | `available_balls`, `state`, `balls` |
| `playfields` | `available_balls`, `balls`, and more |
| `flippers`, `autofire_coils`, `kickbacks` | `enabled` |
| `diverters` | `active`, `enabled`, `eject_state` |
| `drop_targets` | `complete` |
| `drop_target_banks` | `complete`, `down`, `up`, `state` |
| `shots` | `state`, `state_name`, `enabled` |
| `shot_groups` | `common_state`, `rotation_enabled` |
| `counters`, `accruals`, `sequences` | `value`, `enabled`, `completed` |
| `timers` | `running`, `ticks`, `end_value`, `max_value`, `start_value` |
| `ball_saves` | `saves_remaining`, `enabled`, `timer_started`, `state` |
| `multiballs` | `shoot_again`, `grace_period`, `hurry_up`, `balls_added_live`, `balls_live_target`, `enabled` |
| `multiball_locks` | `locked_balls`, `enabled` |
| `ball_holds` | `balls_held`, `enabled` |
| `extra_balls`, `extra_ball_groups` | `enabled` |
| `achievements` | `state`, `selected` |
| `achievement_groups` | `enabled`, `selected_member` |
| `state_machines` | `state` |
| `combo_switches` | `state` |
| `timed_switches` | `active_switches` |
| `magnets` | `active`, `release_in_progress`, `enabled` |
| `spinners` | `active`, `idle`, `enabled` |
| `segment_displays` | `text` |

A condition reads the value from **before** the event it's attached to is handled; see
[conditions](/build/events/#only-while-something-is-true).

## Events devices post

Devices post events named after themselves, such as `logicblock_ramp_counter_hit`, `ball_save_start_save_enabled` or
`balldevice_bd_trough_ball_eject_success`. The [events reference](/reference/events/) lists them by device type, and
each [config reference](/reference/config/) page lists the events its device posts.

## What happened in the test run

| Time into ball 1 | Step | `value` | `enabled` | Events |
|---|---|---|---|---|
| (attract mode) | | `None` | `None` | |
| 0 s | The ball starts | 0 | `false` | `mode_base_started` |
| 1.1 s | Ramp | 0 | `false` | Not counted |
| 2.7 s | Ramp | 1 | `true` | `logicblock_ramp_counter_hit`; the delayed enable came at 2 s |
| 2.8 s | Target | 1 | `true` | Nothing: the condition needs 2 |
| 2.9 s | Ramp | 2 | `true` | `logicblock_ramp_counter_hit` |
| 3.0 s | Target | 2 | `true` | `target_lit_hit` |
| | The ball drains; ball 2 starts | 0 | | The counter started over: no `persist_state` |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base

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
  s_ramp:
    number:
    tags: playfield_active
  s_target:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:

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

virtual_platform_start_active_switches: s_trough1, s_trough2
```

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

counters:
  ramp_counter:
    count_events: s_ramp_active
    count_complete_value: 3
    events_when_complete: ramp_jackpot_lit
    start_enabled: false
    enable_events:
      mode_base_started: 2s

event_player:
  s_target_active{device.counters.ramp_counter.value>=2}: target_lit_hit
```
