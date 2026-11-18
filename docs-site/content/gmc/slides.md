---
title: "Slides and slide_player"
weight: 3
summary: "Make slides in Godot, play and remove them from MPF with slide_player, and how GMC's slide stack decides what is on screen."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

A **slide** is a full-screen Godot scene. MPF decides when slides come and go with `slide_player`; GMC keeps every
slide that is playing in a **stack** and shows the one with the highest priority on top. This page builds a small
machine with three slides and walks through what GMC did with them.

{{< tip >}}
**Verified.** The machine at the end of this page was run with GMC and MPF together on the smart virtual platform,
with the switch hits scripted. The screenshots and event orders below are from that run.
{{< /tip >}}

It starts from the project on [Install GMC and connect it to MPF](/gmc/install-and-connect/): `project.godot`,
`gmc.cfg`, the add-on and the `attract` slide stay as they were.

## Making a slide

A slide is a scene whose root node is an `MPFSlide`, saved as a `.tscn` file. Its file name is its name: GMC looks
through these folders when it starts and maps each scene's file name to its path (`GMCMedia.traverse_tree_for`):

| Folder | Example | Slide name |
|---|---|---|
| `slides/` in the project | `slides/base.tscn` | `base` |
| `modes/<mode>/slides/` | `modes/skillshot/slides/skillshot.tscn` | `skillshot` |
| GMC's own `addons/mpf-gmc/slides/` | `bonus.tscn`, `tilt.tscn`, `high_score.tscn` ... | used only if your project has no slide of that name |

Subfolders are searched too, but the name is still just the file name: if two slides in different folders have the
same file name, one replaces the other in GMC's list. To keep slides under another folder, set `content_root` in the `[gmc]` section of `gmc.cfg`;
GMC then looks in `<content_root>/slides/` instead of `slides/`.

Anything a Godot scene can hold can go on a slide: labels, images, video, animation, shaders. The slides on this page
are a coloured background and a label each. The `skillshot` slide has **no background**, just a banner across the
bottom, so whatever is underneath it shows through.

`base` and `ramp_lit` are built like the attract slide in [the install guide](/gmc/install-and-connect/#5-add-an-attract-slide),
with a different colour and text. To build `skillshot`:

1. Make a new scene with an `MPFSlide` root named `skillshot`, anchored **Full Rect**, as before. Don't add a
   background.
2. Add a `ColorRect` child named `Banner`. In the anchor preset menu, choose **Bottom Wide**, then drag its top edge up
   in the 2D view to make it 220 pixels tall (or set **Size** under **Layout > Transform** in the Inspector). Pick a
   **Color**.

   ![The skillshot slide with Banner selected: a purple banner across the bottom of an otherwise empty slide](/images/gmc/editor/slides-skillshot-banner.png)

   ![The Inspector filtered to "anchor", showing the Bottom Wide anchor preset](/images/gmc/editor/slides-skillshot-banner-anchors.png)

3. Add a `Label` as a child of **`Banner`**, not of the slide: select `Banner` before clicking **+**. Name it
   `Title`, set its text and font size, centre it, and anchor it **Full Rect**, which now means "fill the banner".

   ![The scene tree with Title nested under Banner, and the label filling the banner](/images/gmc/editor/slides-skillshot-title.png)

4. Save it as `slides/skillshot.tscn`.

## Playing slides

`slide_player` goes in a mode's config (or the machine config, or a show). Each entry is an event, then the slide to
play:

```yaml
slide_player:
  mode_base_started: base
```

That's the short form. The long form puts settings under the slide name:

```yaml
slide_player:
  s_ramp_active:
    ramp_lit:
      priority: 10
      expire: 3s
  s_target_active:
    ramp_lit:
      action: remove
```

| Setting | Default | What it does |
|---|---|---|
| `action` | `play` | `play` adds the slide to the stack; `remove` takes it off. Other actions are listed [below](#other-actions). |
| `priority` | `0` | Added to the priority of the mode that plays the slide. |
| `expire` | none | Remove the slide this long after it was played. |
| `target` | the default display | Which display to play on, for machines with more than one. |
| `tokens` | none | Extra values for the slide's variables (see [Showing scores and variables](/gmc/variables/#values-from-events-and-tokens)). |

`transition` and `transition_out` are accepted, because MPF's config spec still lists them (as `ignore`), but GMC
doesn't use them. Slides animate with Godot animations instead.

## The slide stack

Each slide's priority is the priority of the mode that played it, plus its own `priority` setting
(`MPFSceneBase.initialize`). Every time a slide is added or removed, GMC sorts the stack and makes the highest-priority
slide the **active** one, drawn on top (`MPFDisplay._update_stack`). The slides below it are still there and still
drawn, underneath.

In the example machine, `base` (priority 100) starts with the ball, and the `skillshot` mode (priority 200) puts its
slide on top a moment later. The banner covers only the bottom of the screen, so `base` shows above it:

![The skillshot banner on top, with the base slide showing through above it](/images/gmc/skillshot-over-base.png)

A slide doesn't have to be on top to be played. Hitting the ramp during the skill shot played `ramp_lit` at 100 + 10 =
110: higher than `base`, lower than `skillshot`. It went into the stack under the banner, and since `ramp_lit` fills the
screen it hid `base`:

![The skillshot banner still on top, now over the ramp_lit slide](/images/gmc/skillshot-over-ramp.png)

## How slides go away

### When the mode stops

A slide belongs to the mode that played it. When that mode stops, MPF sends GMC a `slides_clear` for the mode, and GMC
removes all of that mode's slides (`MPFDisplay._on_clear`). The skill shot needs no `remove` entry: in the test run,
hitting the target stopped the `skillshot` mode and its banner went with it, leaving whatever was next in the stack.

### With `action: remove`

`remove` takes a slide off before its mode stops. In the test run the same target hit also removed `ramp_lit` (the
`s_target_active` entry above), so the screen went back to `base`.

### With `expire`

`expire: 3s` removes the slide three seconds after it was played. Playing a slide that is already in the stack doesn't
add a second copy: GMC keeps the one it has, and if the entry has an `expire`, starts its countdown again
(`MPFSceneBase._create_expire`). In the test run the ramp was hit twice, two seconds apart. There was one `ramp_lit`,
still showing four seconds after the first hit, and it was removed 3.0 seconds after the **second** hit.

### When nothing is left

If the last slide on a display is removed, the display keeps showing it until a new slide arrives, rather than going
blank. Turn on **Allow Empty** on the `MPFDisplay` node to let the display empty instead (`MPFDisplay.allow_empty`).
This was read from the code, not run.

## Events GMC sends back

GMC tells MPF what it did with each slide by posting events, which MPF handles like any other event (they arrive with
`_from_bcp: True` in the log). You can use them in any config, for example to play a sound when a slide goes away.

| Event | When |
|---|---|
| `slide_<name>_created` | The slide was added to the stack. |
| `slide_<name>_active` | The slide became the active slide (top of the stack). Carries the arguments of the event that played it. |
| `slide_<name>_inactive` | The slide stopped being the active slide. `is_removing` is `True` if it is also being removed. |
| `slide_<name>_removed` | The slide is gone. |

The order, from the test run, when the ball started:

```text
slide_base_created
slide_attract_inactive    is_removing: True
slide_base_active
slide_attract_removed
slide_skillshot_created
slide_base_inactive       is_removing: False
slide_skillshot_active
```

`_active` is only posted for the slide that becomes the top one. When `ramp_lit` was played under the skill shot banner,
GMC posted `slide_ramp_lit_created` and nothing else; `slide_ramp_lit_active` came only on the later ramp hits, with
nothing above it.

## Other actions

| `action` | What it does | Where |
|---|---|---|
| `update` | Send new values to a slide's variables. | [Showing scores and variables](/gmc/variables/#changing-values-on-a-slide-thats-showing) |
| `method` | Call a function on the slide's script, passing the settings and event arguments. | A later page |
| `animation` | Play a named animation from the slide's `AnimationPlayer`. | A later page |
| `preload` | Load the slide's scene ahead of time without showing it. | `MPFWindow._play_scene` |
| `queue`, `queue_first`, `queue_immediate` | Play slides one after another instead of stacking them, with `queue` and `max_queue_time`. | `MPFDisplay.action_queue` |

These weren't run for this page, except `update`, which is on the variables page.

## What is not on this page

- **Widgets**, which go on top of a slide instead of replacing it: see [Widgets and widget_player](/gmc/widgets/).
- **Animations** when a slide is created, becomes active or is removed.
- **More than one display** (`target`).

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - skillshot

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
    ramp_lit:
      priority: 10
      expire: 3s
  s_target_active:
    ramp_lit:
      action: remove
```

`modes/skillshot/config/skillshot.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_started
  stop_events: s_target_active
  priority: 200

slide_player:
  mode_skillshot_started: skillshot
```

The three slides, as saved by the editor. `base` and `ramp_lit` are a full-screen `ColorRect` and a `Label`;
`skillshot` is a `ColorRect` banner anchored to the bottom, with a `Label` inside it and nothing behind it.

{{< scenefile "slides/base.tscn" >}}
`slides/base.tscn`:

```ini
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]

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

[node name="Title" type="Label" parent="."]
layout_mode = 1
anchors_preset = 10
anchor_right = 1.0
offset_top = 60.0
offset_bottom = 200.0
grow_horizontal = 2
theme_override_font_sizes/font_size = 80
text = "BALL IN PLAY"
horizontal_alignment = 1
vertical_alignment = 1
```
{{< /scenefile >}}

{{< scenefile "slides/ramp_lit.tscn" >}}
`slides/ramp_lit.tscn`:

```ini
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]

[node name="ramp_lit" type="Control"]
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
color = Color(0.8, 0.35, 0.0, 1)

[node name="Title" type="Label" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 110
text = "RAMP LIT"
horizontal_alignment = 1
vertical_alignment = 1
```
{{< /scenefile >}}

{{< scenefile "slides/skillshot.tscn" >}}
`slides/skillshot.tscn`:

```ini
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]

[node name="skillshot" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1_slide")

[node name="Banner" type="ColorRect" parent="."]
layout_mode = 1
anchors_preset = 12
anchor_top = 1.0
anchor_right = 1.0
anchor_bottom = 1.0
offset_top = -220.0
grow_horizontal = 2
grow_vertical = 0
color = Color(0.6, 0.0, 0.4, 1)

[node name="Title" type="Label" parent="Banner"]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 72
text = "SKILL SHOT!"
horizontal_alignment = 1
vertical_alignment = 1
```
{{< /scenefile >}}
