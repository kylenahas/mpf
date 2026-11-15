---
title: "BCP: talking to a media controller"
weight: 7
summary: "The Backbox Control Protocol between MPF and GMC: who connects to whom, the message format, what MPF sends during a game, and what a media controller can ask MPF to do."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

MPF runs the rules; a media controller such as [GMC](/gmc/) draws the screens and plays the sounds. They're separate
programs that talk over a network connection using **BCP**, the Backbox Control Protocol. This page explains what
travels over that connection, which helps when a slide doesn't appear, when you write your own media controller, or
when you want to drive MPF from another program.

{{< tip >}}
**Verified.** The machine on this page was run on MPF 0.82.0.dev0 with `MpfGameTestCase`, connected to MPF's own mock
BCP client (`mpf/tests/MpfBcpTestCase.py`) that subscribed the way GMC 1.0.0 does. Every message below was recorded
from that run. `docs-site/verify/test_guides.py` repeats it.
{{< /tip >}}

## Who connects to whom

The media controller is the **server**: GMC listens on port 5050. MPF is the **client**: it connects to it at startup.
The connection comes from MPF's own `mpfconfig.yaml`:

```yaml
bcp:
  connections:
    local_display:
      host: localhost
      port: 5050
      type: mpf.core.bcp.bcp_socket_client.BCPClientSocket
      required: true
      exit_on_close: true
```

- `required: true` makes MPF keep trying until it connects, without a time limit, so MPF waits for GMC at startup.
- `exit_on_close: true` stops MPF when the media controller closes.
- `mpf game -b` skips the connection, for running MPF without a media controller.

Your machine config can change these under `bcp: connections:`, for example to connect to a media controller on
another computer.

## The message format

Each message is one line of text: a command, then `?` and URL-style parameters
(`mpf/core/bcp/bcp_socket_client.py`). Values that aren't strings carry their type, so the other side gets the right
kind of value back:

```text
player_variable?name=score&value=int:1000&prev_value=int:0&change=int:1000&player_num=int:1
```

The prefixes are `int:`, `float:`, `bool:` and `NoneType:`. A message with a list or dictionary among its parameters is
sent as JSON instead:

```text
trigger?json={"name": "slides_play", "settings": {"base": {"action": "play"}}, "context": "base"}
```

Both lines above were made with MPF's own encoder, `encode_command_string`, and decoded back to the same values with
`decode_command_string`.

## Connecting

When the connection opens, both sides send `hello`. MPF then sends `reset`, and the media controller answers
`reset_complete` (`BCPClientSocket` in MPF, `bcp_server.gd` in GMC). A media controller then tells MPF what it wants to
hear about. MPF only sends most messages to clients that asked for them. GMC 1.0.0 asks for:

```text
monitor_start?category=core_events
monitor_start?category=service_events
monitor_start?category=modes
monitor_start?category=player_vars
monitor_start?category=machine_vars
register_trigger?event=carousel_item_highlighted
register_trigger?event=text_input
register_trigger?event=bonus_entry
```

plus a `register_trigger` for each event an `MPFEventHandler` node in your project listens to (see
[Events between MPF and Godot](/gmc/events/)).

## What MPF sends during a game

In the test run, after those subscriptions, a game sent:

| When | Messages |
|---|---|
| The subscriptions arrive | `mode_list` (attract running), `machine_variable` for each machine variable (`credits_string`, `mpf_version`, ...), `settings` |
| A game starts | `mode_start` for `game`, `player_added`, `player_variable` for `index`, `number`, `score` and `ball`, `player_turn_start`, `mode_start` for `base`, `ball_start` |
| Whenever the running modes change | `mode_list` with every running mode and its priority |
| The ramp scores | `player_variable` for `score`, with `value`, `prev_value` and `change` |
| A registered event is posted | `trigger` with the event's name and arguments: `trigger?name=ramp_made` |
| The ball drains | `mode_stop` for `base`, `ball_end`, `player_variable` for `ball`, then the next ball's `player_turn_start`, `mode_start` and `ball_start` |

Without the `modes` and `core_events` subscriptions, none of the mode, player and ball messages were sent; only the
player variables (after `monitor_start?category=player_vars`) and the slide triggers below.

### Slides, widgets and sounds

`slide_player`, `widget_player` and `sound_player` don't do anything inside MPF. Each entry is sent to the media
controller as a `trigger` named after the player. In the test run, the `base` mode's `slide_player` sent:

```text
trigger?json={"name": "slides_play", "settings": {"base": {"action": "play", "priority": null, ...}}, "context": "base", ...}
```

and when the mode stopped, `trigger?name=slides_clear&context=base`, which tells the media controller to remove the
slides that mode put up. The attract mode's slide was sent the same way at startup, before any subscription: these
triggers always go to the media controller. So if a slide doesn't show, the first thing to check is whether MPF sent
`slides_play` for it, for example with `bcp: debug: true` in the machine config, which turns on BCP's debug
logging.

## What a media controller can send

These are the commands MPF accepts (`BcpInterface.bcp_receive_commands` in `mpf/core/bcp/bcp_interface.py`):

| Command | What MPF does |
|---|---|
| `trigger?name=<event>&...` | Posts the event, with the other parameters as arguments. |
| `register_trigger?event=<event>`, `remove_trigger?event=<event>` | Starts or stops sending `trigger` messages for that event. |
| `monitor_start?category=<category>`, `monitor_stop?...` | Starts or stops a category: `events`, `devices`, `drivers`, `switches`, `machine_vars`, `player_vars`, `modes`, `core_events`, `service_events`, `status_request`. |
| `switch?name=<switch>&state=<1, 0 or -1>` | Sets a switch active, inactive, or to the opposite of what it is. GMC's keyboard mapping uses this. |
| `set_machine_var?name=<name>&value=<value>` | Sets a machine variable. |
| `evaluate_placeholder?...` | Evaluates a placeholder and sends the result back. |
| `service?subcommand=...` | Service mode functions. |
| `reset_complete`, `error` | Part of the handshake; error reporting. |

In the test run, the client's `switch?name=s_ramp&state=1` then `state=0` scored the ramp exactly as a real hit did,
and `trigger?name=client_event&value=int:5` posted `client_event` with `value: 5`. MPF added `_from_bcp: True` to the
arguments, and didn't send the event out again, although the client had registered for `client_event`: events that
came in over BCP are never sent back out, which prevents loops (`BcpInterface.bcp_trigger`).

## Other connections

MPF also runs a BCP **server** of its own, on port 5051 (`bcp: servers:` in `mpfconfig.yaml`), for other programs to
connect to MPF. A tool or a second display can use the commands above through it. The test run disabled it, as MPF's
test classes do.


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

slide_player:
  mode_base_started: base

variable_player:
  s_ramp_active:
    score: 1000

event_player:
  s_ramp_active: ramp_made
```
