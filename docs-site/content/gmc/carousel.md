---
title: "Choosing from a list: carousels"
weight: 7
summary: "Let the player pick from a list with the flippers using MPF's Carousel mode and GMC's MPFCarousel node: an award chooser at the start of a ball."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

A **carousel** lets the player choose one thing from a list: an award at the start of a ball, the next mission, a
mystery prize. The flippers move through the list and another button chooses. It takes one piece on each side:

- **In MPF**, a mode that uses the built-in `Carousel` code keeps track of which item is highlighted and posts events
  as the player moves and chooses.
- **In GMC**, an `MPFCarousel` node on a slide shows the child that matches the highlighted item and hides the rest.

This page builds an award chooser that runs at the start of each ball.

{{< tip >}}
**Verified.** The machine at the end of this page was run with GMC and MPF together on the smart virtual platform,
with the flipper and button presses scripted. The screenshots and events below are from that run.
{{< /tip >}}

It builds on [Showing scores and variables](/gmc/variables/): the same `base` slide, with flipper and launch-button
switches and an `award_select` mode added.

## The carousel mode

A carousel is a mode whose `code:` is MPF's `Carousel` class. Its `mode_settings` say what the items are and which
events move and choose:

`modes/award_select/config/award_select.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_started
  stop_events: carousel_item_selected{carousel=="award_select"}
  code: mpf.modes.carousel.code.carousel.Carousel
  priority: 200

mode_settings:
  selectable_items: extra_points, light_lock, double_scoring
  next_item_events: s_right_flipper_active
  previous_item_events: s_left_flipper_active
  select_item_events: s_launch_active

slide_player:
  mode_award_select_started: award_select
```

| `mode_settings` | Default | What it does |
|---|---|---|
| `selectable_items` | required | The items, in order. Each can have a [condition](/build/events/#conditions), see [below](#items-that-depend-on-the-game). |
| `next_item_events` | none | Events that move to the next item. |
| `previous_item_events` | none | Events that move to the previous item. |
| `select_item_events` | none | Events that choose the highlighted item. |
| `wrap_items` | `true` | Go from the last item to the first (and back). With `false`, moving past the end does nothing. |
| `block_events`, `release_events` | none | While a block event has happened and no release event since, next and previous are ignored. |

The mode posts two events (`Carousel` in `mpf/modes/carousel/code/carousel.py`):

| Event | Arguments | When |
|---|---|---|
| `carousel_item_highlighted` | `carousel` (the mode's name), `item`, `direction` (`forwards`, `backwards`, or `None` when the mode starts) | The mode started, or the player moved. |
| `carousel_item_selected` | `carousel`, `item` | The player chose. |

Choosing doesn't stop the mode by itself; the `stop_events` above do it. The `{carousel=="award_select"}` condition
keeps another carousel's choice from stopping this one. If the mode kept running after a choice, it would ignore
further moves and choices until it was started again (read from the code).

## Acting on the choice

`carousel_item_selected` is an ordinary event, so any config can react to it. Conditions on `item` pick out each
choice. The base mode gives the award:

```yaml
variable_player:
  carousel_item_selected{item=="extra_points"}:
    score: 5000
  carousel_item_selected{item=="light_lock"}:
    lock_lit: 1
  carousel_item_selected{item=="double_scoring"}:
    score_multiplier: 2
```

In a real game these would start a mode or light a shot; here they set player variables, and the 5,000 points show on
the base slide.

## The slide

The slide has an **`MPFCarousel`** node (add a child node and pick it; it's a `Control`) with one child per item.
**Each child's name must be the item's name.** GMC listens for `carousel_item_highlighted`, shows the child whose name
is the `item`, and hides the others (`MPFCarousel._on_item_highlighted`). The children can be anything: a label, an
image, a whole layout in a container.

| Property | What it does |
|---|---|
| **Carousel Name** | The carousel mode's name, matched against the event's `carousel` argument. If it's empty, the node's own name is used. |

To build `award_select.tscn`:

1. Make a slide named `award_select` with a background and a title, as in [Slides](/gmc/slides/#making-a-slide).
2. Add a child, pick **MPFCarousel**, rename it `Awards` and anchor it **Full Rect**.

   ![The Create New Node dialog with MPFCarousel found under Control](/images/gmc/editor/carousel-create-mpfcarousel.png)

3. In the Inspector, set its **Carousel Name** to `award_select`, the carousel mode's name.

   ![The Inspector for Awards: MPFCarousel with Carousel Name award_select](/images/gmc/editor/carousel-awards-inspector.png)

4. Add a `Label` child to `Awards` for each item, named exactly as the item: `extra_points`, `light_lock` and
   `double_scoring`. Give each its text, size and centring.

   ![The award_select slide in the editor, with the three item labels under Awards drawn on top of each other](/images/gmc/editor/carousel-awards.png)

In the editor all three items are visible at once, drawn on top of each other. That's expected: GMC hides all but the
highlighted one when the slide runs. While you work on one item, click the eye icons in the Scene panel to hide the
others; GMC sets each item's visibility itself, so it doesn't matter how you leave them.

## What happened in the test run

When the ball started, the `award_select` mode started and played its slide, with the first item showing:

![The award chooser with 5,000 POINTS highlighted](/images/gmc/carousel-first.png)

The `slide_player` entry plays the slide on `mode_award_select_started`, which MPF posted just before the first
`carousel_item_highlighted`, so the slide was already there to catch it.

One right flipper press later:

![The award chooser with LIGHT LOCK highlighted](/images/gmc/carousel-next.png)

| Press | `item` | `direction` |
|---|---|---|
| (mode start) | `extra_points` | `None` |
| right | `light_lock` | `forwards` |
| right | `double_scoring` | `forwards` |
| right | `extra_points` | `forwards` (wrapped round) |
| left | `double_scoring` | `backwards` (wrapped round) |
| left, left | `light_lock`, then `extra_points` | `backwards` |
| launch | `carousel_item_selected` with `extra_points` | |

The choice stopped the mode, its slide went with it (see [how slides go away](/gmc/slides/#when-the-mode-stops)), and
the base slide showed 5,000.

With `wrap_items: false` in another run, a third right press at `double_scoring` posted nothing and the highlight
stayed put; the left presses then walked back to `extra_points`.

{{< warn >}}
**A child with the wrong name shows nothing.** If no child is named after the highlighted item, GMC hides every child
and logs `Carousel could not find a child named 'double_scoring' to highlight.` (from a test run with the child named
`doublescoring`). Check spelling, and that the node names in the scene match `selectable_items` exactly.
{{< /warn >}}

## Items that depend on the game

An item can have a condition, written after its name in braces. Items whose condition is false are left out when the
mode starts:

```yaml
mode_settings:
  selectable_items:
    - extra_points
    - light_lock{not current_player.lock_lit}
    - double_scoring{current_player.ball > 1}
```

The conditions are checked once, when the mode starts. If every item's condition is false, the mode posts
`carousel_items_empty` and stops itself straight away. The conditional items and the `block_events` and
`release_events` settings are covered by MPF's own tests (`mpf/tests/test_CarouselMode.py`) and weren't run with GMC
for this page; neither was the snippet above.

## The complete machine

The machine config adds flipper and launch-button switches to the one from
[Slides and slide_player](/gmc/slides/#the-complete-machine). The `base` slide is `slides/base.tscn` from
[Showing scores and variables](/gmc/variables/#the-complete-machine), and `award_select.yaml` is above.

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - award_select

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
  s_left_flipper:
    number:
  s_right_flipper:
    number:
  s_launch:
    number:

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

variable_player:
  carousel_item_selected{item=="extra_points"}:
    score: 5000
  carousel_item_selected{item=="light_lock"}:
    lock_lit: 1
  carousel_item_selected{item=="double_scoring"}:
    score_multiplier: 2
```

{{< scenefile "slides/award_select.tscn" >}}
`slides/award_select.tscn`:

```ini
[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_carousel.gd" id="2_carousel"]

[node name="award_select" type="Control"]
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
color = Color(0.15, 0.05, 0.3, 1)

[node name="Title" type="Label" parent="."]
layout_mode = 1
anchors_preset = 10
anchor_right = 1.0
offset_top = 60.0
offset_bottom = 160.0
grow_horizontal = 2
theme_override_font_sizes/font_size = 56
text = "CHOOSE AN AWARD"
horizontal_alignment = 1
vertical_alignment = 1

[node name="Awards" type="Control" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("2_carousel")
carousel_name = "award_select"

[node name="extra_points" type="Label" parent="Awards"]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 96
text = "< 5,000 POINTS >"
horizontal_alignment = 1
vertical_alignment = 1

[node name="light_lock" type="Label" parent="Awards"]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 96
text = "< LIGHT LOCK >"
horizontal_alignment = 1
vertical_alignment = 1

[node name="double_scoring" type="Label" parent="Awards"]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 96
text = "< DOUBLE SCORING >"
horizontal_alignment = 1
vertical_alignment = 1
```
{{< /scenefile >}}
