---
title: "Events between MPF and Godot"
weight: 7
summary: "React to MPF events in Godot with MPFEventHandler or a script, call a slide's own code from slide_player, send events back to MPF, and map keyboard keys to switches."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

The players on the earlier pages (`slide_player`, `widget_player`, `sound_player`) cover most of what a display does.
When a slide needs to do something of its own (count, animate, pick a random award), Godot code takes over. This
page covers the four connections between MPF and that code:

| Direction | How |
|---|---|
| MPF event → Godot code | An `MPFEventHandler` node, or `MPF.server.add_event_handler()` in a script. |
| MPF config → a slide's code | `slide_player` with `action: method`. |
| Godot code → MPF | `MPF.server.send_event()` and `send_event_with_args()`. |
| Keyboard → MPF | A `[keyboard]` section in `gmc.cfg`. |

{{< tip >}}
**Verified.** The machine at the end of this page was run with GMC and MPF together on the smart virtual platform,
with the switch hits scripted and a key press simulated in Godot. The screenshots and events below are from that run.
{{< /tip >}}

The example is a mystery award: the ramp shows a `mystery` slide, the target makes it "spin" for a second in Godot,
and Godot then tells MPF what was won. A lock switch, pressed from the keyboard, lights a jackpot that the base slide
shows.

## Reacting to an MPF event in Godot

### With an MPFEventHandler node

An **`MPFEventHandler`** node subscribes to one MPF event and calls a method when it happens. Add it as a child of the
node that should react:

| Property | What it does |
|---|---|
| **Event Name** | The MPF event to listen for. |
| **Handler Direction** | `Parent` (default): call the method on this node's parent. `Children`: call it on each of its children. |
| **Call Method** | The method to call. It gets one argument: a dictionary of the event's arguments. |

In the example the base slide has a `Label` called `Jackpot` with this script, and an `MPFEventHandler` child with
Event Name `jackpot_lit` and Call Method `show_jackpot`:

`slides/jackpot_label.gd`:

```gdscript
extends Label

# Called by the MPFEventHandler child when MPF posts jackpot_lit.
func show_jackpot(payload: Dictionary) -> void:
	text = "JACKPOT LIT: %s" % payload.get("value", "?")
```

MPF posts the event with an argument, from the base mode's `event_player`:

```yaml
event_player:
  s_lock_active:
    jackpot_lit:
      value: 25000
```

In the test run, the lock switch filled in the label:

![The base slide showing JACKPOT LIT: 25000](/images/gmc/events-jackpot-lit.png)

The handler only listens while its slide is in the stack: it subscribes when the slide is created and unsubscribes when
it's removed (`MPFEventHandler._ready` and `_exit_tree`). A slide that's in the stack but covered by another still
gets events: in the test run the base slide's `mystery_done` handler ran while the `mystery` slide covered it. If the target node has no method of that name, GMC logs a warning instead (read from the code).

### From a script

The node is a wrapper around `MPF.server.add_event_handler(event_name, callable)`, which any script can call. The
callable gets the same dictionary. Remove the handler with `MPF.server.remove_event_handler()` when the node goes away,
as `MPFEventHandler` does. GMC asks MPF to send it an event only once something has subscribed to it.

## Calling a slide's code from slide_player

`action: method` calls a function on a slide that's in the stack, by name:

```yaml
slide_player:
  s_ramp_active:
    mystery:
      priority: 10
      expire: 4s
  s_target_active:
    mystery:
      action: method
      method: spin
      tokens:
        points: "5000"
```

The slide's root node needs a script that extends `MPFSlide` and has that function. It's called with two
dictionaries: the `slide_player` settings (including `tokens`) and the arguments of the event
(`MPFSceneBase.process_action`):

`slides/mystery.gd`:

```gdscript
extends MPFSlide

# Called by slide_player with `action: method` and `method: spin`.
func spin(settings: Dictionary, kwargs: Dictionary) -> void:
	$Result.text = "SPINNING..."
	await get_tree().create_timer(1.0).timeout
	var points: int = int(settings.get("tokens", {}).get("points", "1000"))
	$Result.text = "MYSTERY: %s" % points
	MPF.server.send_event_with_args("mystery_done", {"points": points})
```

In the test run the target hit started the spin:

![The mystery slide reading SPINNING...](/images/gmc/events-spinning.png)

If the slide isn't in the stack, or its script has no function of that name, `method` does nothing. Widgets take
`action: method` too. (Both read from the code.)

## Sending events to MPF

The last line of `spin` sends an event back to MPF. Two functions do it:

| Function | Sends |
|---|---|
| `MPF.server.send_event("name")` | The event with no arguments. |
| `MPF.server.send_event_with_args("name", {"key": value})` | The event with arguments. `name` is reserved: an argument called `name` is dropped with a warning (read from the code). |

MPF posts it like any other event, so any config can react. The base mode scores the award:

```yaml
variable_player:
  mystery_done:
    score: 5000
```

In the test run, MPF logged `mystery_done` with `points: 5000` (and `_from_bcp: True`, marking it as sent by GMC) one
second after the target hit, and the score went to 5,000 in the same moment.

Godot's own handlers for an event Godot sends are called directly, without a round trip through MPF
(`GMCServer._bounceback`), and MPF doesn't send it back. The base slide in the example has a second `MPFEventHandler`,
on `mystery_done`, that counts its calls; after the spin it read `MYSTERY DONE x1: 5000`:

![The base slide after the mystery: 5,000, JACKPOT LIT: 25000, MYSTERY DONE x1: 5000](/images/gmc/events-done.png)

GDScript can also set a machine variable in MPF with `MPF.server.set_machine_var(name, value)`, and press a switch with
`MPF.server.send_switch(name, state)`; neither was run for this page.

## Keyboard keys

A `[keyboard]` section in `gmc.cfg` maps keys to switches or events, which is useful at a desk with no machine. Each
line is a key name, then a list:

`gmc.cfg`:

```ini
[cli]
godot_exec_path="C:/Tools/Godot/Godot_v4.7.2-stable_win64.exe"

[gmc]
exit_on_esc=true

[keyboard]
l=["switch", "s_lock"]
```

| Value | What the key does (`MPFGMC._input`) |
|---|---|
| `["switch", "s_name"]` | The switch is active while the key is held, inactive when it's released. |
| `["switch", "s_name", "toggle"]` | Each press flips the switch. `"active"` or `"inactive"` instead sets it on each press. |
| `["event", "name"]` | Each press posts the event in MPF. |
| `["event", "name", {"key": value}]` | Each press posts the event with arguments. |

Key names are Godot's names for the key, and aren't case-sensitive: `l`, `space`, `enter`, `left`. Holding a key down
doesn't repeat it. (Read from the code; only `l` was run.) As with any program, the GMC window needs keyboard focus.

In the test run a simulated press and release of L sent `s_lock` to MPF, which posted `s_lock_active` and then
`jackpot_lit`. Only the plain `["switch", ...]` form was run.

## The complete machine

The machine config adds an `s_lock` switch to the one from
[Slides and slide_player](/gmc/slides/#the-complete-machine); `gmc.cfg`, `jackpot_label.gd` and `mystery.gd` are
above.

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
  s_ramp:
    number:
    tags: playfield_active
  s_target:
    number:
    tags: playfield_active
  s_lock:
    number:
    tags: playfield_active

coils:
  c_trough_eject:
    number:

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

virtual_platform_start_active_switches: s_trough1
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
  s_ramp_active:
    mystery:
      priority: 10
      expire: 4s
  s_target_active:
    mystery:
      action: method
      method: spin
      tokens:
        points: "5000"

event_player:
  s_lock_active:
    jackpot_lit:
      value: 25000

variable_player:
  mystery_done:
    score: 5000
```

The counter on the base slide:

`slides/done_label.gd`:

```gdscript
extends Label

var count := 0

# Called by the MPFEventHandler child when mystery_done is posted.
func on_done(payload: Dictionary) -> void:
	count += 1
	text = "MYSTERY DONE x%d: %s" % [count, payload.get("points", "?")]
```

`slides/base.tscn`:

```ini
[gd_scene load_steps=6 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_variable.gd" id="2_var"]
[ext_resource type="Script" path="res://slides/jackpot_label.gd" id="3_jackpot"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_event_handler.gd" id="4_handler"]
[ext_resource type="Script" path="res://slides/done_label.gd" id="5_done"]

[node name="base" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1_slide")

[node name="Background" type="ColorRect" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
color = Color(0.05, 0.25, 0.12, 1)

[node name="Lines" type="VBoxContainer" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
alignment = 1

[node name="Player" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 40
horizontal_alignment = 1
script = ExtResource("2_var")
variable_name = "number"
template_string = "PLAYER %s"

[node name="Score" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 120
horizontal_alignment = 1
script = ExtResource("2_var")
variable_name = "score"
comma_separate = true

[node name="Credits" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 36
horizontal_alignment = 1
script = ExtResource("2_var")
variable_type = 2
variable_name = "credits_string"

[node name="Jackpot" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 48
horizontal_alignment = 1
script = ExtResource("3_jackpot")

[node name="OnJackpotLit" type="Control" parent="Lines/Jackpot"]
layout_mode = 3
anchors_preset = 0
script = ExtResource("4_handler")
event_name = "jackpot_lit"
call_method = "show_jackpot"

[node name="Done" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 36
horizontal_alignment = 1
script = ExtResource("5_done")

[node name="OnMysteryDone" type="Control" parent="Lines/Done"]
layout_mode = 3
anchors_preset = 0
script = ExtResource("4_handler")
event_name = "mystery_done"
call_method = "on_done"
```

`slides/mystery.tscn`:

```ini
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://slides/mystery.gd" id="1_mystery"]

[node name="mystery" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1_mystery")

[node name="Background" type="ColorRect" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
color = Color(0.3, 0.1, 0.4, 1)

[node name="Result" type="Label" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 96
text = "MYSTERY"
horizontal_alignment = 1
vertical_alignment = 1
```
