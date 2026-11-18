---
title: "Showing scores and variables"
weight: 4
summary: "Put the score, player and machine variables, and event values on a slide with MPFVariable, and change them with tokens and action: update."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

Text that changes during a game, such as the score, the ball number or a jackpot value, goes on a slide as an
**`MPFVariable`** node: a Godot `Label` that GMC fills in from MPF's data and keeps up to date. This page puts several on
a slide and shows what they displayed during a game.

{{< tip >}}
**Verified.** The machine at the end of this page was run with GMC and MPF together on the smart virtual platform,
with the switch hits scripted. The screenshots are from that run.
{{< /tip >}}

It builds on [Slides and slide_player](/gmc/slides/): the same machine, without the skill shot, with scoring added.

## Adding a variable to a slide

In a slide scene, add a child node and pick **MPFVariable** (it's listed under `Label`, because that's what it extends).

![The Create New Node dialog with MPFVariable found under Label](/images/gmc/editor/variables-create-mpfvariable.png)

Style it like any label (font, size, alignment), then set what it shows in the Inspector, in the **MPFVariable**
section at the top:

![The Inspector for the Score label: Variable Type Current Player, Variable Name score, Comma Separate on](/images/gmc/editor/variables-score-inspector.png)

| Property | Default | What it does |
|---|---|---|
| **Variable Type** | Current Player | Where the value comes from (see the next table). |
| **Variable Name** | empty | The variable (or event argument) to show. |
| **Comma Separate** | off | Write numbers of 1000 and up with thousands separators: `1,250`. |
| **Min Digits** | `-1` | Pad numbers with zeros to this many digits. Ignored when a **Template String** is set, or when **Comma Separate** applies (read from `MPFVariable.update_text`, not run). |
| **Template String** | empty | Text with `%s` where the value goes: `RAMPS: %s`. |
| **Format String** | empty | Text with `{name}` placeholders, filled from all the variables of that type at once: `Ball {ball}, {score} points`. |
| **Initialize Empty** | on | Show no text until a value arrives, instead of the label's placeholder text from the editor. |
| **Update Event** | empty | For Event Arg labels: an MPF event whose arguments also refresh this label (read from the code, not run). |
| **Min Players**, **Max Players** | `0` | Hide the label unless the number of players is in this range. |

| Variable Type | Value from |
|---|---|
| **Current Player** | The player whose turn it is: `score`, `ball`, `number` and any player variable your config sets. |
| **Machine Var** | A machine variable, such as `credits_string`. |
| **Event Arg** | The event that played the slide, plus the `tokens` in its `slide_player` entry (see [below](#values-from-events-and-tokens)). |
| **Player 1** to **Player 4** | A specific player, whoever's turn it is. |
| **Setting** | A machine setting. |
| **Active Slide** | Listed in GMC's types, for the name of the active slide. |

**Current Player**, **Machine Var** and **Event Arg** were run for this page; the others weren't.

Player variables only exist during a game, so labels of the player types belong on slides that game modes play. GMC
logs `MPFVariable '<name>' is a player variable and should only exist in game modes.` when one appears outside a game
(`MPFVariable._calculate_player_value`).

## The base slide

The base slide in the example has five labels, stacked by a `VBoxContainer`:

1. Make the slide as in [Slides](/gmc/slides/#making-a-slide): an `MPFSlide` root named `base` and a full-rect
   `ColorRect` background.
2. Add a `VBoxContainer` child named `Lines`, anchored **Full Rect**, with **Alignment** set to **Center**. A
   container lays out its children, here one under the other, so the labels need no positions of their own.
3. Add five **MPFVariable** children to `Lines` and set each one as in the table below.

![The base slide in the editor: Lines holds the five MPFVariable labels, with Score selected](/images/gmc/editor/variables-base-score.png)

The labels have no text of their own, so the slide looks empty in the editor. To see the layout while you work, give
them some sample **Text**: **Initialize Empty** (on by default) hides it in the game until the real value arrives.

The `Credits` label shows a machine variable instead of a player variable:

![The Inspector for the Credits label: Variable Type Machine Var, Variable Name credits_string](/images/gmc/editor/variables-credits-inspector.png)

| Label | Variable Type | Variable Name | Formatting |
|---|---|---|---|
| Player | Current Player | `number` | Template `PLAYER %s` |
| Score | Current Player | `score` | Comma Separate |
| Ramps | Current Player | `ramps` | Template `RAMPS: %s` |
| Summary | Current Player | `score` | Format `Ball {ball}, {score} points` |
| Credits | Machine Var | `credits_string` | none |

At the start of the ball:

![The base slide at the start of a ball: PLAYER 1, 0, RAMPS: 0, Ball 1, 0 points, FREE PLAY](/images/gmc/variables-start.png)

After a ramp (1000 points, one more ramp) and a target (250 points):

![The base slide after a ramp and a target: 1,250 and RAMPS: 1](/images/gmc/variables-after-ramp.png)

The labels changed as MPF sent each new value, with no slide_player entry: a label subscribes to its variable when the
slide appears (`MPFVariable._ready`). The summary line shows `1250`, not `1,250`: **Comma Separate** doesn't apply to
format strings.

{{< warn >}}
**A format string only refreshes when its Variable Name changes.** The format string can name several variables, but
the label listens for just the one in **Variable Name** (`MPFVariable._on_player_update`). In a test run with Variable
Name left empty, the summary stayed at `Ball 1, 0 points` all game. With `score` as the Variable Name it changed with
every score, and picked up the ball number at the same time.
{{< /warn >}}

## A player variable's first value

`ramps` is declared in the machine config with a starting value:

```yaml
player_vars:
  ramps:
    initial_value: 0
```

{{< warn >}}
**GMC doesn't show the first value of a player variable it hasn't seen before.** In a test run without this
`player_vars` entry, the Ramps label stayed blank after the first ramp, though MPF had sent `ramps` = 1. It showed
`RAMPS: 2` after the second. GMC stores a variable's first value without telling the labels on screen; only later
changes reach them (`GMCGame.update_player`). A slide that appears afterwards does read the stored value.

Giving the variable an `initial_value` in `player_vars` avoids it: MPF sends that value when the player is added,
before any slide shows it, so the first real change is reported. With the entry above, the label read `RAMPS: 0` from
the start and `RAMPS: 1` after the first ramp. `score` doesn't need this; GMC starts every player with `score` 0.
{{< /warn >}}

## Values from events and tokens

A label with **Variable Type** Event Arg shows a value that comes with the slide rather than from a player. The
`ramp_lit` slide has one, with Variable Name `award`. Its value can come from three places, and the first one that has
`award` wins (`MPFVariable.update`):

1. An argument of the event that played the slide.
2. `tokens` in the `slide_player` entry.
3. Another setting of the same name in the `slide_player` entry.

In the example the ramp posts an event, `ramp_award`, with an `award` argument, and `slide_player` plays `ramp_lit` on
that event with a token of the same name:

```yaml
event_player:
  s_ramp_active:
    ramp_award:
      award: FROM EVENT

slide_player:
  ramp_award:
    ramp_lit:
      priority: 10
      expire: 2s
      tokens:
        award: FROM TOKEN
```

The slide showed `FROM EVENT`. Without the event argument it would show the token. Tokens are how one slide shows
different text for different shots; event arguments carry values that only exist when the event happens, such as
`value` in MPF's `player_score` event.

### Changing values on a slide that's showing

`action: update` sends new values to a slide that's already in the stack, without playing it again:

```yaml
slide_player:
  s_target_active:
    ramp_lit:
      action: update
      tokens:
        award: TARGET 250
```

In the test run a target hit while `ramp_lit` was showing changed its text in place:

![The ramp_lit slide after action: update, now reading TARGET 250](/images/gmc/variables-update.png)

The slide's `expire` kept counting from when it was played; `update` doesn't restart it. If the slide isn't in the
stack, `update` does nothing (`MPFSceneBase.process_action`).

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base

machine:
  balls_installed: 1

player_vars:
  ramps:
    initial_value: 0

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

variable_player:
  s_ramp_active:
    score: 1000
    ramps: 1
  s_target_active:
    score: 250

event_player:
  s_ramp_active:
    ramp_award:
      award: FROM EVENT

slide_player:
  mode_base_started: base
  ramp_award:
    ramp_lit:
      priority: 10
      expire: 2s
      tokens:
        award: FROM TOKEN
  s_target_active:
    ramp_lit:
      action: update
      tokens:
        award: TARGET 250
```

The two slides. In the scene files an `MPFVariable` is a `Label` with the `mpf_variable.gd` script; its Inspector
settings are the lines after `script =`. `variable_type = 1` is Event Arg and `2` is Machine Var; Current Player is the
default, so it isn't written.

{{< scenefile "slides/base.tscn" >}}
`slides/base.tscn`:

```ini
[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_variable.gd" id="2_var"]

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

[node name="Ramps" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 48
horizontal_alignment = 1
script = ExtResource("2_var")
variable_name = "ramps"
template_string = "RAMPS: %s"

[node name="Summary" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 36
horizontal_alignment = 1
script = ExtResource("2_var")
variable_name = "score"
format_string = "Ball {ball}, {score} points"

[node name="Credits" type="Label" parent="Lines"]
layout_mode = 2
theme_override_font_sizes/font_size = 36
horizontal_alignment = 1
script = ExtResource("2_var")
variable_type = 2
variable_name = "credits_string"
```
{{< /scenefile >}}

{{< scenefile "slides/ramp_lit.tscn" >}}
`slides/ramp_lit.tscn`:

```ini
[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_variable.gd" id="2_var"]

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

[node name="Award" type="Label" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 96
horizontal_alignment = 1
vertical_alignment = 1
script = ExtResource("2_var")
variable_type = 1
variable_name = "award"
```
{{< /scenefile >}}
