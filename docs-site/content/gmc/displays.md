---
title: "Displays, filters and running GMC on the machine"
weight: 9
summary: "Your own window scene with more than one display, slides aimed at each with target, screen filters, window settings, GMC starting MPF itself, and exporting."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together); exporting not run"
---

So far every slide has gone to GMC's built-in window, which has one display. A machine often has more: an LCD in the
backbox and a small screen in the apron, or a main screen and a strip below it. This page makes a window with two
displays, aims slides at each, adds a screen filter, and covers how GMC runs on the finished machine.

{{< tip >}}
**Verified.** The window, displays, filter and `spawn_mpf` below were run with GMC and MPF together, and the
screenshots are from those runs. Exporting wasn't run: it needs Godot's export templates, which weren't installed on
the test machine.
{{< /tip >}}

It builds on [Slides and slide_player](/gmc/slides/): the same machine and `base` slide.

## Your own window scene

GMC starts from the scene set as the project's main scene. The [install page](/gmc/install-and-connect/#4-turn-gmc-on-in-the-project-settings)
used GMC's own `addons/mpf-gmc/slides/window.tscn`, which has one display. For anything else, make your own: a scene
whose root node is an **`MPFWindow`**, with an **`MPFDisplay`** child for each display. Set it as the main scene in
**Project Settings > Application > Run > Main Scene**. Don't edit GMC's own copy: an update of the add-on replaces it.

The window covers the whole Godot window. Set the window size (**Display > Window > Size**) to the area that holds all
your displays, and give each display its position and size within it. The example is 1152 × 864: a 1152 × 648 main
display, and a 1152 × 216 strip below it called `info`:

`project.godot`:

```ini
config_version=5

[application]

config/name="my_machine"
run/main_scene="res://window.tscn"
config/features=PackedStringArray("4.7")

[display]

window/size/viewport_width=1152
window/size/viewport_height=864

[autoload]

MPF="*res://addons/mpf-gmc/mpf_gmc.gd"

[editor_plugins]

enabled=PackedStringArray("res://addons/mpf-gmc/plugin.cfg")
```

`MPFDisplay` has these settings in the Inspector:

| Property | What it does |
|---|---|
| node name | The display's name, used by `target:`. |
| **Is Default** | Slides and widgets without a `target` go here. Only one display can be the default; with none, the first display is. |
| **Initial Slide** | A scene shown on this display from startup until the first slide arrives. The example gives the main display GMC's startup scene, which shows "Waiting for MPF...". |
| **Allow Empty** | Let the display go blank when its last slide is removed (see [slides](/gmc/slides/#when-nothing-is-left)). |

To build the example's `window.tscn`:

1. **Scene > New Scene**, choose **Other Node** and pick **MPFWindow**. Anchor it **Full Rect**. Searching for `MPF`
   in this dialog lists every node type GMC adds:

   ![The Create New Node dialog searched for MPF, listing MPFDisplay, MPFDMDDisplay, MPFSlide, MPFWidget, MPFEventHandler, MPFVariable, MPFWindow and others](/images/gmc/editor/displays-create-mpf.png)

2. Add an **MPFDisplay** child named `main`. Under **Layout > Transform**, give it **Size** 1152 × 648 at **Position**
   0, 0. Tick **Is Default**, and set **Initial Slide** to GMC's `addons/mpf-gmc/slides/startup.tscn` (drag it from the
   FileSystem panel onto the property, or use the property's **Load** option).

   ![The Inspector for main: Is Default on, Initial Slide set to the startup scene](/images/gmc/editor/displays-main-inspector.png)

3. Add a second **MPFDisplay** named `info`, with **Size** 1152 × 216 at **Position** 0, 648, just below `main`.

   ![The Inspector for info filtered to "position", showing Position 0, 648](/images/gmc/editor/displays-info-position.png)

4. Save the scene as `window.tscn` and make it the project's main scene.

In the editor each display is drawn as a coloured box with its name, so the layout is easy to check:

![The window scene in the editor: main as a red box above info as a blue box, with info selected](/images/gmc/editor/displays-window-info.png)

Each display keeps its own [slide stack](/gmc/slides/#the-slide-stack), so slides on one never cover slides on
another.

## Aiming slides at a display

`target:` on a `slide_player` (or `widget_player`) entry names the display:

```yaml
slide_player:
  mode_base_started:
    base: {}
    info_bar:
      target: info
```

In attract mode the `attract` slide went to the main display (the default) and the `info` display stayed empty. When
the game started, `base` went to the main display and `info_bar` (a label showing the ball number) to the strip:

![Two displays: BALL IN PLAY on the main display, INFO DISPLAY: BALL 1 on the strip below](/images/gmc/two-displays.png)

A `target` that isn't one of the window's displays stops GMC with an assertion, `Unknown display name '<name>'`
(`MPFWindow.get_display`, read from the code).

## Screen filters

A filter is a shader drawn over the whole window, for looks such as a dot-matrix effect. GMC's window scene has a
`filters` node holding three, named `virtual_dmd`, `pixelate` and `dmd_dots`, plus `custom` for your own. A `[filter]`
section in `gmc.cfg` turns one on, and its other lines set the shader's parameters (`MPFWindow._check_config`):

```ini
[filter]
filter="pixelate"
columns=96.0
rows=72.0
```

The example's window scene copies the `pixelate` filter from GMC's window. To do the same, open GMC's
`addons/mpf-gmc/slides/window.tscn`, right-click its `filters` node and choose **Copy**, then in your window scene
right-click the root and choose **Paste**, and delete the filters you don't use. With the section above, the picture was
drawn as a 96 × 72 grid of blocks:

![The same two displays drawn through the pixelate filter](/images/gmc/filter-pixelate.png)

If `gmc.cfg` has a `[filter]` section, the window scene must have a `filters` child, or GMC stops with an assertion.
`filter` can also be a `res://` path to your own shader, which GMC puts on the `custom` node. Only `pixelate` was run.

## Window settings

| Setting in `gmc.cfg` | What it does |
|---|---|
| `[gmc] fullscreen=true` | Open the window in exclusive full screen (`MPFWindow._enter_tree`). |
| `[window] size=Vector2i(1920, 1080)` | Set the window's size in pixels when GMC starts (`MPFGMC._enter_tree`). |
| `[window] scale=0.5` | Scale the window's contents, for example to see a large layout on a small monitor. |
| `[gmc] exit_on_esc=true` | Close GMC with the Escape key. |

These were read from the code; only `exit_on_esc` appears in the runs on these pages.

## GMC starting MPF

On the machine, it's simpler for one program to start the other. `mpf both` starts GMC from MPF
([install page](/gmc/install-and-connect/#7-start-both)); `spawn_mpf` works the other way, with GMC starting MPF. That's
how an exported GMC build, which has no terminal, gets MPF running. The settings go in an `[mpf]` section of `gmc.cfg`,
and the **MPF** dock in the editor writes them too:

```ini
[mpf]
spawn_mpf=true
executable_path="C:/path/to/venv/Scripts/mpf.exe"
mpf_args="-X"
```

| Setting | What it does (`GMCProcess._spawn_mpf`) |
|---|---|
| `spawn_mpf` | Start MPF when GMC starts. Also turned on by a `spawn_mpf` export feature, or `--spawn_mpf` on Godot's command line. |
| `executable_path` | Required. The program to run: the `mpf` command in your venv, or a Python interpreter (with `executable_args`). |
| `executable_args` | Arguments placed before the machine folder, for example `-m mpf` when `executable_path` is Python. |
| `machine_path` | The MPF machine folder. Default: the Godot project folder when run from the editor, the folder holding the program when exported. |
| `mpf_args` | Arguments placed after the machine folder. |
| `virtual` | `true` adds `-x`. |
| `verbose` | `true` adds `-vV`. |

GMC always adds `-t` (no text UI, since there's no terminal) and a log file in its own user data folder, so in the test
run it ran:

```text
mpf.exe <machine folder>/ -t -X -l <Godot user data>/logs/mpf_2026-11-15_07.13.37.log
```

MPF connected 1.7 seconds after GMC started it, and the game ran as with `mpf both`, attract slide and all. When the GMC
window closed, MPF shut down too.

{{< note >}}
**On Windows, GMC's check that MPF started doesn't work.** A few seconds after starting MPF, GMC checks the process with
`find`, which on Windows is a text-search tool, so the test run logged `Unknown process status 'FIND: Parameter format
not correct'`. MPF was running fine. The cost is that GMC's automatic retry, up to three more attempts if MPF quits at
startup, can't happen on Windows (`GMCProcess._check_mpf`).
{{< /note >}}

## Exporting

Exporting turns the project into a program that runs without the Godot editor, which is what goes in the machine. It
uses Godot's normal export (**Project > Export**), which needs Godot's export templates for your version, installed
from the editor. **This wasn't run for this page**; what GMC adds, from its code:

- GMC's export plugin (`editor/mpf_gmc_export.gd`) lists every slide, widget and sound before the export and stores the
  list in the exported program (`_media.res`). The exported program reads that list at startup instead of searching
  folders, which it can't do once the files are packed (`GMCMedia._enter_tree`).
- For the exported program to start MPF, use `spawn_mpf` above. Without a `machine_path`, it looks for the machine
  folder where the exported program is.
- `gmc.cfg` is part of the project, so it's exported with it. Settings for one computer can go in `gmc.local.cfg` in the
  user data folder, which overrides it (see the [install page](/gmc/install-and-connect/#6-add-gmccfg)).

## DMD displays

`MPFDMDDisplay` is a display that also sends what it shows to MPF, a frame at a time, for MPF to drive a physical RGB
DMD. [A 128×32 DMD](/gmc/dmd/) sets one up, along with designing slides at DMD resolution and the DMD look on a
screen.

## The complete window

The machine, slides and modes are from [Slides and slide_player](/gmc/slides/#the-complete-machine), with the
`base.yaml` `slide_player` entry above. The new files:

{{< scenefile "window.tscn" >}}
`window.tscn`:

```ini
[gd_scene load_steps=6 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_window.gd" id="1_window"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_display.gd" id="2_display"]
[ext_resource type="PackedScene" path="res://addons/mpf-gmc/slides/startup.tscn" id="3_startup"]
[ext_resource type="Shader" path="res://addons/mpf-gmc/resources/pixelate.gdshader" id="4_pixelate"]

[sub_resource type="ShaderMaterial" id="ShaderMaterial_pixelate"]
shader = ExtResource("4_pixelate")
shader_parameter/columns = 128.0
shader_parameter/rows = 32.0

[node name="MPFWindow" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1_window")

[node name="main" type="Control" parent="."]
layout_mode = 0
offset_right = 1152.0
offset_bottom = 648.0
script = ExtResource("2_display")
is_default = true
initial_slide = ExtResource("3_startup")

[node name="info" type="Control" parent="."]
layout_mode = 0
offset_top = 648.0
offset_right = 1152.0
offset_bottom = 864.0
script = ExtResource("2_display")

[node name="filters" type="Control" parent="."]
visible = false
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2

[node name="pixelate" type="ColorRect" parent="filters"]
visible = false
z_index = 4096
material = SubResource("ShaderMaterial_pixelate")
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
```
{{< /scenefile >}}

{{< scenefile "slides/info_bar.tscn" >}}
`slides/info_bar.tscn`:

```ini
[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_variable.gd" id="2_var"]

[node name="info_bar" type="Control"]
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
color = Color(0.1, 0.1, 0.1, 1)

[node name="Ball" type="Label" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_colors/font_color = Color(1, 0.8, 0.2, 1)
theme_override_font_sizes/font_size = 72
horizontal_alignment = 1
vertical_alignment = 1
script = ExtResource("2_var")
variable_name = "ball"
template_string = "INFO DISPLAY: BALL %s"
```
{{< /scenefile >}}

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

slide_player:
  mode_base_started:
    base: {}
    info_bar:
      target: info
```
