---
title: "Widgets and widget_player"
weight: 4
summary: "Put small scenes on top of a slide with widget_player: positioning, expiry, the overlay that sits above every slide, and what happens when slides and modes change."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

A **widget** is a scene that goes *on* a slide rather than replacing it: a "JACKPOT!" banner over the score, a "LOCK
LIT" tag in a corner. MPF plays widgets with `widget_player`, which works much like
[`slide_player`](/gmc/slides/).

{{< tip >}}
**Verified.** The machine at the end of this page was run with GMC and MPF together on the smart virtual platform,
with the switch hits scripted. The screenshots and events below are from those runs.
{{< /tip >}}

It builds on [Slides and slide_player](/gmc/slides/): the same `base` and `ramp_lit` slides, with two widgets and a
`lock` mode added.

## Making a widget

A widget is a scene whose root node is an `MPFWidget`, saved as a `.tscn` file in a `widgets/` folder (in the project,
or in `modes/<mode>/widgets/`). As with slides, the file name is the widget's name.

Unlike a slide, a widget isn't stretched over the screen. Give its root node the size the widget should be: in the
example, `jackpot` is 600 × 150 and `lock_lit` is 360 × 90, each a coloured `ColorRect` with a `Label` on it.
`widget_player` places the widget's top-left corner with `x` and `y` (`MPFWidget.initialize`).

## Playing widgets

```yaml
widget_player:
  s_ramp_active:
    jackpot:
      x: 276
      y: 400
      expire: 3s
```

| Setting | Default | What it does |
|---|---|---|
| `action` | `play` | `play` or `remove`; also `update`, `animation`, `method` and `preload`, as for slides. |
| `slide` | the active slide | Which slide to put the widget on: a slide's name, or `_overlay` (see [below](#the-overlay)). |
| `x`, `y` | `0` | Position of the widget's top-left corner on the slide, in pixels. |
| `expire` | none | Remove the widget this long after it was played. |
| `priority` | `0` | Added to the mode's priority; orders widgets on the same slide (higher is drawn on top). |
| `key` | the widget's name | An identity for this copy of the widget. Two entries with different keys put two copies on screen; `remove` and `update` find the widget by key (`MPFSceneBase.process_action`). |
| `target` | the default display | Which display. |
| `tokens` | none | Values for the widget's `MPFVariable` labels, as on [slides](/gmc/variables/#values-from-events-and-tokens). |

`priority`, `key` and `target` weren't run for this page.

In the test run, the ramp put `jackpot` on the base slide where `x` and `y` said:

![The JACKPOT! widget on the base slide](/images/gmc/widget-on-base.png)

## A widget belongs to its slide

Without a `slide:` setting, a widget goes on whichever slide is active when it's played, and stays on that slide. It
doesn't move to the next slide.

In the test run a target hit played `ramp_lit` half a second after the jackpot widget appeared. `ramp_lit` covered the
whole screen, including the widget, which was still on `base` underneath. When `ramp_lit` expired a second later,
`base` was back on top with the widget still on it, and the widget went away at its own 3-second `expire`.

To put a widget on a particular slide, name it with `slide:`. That slide has to be in the stack: in a test run, a
widget aimed at `slide: attract` during a game wasn't shown, and GMC logged `Unable to add widget 'jackpot' because
target slide 'attract' is not on this display.`

When a slide is removed, its widgets go with it, since they're part of the slide's scene (read from the code).

## The overlay

`slide: _overlay` puts the widget on a layer above every slide on the display (`MPFDisplay._get_overlay_slide`). It
stays put while slides come and go underneath. That suits things like "LOCK LIT", which should stay visible whatever
slide is playing.

```yaml
widget_player:
  mode_lock_started:
    lock_lit:
      slide: _overlay
      x: 760
      y: 30
```

In the test run `lock_lit` stayed in the corner when `ramp_lit` played over `base`:

![LOCK LIT on the overlay, above the RAMP LIT slide](/images/gmc/widget-overlay.png)

{{< warn >}}
**Overlay widgets aren't removed when their mode stops.** Widgets on ordinary slides go when the mode that played them
stops, like slides do (read from the code). Widgets on `_overlay` don't: GMC clears a stopped mode's widgets only from the slides in the
stack, and the overlay isn't one of them (`MPFDisplay._on_clear`). In the test run, `lock_lit` was still on screen
after the `lock` mode stopped, and GMC posted no `widget_lock_lit_removed`:

![LOCK LIT still showing after the lock mode stopped](/images/gmc/widget-overlay-left-behind.png)

Remove overlay widgets yourself. The example does it from the `base` mode, which is still running when `lock` stops:

```yaml
widget_player:
  mode_lock_stopped:
    lock_lit:
      slide: _overlay
      action: remove
```

With that entry, GMC posted `widget_lock_lit_removed` as the mode stopped and the corner was clear. An `expire` on the
widget is another way out.
{{< /warn >}}

## Events GMC sends back

| Event | When |
|---|---|
| `widget_<name>_active` | The widget was added. Carries the arguments of the event that played it. |
| `widget_<name>_removed` | The widget was removed (by `remove`, `expire` or its mode stopping). |

`<name>` is the widget's name, not its `key`. In the test run, `widget_jackpot_removed` came 3.0 seconds after
`widget_jackpot_active`, from the `expire`.

## The complete machine

The machine config is the one from [Slides and slide_player](/gmc/slides/#the-complete-machine), with a third mode and
switch:

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - lock

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
  s_target_active:
    ramp_lit:
      priority: 10
      expire: 1s

widget_player:
  s_ramp_active:
    jackpot:
      x: 276
      y: 400
      expire: 3s
  mode_lock_stopped:
    lock_lit:
      slide: _overlay
      action: remove
```

`modes/lock/config/lock.yaml`:

```yaml
#config_version=6

mode:
  start_events: s_lock_active
  stop_events: s_ramp_active
  priority: 200

widget_player:
  mode_lock_started:
    lock_lit:
      slide: _overlay
      x: 760
      y: 30
```

The slides are `slides/base.tscn` and `slides/ramp_lit.tscn` from the [slides page](/gmc/slides/#the-complete-machine).
The widgets:

`widgets/jackpot.tscn`:

```ini
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_widget.gd" id="1_widget"]

[node name="jackpot" type="Control"]
layout_mode = 3
anchors_preset = 0
offset_right = 600.0
offset_bottom = 150.0
script = ExtResource("1_widget")

[node name="Panel" type="ColorRect" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
color = Color(0.9, 0.75, 0.0, 1)

[node name="Title" type="Label" parent="Panel"]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_colors/font_color = Color(0, 0, 0, 1)
theme_override_font_sizes/font_size = 72
text = "JACKPOT!"
horizontal_alignment = 1
vertical_alignment = 1
```

`widgets/lock_lit.tscn`:

```ini
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_widget.gd" id="1_widget"]

[node name="lock_lit" type="Control"]
layout_mode = 3
anchors_preset = 0
offset_right = 360.0
offset_bottom = 90.0
script = ExtResource("1_widget")

[node name="Panel" type="ColorRect" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
color = Color(0.1, 0.4, 0.9, 1)

[node name="Title" type="Label" parent="Panel"]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 48
text = "LOCK LIT"
horizontal_alignment = 1
vertical_alignment = 1
```
