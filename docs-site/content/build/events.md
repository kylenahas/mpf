---
title: "Events and conditions"
weight: 6
summary: "How config pieces talk to each other: posting and handling events, delays, priorities, conditions and event arguments."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

Almost everything in an MPF config is connected by **events**. An event is a named message such as `ball_started` or
`s_target_active`. Devices, modes and switches post events when things happen; other settings list the events they
react to. You build game rules by connecting the two.

{{< tip >}}
**Verified.** The complete config at the end of this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase`, and every
"in the test run" statement is checked by `docs-site/verify/test_guides.py`.
{{< /tip >}}

## Where events come from

- **Devices and modes.** Each config reference page has an **Events posted** section, and the
  [events](/reference/events/) page lists every event MPF documents, with its arguments.
- **Switches**, as `<switch>_active`, `sw_<tag>` and their `events_when_activated` (see
  [switches and coils](/build/switches-and-coils/#events-a-switch-posts)).
- **Settings named `events_when_...`** on many devices, for example `events_when_started` on a mode.
- **`event_player:`**, which posts events when other events happen (below).

Every posted event is written to the log, with its arguments:

```text
INFO : EventManager : Event: ======'ball_started'====== Args={'ball': 1, 'player': 1, ...}
```

Reading that line is the quickest way to find the exact event name to use.

## Reacting to events

Settings ending in `_events` list events to react to. They accept a list, a comma string, or a mapping of event to
delay, as described in [writing config files](/get-started/config-files/#event-handlers):

```yaml
coils:
  c_knocker:
    number:
    pulse_events:
      big_award: 500ms
```

With a delay, the action happens that long after the event (`DeviceManager._control_event_handler`). In the test run,
the knocker was still off 0.1 s after `big_award` and had pulsed by 0.6 s.

Config players (`event_player:`, `show_player:`, `light_player:` and the rest) are keyed by event instead: each key
is an event, and the value says what to do when it is posted.

## event_player

`event_player:` posts events in response to events. It is valid in machine configs, mode configs and shows; in a mode
it only works while the mode runs.

```yaml
event_player:
  s_target_active: target_hit
  s_lane_active: lane_done|2s
```

| Form | Meaning |
|---|---|
| `trigger: one_event` | Post `one_event` when `trigger` is posted. |
| `trigger: a, b` or a YAML list | Post several events. |
| `trigger: name\|2s` | Post `name` 2 seconds later. In the test run, `lane_done` had not been posted 1.5 s after the lane switch and had been by 2.5 s. |
| `trigger: [plain, maybe{condition}]` | Post each event; ones with a condition only when it is true. |
| `trigger:` with a mapping of event to arguments | Post events with arguments (below). |

The forms come from MPF's own tests (`event_players/config/test_event_player.yaml`).

### Passing arguments

Events can carry arguments. To post one with arguments, map the event name to them. A value can be computed from the
triggering event's arguments with `value` and `type`:

```yaml
event_player:
  ball_started:
    ball_report:
      which:
        value: ball
        type: int
```

In the test run, `ball_report` was posted with `which: 1` on ball 1 and `which: 2` on ball 2, taken from the `ball`
argument of `ball_started`. `type` is `int`, `float`, `bool` or `string`.

## Conditions

Add a condition in braces after any event name you react to. The handler only runs when the condition is true:

```yaml
event_player:
  ball_started{ball==2}: second_ball_started
  target_hit{current_player.ball>=2}: big_award
```

Conditions use Python expression syntax: `==`, `!=`, `>`, `>=`, `and`, `or`, `not`, `True`, `False`. Writing
`true` or `false` in lower case is a config error ("Placeholder use Python syntax. Use True and False instead of
true and false.", `placeholder_manager.py`). MPF reports it only when the condition is first evaluated, not at
startup: in the test run, a machine with `ball_started{true}` booted normally and stopped when the first ball started.
There must be no space in the event name before the brace.

Names you can use in a condition (`PlaceholderManager.get_global_parameters` and `_eval_name`):

| Name | Value | Example |
|---|---|---|
| the event's own arguments | as posted | `ball==2` on `ball_started` |
| `current_player` | the player whose turn it is | `current_player.score>1000` |
| `players` | all players, by index | `players[0].score>0` |
| `game` | the running game | `game.num_players>1` |
| `machine` | machine variables | `machine.my_variable>0` |
| `device` | any device, by collection and name | `device.ball_holds.hold_test.enabled` |
| `mode` | any mode | `mode.mode1.active` |
| `settings` | operator settings | |

In the test run:

- `ball_started{ball==2}` did nothing on ball 1 and posted `second_ball_started` on ball 2.
- `target_hit{current_player.ball>=2}` did nothing in attract mode or on ball 1, and posted `big_award` on ball 2.
  Outside a game, a condition on `current_player` is simply false; it is not an error.

## Handler order

When several handlers listen to the same event, they run from the highest priority to the lowest. Add `.N` to an event
name to raise a handler's priority by N (`EventManager.get_event_and_condition_from_string`):

```yaml
event_player:
  target_hit.2: target_first
  target_hit.1: target_second
```

In the test run, `target_first` was posted before `target_second`. Handlers that belong to a mode also get the mode's
priority (see [modes](/build/modes/#priority)). Because of the `.N` syntax, an event name you react to cannot contain
a dot ("Failed to parse priority in event name ... Does your event name contain a dot?").

## More examples

Recipes for the events you will react to most often. They all live in one game mode, `examples`, plus a few devices in
the machine config. Each was run on MPF; the file is at the end of this section.

### A drop target bank is complete

Drop target banks post `drop_target_bank_<name>_down` when every target in the bank is down
(`mpf/devices/drop_target.py`):

```yaml
event_player:
  drop_target_bank_lower_bank_down: lower_bank_complete
```

In the test run, knocking down two of the three targets posted nothing; the third posted `lower_bank_complete`. The
bank also posts `_up` and `_mixed`.

### Something was hit N times

A **counter** counts events and posts `events_when_complete` when it reaches `count_complete_value`. Every hit
posts `logicblock_<name>_hit` with `count`, `hits` and `remaining` arguments, so a condition can react to a specific
hit:

```yaml
counters:
  ramp_counter:
    count_events: s_ramp_active
    count_complete_value: 3
    events_when_complete: ramp_jackpot_lit

event_player:
  logicblock_ramp_counter_hit{count==2}: one_more_ramp
```

In the test run, the second ramp posted `one_more_ramp` and the third posted `ramp_jackpot_lit`.

{{< note >}}
Setting `events_when_complete` **replaces** the default event `logicblock_<name>_complete`; it is not posted as well
(`LogicBlock.validate_and_parse_config`). The same goes for `events_when_hit`. In the test run,
`logicblock_ramp_counter_complete` was never posted.
{{< /note >}}

### Something happens over time

A **timer** (valid in modes only) counts and posts `timer_<name>_tick` each step, with `ticks` and
`ticks_remaining`, then `timer_<name>_complete` at the end. `control_events` start, stop, restart or change it:

```yaml
timers:
  hurry_up_timer:
    start_value: 10
    end_value: 0
    direction: down
    control_events:
      - action: restart
        event: ramp_jackpot_lit
      - action: stop
        event: hurry_up_collected

event_player:
  timer_hurry_up_timer_tick{ticks==5}: hurry_up_halfway
  timer_hurry_up_timer_complete: hurry_up_missed
```

In the test run, the timer started on the third ramp, posted `hurry_up_halfway` 5 seconds later and `hurry_up_missed`
after 10.

### Only while something is true

A condition can read any device. Here a ramp collects the hurry-up only while its timer is running:

```yaml
event_player:
  s_ramp_active{device.timers.hurry_up_timer.running}: hurry_up_collected
```

In the test run, a ramp 3 seconds into the hurry-up posted `hurry_up_collected` and stopped the timer, so
`hurry_up_missed` never came. Ramps before the timer started, or after it ended, posted nothing.

{{< warn >}}
**A condition sees the state from before the event is handled.** The third ramp both starts the timer (through the
counter) and is checked by the condition above, but the condition is evaluated first, so the third ramp does **not**
collect the hurry-up. The same applies to counters: `s_ramp_active{device.counters.ramp_counter.value==2}` is true
on the *third* hit, because the counter has not counted that hit yet. To react to a count, use the counter's own
`logicblock_<name>_hit` event as above, whose `count` argument is already updated.
{{< /warn >}}

### Both flipper buttons

MPF's own `mpfconfig.yaml` already defines two devices for the flipper buttons. Tag your buttons `left_flipper` and
`right_flipper` and you get:

| Event | When | Built-in device |
|---|---|---|
| `flipper_cancel` | Both buttons are pressed together. | `combo_switches: both_flippers` |
| `flipper_cradle` / `flipper_cradle_release` | Either button is held for 3 s / released. | `timed_switches: flipper_cradle` |

```yaml
switches:
  s_left_flipper:
    number:
    tags: left_flipper
  s_right_flipper:
    number:
    tags: right_flipper

event_player:
  flipper_cancel: show_status
```

In the test run, pressing both buttons posted `show_status` at once. `flipper_cradle` is also what pauses ball search
while a player holds the ball (`ball_search_block_events` on the playfield).

{{< warn >}}
Do not name your own combo switch `both_flippers` or timed switch `flipper_cradle`. Your entry is merged into MPF's,
so it inherits MPF's settings (`tag_1`, `tag_2`, `events_when_both: flipper_cancel`) wherever you leave one out. In the
test run, a combo switch named `both_flippers` with only `switches_1` and `switches_2` reached state `both` and posted
`flipper_cancel`, not the `both_flippers_both` a new combo switch would post. Use the built-in one, or pick another
name and use `combo_switches:` with `switches_1`, `switches_2`, `hold_time` and `events_when_both` (see the
[`combo_switches` reference](/reference/config/devices/combo-switches/)).
{{< /warn >}}

### Everything in one place

These additions go into the machine config of [the complete config](#the-complete-config) below. Add `examples` to its
`modes:` list:

```yaml
# Added to config/config.yaml for the examples
modes:
  - examples

switches:
  s_ramp:
    number:
  s_left_flipper:
    number:
    tags: left_flipper
  s_right_flipper:
    number:
    tags: right_flipper
  s_drop1:
    number:
  s_drop2:
    number:
  s_drop3:
    number:

drop_targets:
  drop1:
    switch: s_drop1
  drop2:
    switch: s_drop2
  drop3:
    switch: s_drop3

drop_target_banks:
  lower_bank:
    drop_targets: drop1, drop2, drop3
```

`modes/examples/config/examples.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_started
  stop_events: ball_will_end
  priority: 150

counters:
  ramp_counter:
    count_events: s_ramp_active
    count_complete_value: 3
    events_when_complete: ramp_jackpot_lit

timers:
  hurry_up_timer:
    start_value: 10
    end_value: 0
    direction: down
    control_events:
      - action: restart
        event: ramp_jackpot_lit
      - action: stop
        event: hurry_up_collected

event_player:
  drop_target_bank_lower_bank_down: lower_bank_complete
  logicblock_ramp_counter_hit{count==2}: one_more_ramp
  timer_hurry_up_timer_tick{ticks==5}: hurry_up_halfway
  timer_hurry_up_timer_complete: hurry_up_missed
  s_ramp_active{device.timers.hurry_up_timer.running}: hurry_up_collected
  flipper_cancel: show_status
```

## Other event players

| Section | What it does |
|---|---|
| [`random_event_player`](/reference/config/players/random-event-player/) | Posts one event picked at random from a list. |
| [`queue_event_player`](/reference/config/players/queue-event-player/) | Posts `queue_event` as a queue event and posts `events_when_finished` once every handler has released it. |
| [`queue_relay_player`](/reference/config/players/queue-relay-player/) | Holds a queue event (such as `ball_ending`): posts `post`, then releases the queue when `wait_for` is posted. |

## The complete config

The `modes/base/config/base.yaml` from `mpf init` is used unchanged.

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
  s_lane:
    number:

coils:
  c_trough_eject:
    number:
  c_knocker:
    number:
    pulse_events:
      big_award: 500ms

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

event_player:
  s_target_active: target_hit
  target_hit{current_player.ball>=2}: big_award
  target_hit.2: target_first
  target_hit.1: target_second
  s_lane_active: lane_done|2s
  ball_started{ball==2}: second_ball_started
  ball_started:
    ball_report:
      which:
        value: ball
        type: int

virtual_platform_start_active_switches: s_trough1
```

What the test run showed:

1. In attract mode, hitting `s_target` posts `target_hit`, then `target_first` and `target_second` in that order; no
   `big_award`.
2. Ball 1 starts: `ball_report` with `which: 1`; no `second_ball_started`.
3. `s_target` on ball 1: no `big_award`.
4. `s_lane`: `lane_done` 2 s later.
5. Ball 2 starts: `second_ball_started`, and `ball_report` with `which: 2`.
6. `s_target` on ball 2: `big_award`; the knocker pulses 500 ms later.
