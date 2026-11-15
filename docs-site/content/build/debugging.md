---
title: "Debugging"
weight: 20
summary: "Where MPF reports problems, how to read a config error, the exact messages for common mistakes, and why a game will not start."
verified: "MPF 0.82.0.dev0, smart virtual platform and mpf game -X"
---

When something is wrong, MPF either stops with an error (usually a config problem) or runs but does not do what you
expected. This page covers both. Every message quoted here is what MPF 0.82.0.dev0 actually printed when the mistake
was made on the config from [Your first machine](/get-started/first-machine/).

{{< tip >}}
**Verified.** Each mistake below was run on MPF; `docs-site/verify/test_guides.py` repeats every one and checks that
MPF still prints the message quoted here. The "game will not start" run used `mpf game -X`.
{{< /tip >}}

## Where to look

**The console.** `mpf game` prints log lines at INFO level and above. Every event, every switch change and every mode
start appears there:

```text
10:57:35.284 : INFO [SwitchController] <<<<<<< 's_start' active >>>>>>>
10:57:35.285 : INFO [EventManager] Event: ======'request_to_start_game'====== Args={}
10:57:35.286 : WARNING [BallController] BallController denies game start. Not enough balls. 0 found. 1 required
```

**The log file.** Each run writes a new file in the machine's `logs/` folder, named
`<date>-<time>-mpf-<computer name>.log` (`mpf/commands/game.py`), for example
`logs/2026-11-13-10-57-33-mpf-DESKTOP.log`. It has the same lines with full timestamps, plus some below INFO.

| Option | Effect |
|---|---|
| `-v` | Verbose (DEBUG) logging to the log file. |
| `-V` | Verbose logging to the console; needs `-v` too. |
| `-t` | Turns the text UI **off**, so the console shows plain log lines. (Its help text says "Use the ASCII test-based UI", but the option switches it off.) |
| `-l <file>` | Write the log to this file instead. |
| `-b` | Do not try to connect to a media controller. |

**One device at a time.** Every device accepts `debug: true`, which logs that device's decisions in detail. Devices
also have `console_log` and `file_log` (`none`, `basic` or `full`) to control how much of their log goes where. Add
`debug: true` to the device you suspect rather than turning on `-v` for everything.

## Reading a config error

Config problems stop MPF at startup with a message of this shape:

```text
Config File Error in ConfigValidator: Config validation error: Entry switches:s_start:ignore_during_ball_search = "maybe" is not valid. Cannot convert value to boolean. Error Code: CFE-ConfigValidator-13 (https://missionpinball.org/latest/logs)
```

- **`Config File Error in <part>`** names the part of MPF that found the problem.
- **`Entry switches:s_start:ignore_during_ball_search`** is the path to the setting: section, device, setting.
- **`= "maybe"`** is the value MPF read, after YAML parsing.
- **The reason** comes next. The [config errors](/reference/errors/) page lists every reason the validator can give.
- **`Error Code: CFE-ConfigValidator-13`** identifies the check. Note that the URL in the message points at the old
  docs site.

YAML problems are reported before MPF looks at any setting, as `YAML error found in file ... Line <n>, Position <m>`.

## Common mistakes and their messages

### YAML

| Mistake | MPF says | Fix |
|---|---|---|
| A tab used for indenting | `while scanning for the next token found character that cannot start any token`, with the line and column | Indent with spaces only. |
| One line indented by 3 spaces instead of 4 | `while parsing a block mapping ... did not find expected key`, naming the line of the parent and the line that is off | Line the setting up with its siblings. |
| The same switch defined twice | `found duplicate key "s_trough3"`, with both line numbers | Remove or rename one. |
| `balls_installed 3` (no colon) | `Your config contains a value for the setting "machine:b", but this is not a valid setting name.` | Add the colon. The odd `machine:b` is the first letter of the line, because MPF read the line as one string. |
| No `#config_version=6` first line | `Version mismatch. Expected: #config_version=6 Actual:` | Make it the first line of every config file. |

### Names

| Mistake | MPF says | Fix |
|---|---|---|
| `switchs:` | `Found a "switchs:" section in config file ..., but that section name is unknown. Did you mean "switches:" instead?` | Use the suggested name. |
| `eject_coils:` on a ball device | `Your config contains a value for the setting "ball_devices:bd_trough:eject_coils", but this is not a valid setting name.` | Check the setting in the [reference](/reference/config/). |
| `eject_coil: c_trough_ejct` (typo in a device name) | `Device "c_trough_ejct" not found in "coils:" section in your config.` | Match the name in `coils:` exactly. |
| `eject_all_events: ball started` | `Cannot handle events with spaces in the event name, please remedy "ball started"` | Event names use underscores. |

{{< note >}}
For ball devices, the path in a device-name error names the internal sub-config, not your section:
`Entry ball_device_ejector_pulse:ball_device_ejector_pulse:eject_coil = "c_trough_ejct"`. The value in quotes is the
part to look for. (MPF copies `eject_coil` and `ball_switches` into these sub-configs; see
[ball devices](/build/ball-devices/).)
{{< /note >}}

### Values

| Mistake | MPF says | Fix |
|---|---|---|
| `eject_timeouts: 2 secs` | `Cannot convert value to ms.` | Use `2s`, `2sec` or `2000` (see [times](/get-started/config-files/#times)). |
| `ignore_during_ball_search: maybe` | `Cannot convert value to boolean.` | `true`/`false` (or yes/no, on/off). |
| `ball_switches: s_trough1, , s_trough3` | `List contains an empty element.` | Remove the extra comma. |

### Required settings and device rules

| Mistake | MPF says | Fix |
|---|---|---|
| A switch with no `number:` line at all | `Required setting "number:" is missing from section "switches:s_trough1:" in your config.` | Add `number:` (it may be empty on the virtual platforms, but it must be there). |
| A ball device with no eject coil | `Configuration error in bd_trough ball device. Device needs an eject_coil, a hold_coil, or "mechanical_eject: True"` | See [ball devices](/build/ball-devices/). |
| A slingshot, pop bumper, kickback or drop target switch tagged `playfield_active` | `... uses switch 's_pop_left' which has a 'playfield_active' tag. This is handled internally by the device. Remove the redundant 'playfield_active' tag from that switch.`, with `CFE-autofire-1`, `CFE-kickback-1` or `CFE-drop_target-1` | Remove the tag ([switches that report the ball themselves](/build/flippers-and-autofire/#switches-that-report-the-ball-themselves)). |

### Errors that only appear later

Some mistakes pass startup and stop MPF the first time the setting is used. These are the confusing ones: the machine
boots and runs attract mode normally.

| Mistake | When it fails | MPF says |
|---|---|---|
| A playfield without `default_source_device` | When a game starts | `Missing a source device to request a ball. Did you define a default_source_device in your playfield?` |
| `true`/`false` in lower case in a condition | When the event first arrives | `Placeholder use Python syntax. Use True and False instead of true and false.` ([conditions](/build/events/#conditions)) |
| A mode's player keyed to the mode's own start event | When the mode first starts | `Change the event_player: ball_started: event name to "mode_skillshot_started:"` ([how events work](/architecture/how-events-work/#who-is-listening)) |
| A single-wound flipper coil with no hold power | When the first ball starts | `Cannot enable driver with hold_power 0.0` ([flippers](/build/flippers-and-autofire/#single-wound-flipper)) |

After a config change, start a game and play a ball before trusting it.

Mode files have startup errors of their own (a listed mode with no file, a game mode that does not stop at ball end);
see [modes](/build/modes/).

## When it runs but does the wrong thing

### The game will not start

Press start and look for `request_to_start_game` in the log. Right after it, the ball controller says why it refused
(`mpf/core/ball_controller.py`):

- `BallController denies game start. Not enough balls. 0 found. 1 required`: MPF counts fewer balls than
  `machine: min_balls` (default 1). Check the trough's `BCH: Initial count:` line at startup. On the virtual platforms
  the trough starts empty unless `virtual_platform_start_active_switches` lists its switches; this was the run that
  produced the message above. On real hardware, check the trough switches and `type: NC` on optos.
- `BallController denies game start. Balls are not in their home positions.`: a ball is somewhere other than a device
  tagged `home` or `trough`. MPF tries to collect it. `game: allow_start_with_loose_balls: true` and
  `allow_start_with_ball_in_drain: true` relax this.

Custom code can also refuse a start (see [boolean events](/architecture/how-events-work/#boolean-asking-for-permission)).

### A switch does nothing

1. **Did MPF see it?** Every switch change is logged as `<<<<<<< 's_name' active >>>>>>>`, whether or not anything
   uses it. No line means a wiring, `number:` or platform problem, or an `NC` switch configured as `NO`.
2. **Was the event posted?** `<switch>_active` and `sw_<tag>` are only posted when something listens for them
   ([why](/build/switches-and-coils/#events-a-switch-posts)). If your handler is in a mode, it only listens while the
   mode runs.
3. **Did the handler run?** Look for the event your handler posts, or add `debug: true` to the device.

### A ball is not counted, or seems stuck

- With no playfield switch, a ball counts as on the playfield only after the eject timeout (10 s by default).
- Ball search is off unless `enable_ball_search: true`. See [ball devices](/build/ball-devices/#ball-search).

### Other surprises covered in the guides

| Symptom | Cause |
|---|---|
| A light effect repeats forever | `show_player` `loops` defaults to `-1`. [Shows](/build/shows/#playing-shows) |
| A shot group "completes" at ball start | All shots start unlit. Use `<group>_lit_complete`. [Shots](/build/shots-and-scoring/#shot-groups) |
| Score does not change in attract | There is no player outside a game. |
| A lower mode's score is ignored | A higher mode uses `\|block`. [Blocking](/build/shots-and-scoring/#blocking-lower-modes) |
| A condition on a counter is one hit late | Conditions see state from before the event. [Events](/build/events/#only-while-something-is-true) |
| A `ball_ending` handler never runs | It is in a mode that stopped at `ball_will_end`. [How events work](/architecture/how-events-work/#queue-holding-things-up) |
| `combo_switches: both_flippers` posts `flipper_cancel` | MPF already defines that device. [Events](/build/events/#both-flipper-buttons) |
