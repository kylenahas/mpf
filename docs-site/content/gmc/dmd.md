---
title: "A 128×32 DMD"
weight: 9
summary: "Designing slides at DMD resolution, showing them as dots on a screen with GMC's DMD filter, and sending frames to a physical DMD through MPF."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

A traditional pinball DMD is 128 × 32 dots. This page sets up a GMC project for one, in two ways that can be combined:

- **On a screen.** Slides are designed at 128 × 32, Godot scales them up to fill the window, and GMC's DMD filter
  draws them as round dots. This is for machines with an LCD, and for designing slides before the DMD arrives.
- **On a physical DMD.** An `MPFDMDDisplay` sends each new picture to MPF as a 128 × 32 frame, and MPF passes it to the
  DMD hardware.

It builds on [Install GMC and connect it to MPF](/gmc/install-and-connect/) and [Slides](/gmc/slides/).

{{< tip >}}
**Verified.** The project at the end of this page was run with GMC and MPF together (`mpf both -X`). The screenshots
are from those runs, and the frame image is the data MPF's `rgb_dmds` device received, drawn as dots. No DMD hardware
was attached: MPF's virtual platform stood in for the DMD controller.
{{< /tip >}}

## A 128 × 32 canvas

Everything starts from making 128 × 32 the size Godot designs for, and letting it scale that up to a real window. In
`project.godot`:

```ini
[display]

window/size/viewport_width=128
window/size/viewport_height=32
window/size/window_width_override=1024
window/size/window_height_override=256
window/stretch/mode="canvas_items"
window/stretch/aspect="keep"
```

- **`viewport_width` and `viewport_height`** are the design size: slides, labels and positions are all in DMD dots.
  The editor shows a 128 × 32 frame to design in.
- **`window_width_override` and `window_height_override`** are the window's actual size, here 8 times larger. On the
  machine, set these to the screen's size, or use GMC's `fullscreen` setting (see
  [window settings](/gmc/displays/#window-settings)).
- **`stretch/mode="canvas_items"`** draws everything at the window's full resolution, scaled from the 128 × 32
  layout. `aspect="keep"` keeps the 4:1 shape, with bars if the window has another shape.

Use `canvas_items`, not `viewport`, if you want GMC's DMD filter. With `viewport`, Godot draws the whole window at 128
× 32 and then enlarges the result. The filter is part of that window (`MPFWindow` keeps it with the slides), so it
would have only one screen pixel per dot to draw a round dot with. Only `canvas_items` was run for this page.

Slides are ordinary GMC slides, just small: the `PRESS START` label in the attract slide below is `font_size = 14`,
and the ball number is 20. Without a filter, the window shows them as smooth text at 8 times the size:

![PRESS START in smooth orange text, 1024 by 256](/images/gmc/dmd-no-filter.png)

## The DMD look on a screen

GMC's window scene has a filter called `virtual_dmd` that turns the picture into a grid of round dots, each showing the
colour of one 128 × 32 pixel (`resources/virtual_dmd.gdshader`). The project's own `window.tscn` (below) has a copy of
it, and a `[filter]` section in `gmc.cfg` turns it on:

```ini
[filter]
filter="virtual_dmd"
columns=128.0
rows=32.0
```

![PRESS START drawn as orange dots on a dark grid](/images/gmc/dmd-filter-attract.png)

![BALL 1 drawn as orange dots on a dark grid](/images/gmc/dmd-filter-ball.png)

Every other line in `[filter]` is passed to the shader as a parameter (see [screen filters](/gmc/displays/#screen-filters)).
`virtual_dmd` has five:

| Parameter | Default in the shader | What it does |
|---|---|---|
| `columns`, `rows` | `128.0`, `32.0` | The dot grid. Dots are round when the window is `columns`:`rows` in shape. |
| `color` | none | The colour between the dots. `window.tscn` below sets `Color(0.1, 0, 0, 1)`, a very dark red. |
| `spacing` | `2.0` | Dot size: larger values make smaller dots. |
| `hardness` | `5.0` | How sharp the dots' edges are. |

A colour in `gmc.cfg` uses Godot's syntax, for example `color=Color(0.05, 0.02, 0, 1)`. GMC's window also has
`dmd_dots`, which draws the dots without snapping the picture to the grid. Only `virtual_dmd` was run for this page.

## A physical DMD

`MPFDMDDisplay` is a display that also sends its picture to MPF (`classes/mpf_dmd_display.gd`). In the window scene
below, the project's only display is one:

```ini
[node name="dmd" type="Control" parent="."]
layout_mode = 0
offset_right = 128.0
offset_bottom = 32.0
script = ExtResource("2_dmd")
is_default = true
resolution = Vector2i(128, 32)
```

Whenever the picture changes, it copies the window, shrinks it to `resolution` without smoothing, and sends the pixels
to MPF in an `rgb_dmd_frame` message named after the display node. It only sends while MPF is connected. Its other
settings are **Pixel Order** (`RGB`, `RBG` or `GRB`, for panels that expect another channel order) and **Use GPU**
(which logs that GPU shading is still in progress; frames are always made on the CPU).

MPF hands each frame to the `rgb_dmds:` device with the same name, which drives the hardware through its platform:

```yaml
rgb_dmds:
  dmd:
    fps: 30
```

On real hardware, give it the DMD controller's platform, for example `platform: pin2dmd`. The platforms that can drive
an RGB DMD in MPF 0.82.0.dev0 are `pin2dmd`, `smartmatrix`, `zedmd`, `rpi_dmd` and `fast` (each has a
`configure_rgb_dmd`). If no `rgb_dmds:` device has the display's name, MPF stops with `rgb dmd <name> not known`
(`RgbDmd._bcp_receive_dmd_frame`).

In the test run, MPF received 12,288 bytes per frame: 128 × 32 pixels of 3 bytes each, red, green and blue. A frame
came each time the picture changed, one for the attract slide and one when the ball slide replaced it, not 30 a
second. Below is the ball slide's frame as MPF received it, drawn one dot per pixel. The dimmer dots at the letters'
edges come from the font's smoothing; for crisp dots, use a pixel font with antialiasing turned off.

![BALL 1 as 128 by 32 orange dots, drawn from the frame MPF received](/images/gmc/dmd-frame.png)

{{< note >}}
**Classic mono DMDs.** MPF's `dmds:` device, for a single-colour plasma or LED DMD (on a P-ROC, for example), takes a
different message, `dmd_frame`. GMC 1.0.0 only sends `rgb_dmd_frame`, so from its code, GMC can't drive a mono `dmds:`
device directly. This wasn't run. DMD controllers that take RGB frames, such as PIN2DMD and ZeDMD, work with any DMD
they can drive.
{{< /note >}}

### With the filter on

`MPFDMDDisplay` captures the whole window, so with the `virtual_dmd` filter on, the frames are made from the dotted
picture. In the test run, the dark background still came through black (the
shrinking landed on the dots, not on the dark grid between them) and the letters kept their shapes; only some edge
pixels had a different brightness. So the filter can stay on with a panel attached, for example when the same window
is also shown on a screen.


## The complete project

`project.godot`:

```ini
config_version=5

[application]

config/name="my_dmd"
run/main_scene="res://window.tscn"
config/features=PackedStringArray("4.7")

[display]

window/size/viewport_width=128
window/size/viewport_height=32
window/size/window_width_override=1024
window/size/window_height_override=256
window/stretch/mode="canvas_items"
window/stretch/aspect="keep"

[autoload]

MPF="*res://addons/mpf-gmc/mpf_gmc.gd"

[editor_plugins]

enabled=PackedStringArray("res://addons/mpf-gmc/plugin.cfg")
```

`window.tscn`:

```ini
[gd_scene load_steps=5 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_window.gd" id="1_window"]
[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_dmd_display.gd" id="2_dmd"]
[ext_resource type="Shader" path="res://addons/mpf-gmc/resources/virtual_dmd.gdshader" id="3_shader"]

[sub_resource type="ShaderMaterial" id="ShaderMaterial_dmd"]
shader = ExtResource("3_shader")
shader_parameter/color = Color(0.1, 0, 0, 1)
shader_parameter/hardness = 5.0
shader_parameter/spacing = 2.0
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

[node name="dmd" type="Control" parent="."]
layout_mode = 0
offset_right = 128.0
offset_bottom = 32.0
script = ExtResource("2_dmd")
is_default = true
resolution = Vector2i(128, 32)

[node name="filters" type="Control" parent="."]
visible = false
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2

[node name="virtual_dmd" type="ColorRect" parent="filters"]
visible = false
z_index = 4096
material = SubResource("ShaderMaterial_dmd")
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
```

`slides/attract.tscn`:

```ini
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/mpf-gmc/classes/mpf_slide.gd" id="1_slide"]

[node name="attract" type="Control"]
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
color = Color(0, 0, 0, 1)

[node name="Title" type="Label" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_colors/font_color = Color(1, 0.55, 0.1, 1)
theme_override_font_sizes/font_size = 14
text = "PRESS START"
horizontal_alignment = 1
vertical_alignment = 1
```

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
color = Color(0, 0, 0, 1)

[node name="Ball" type="Label" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_colors/font_color = Color(1, 0.55, 0.1, 1)
theme_override_font_sizes/font_size = 20
horizontal_alignment = 1
vertical_alignment = 1
script = ExtResource("2_var")
variable_name = "ball"
template_string = "BALL %s"
```

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

rgb_dmds:
  dmd:
    fps: 30

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
```

Add the `[filter]` section above to `gmc.cfg` for the DMD look on a screen.

`gmc.cfg`:

```ini
[cli]
godot_exec_path="C:/Tools/Godot/Godot_v4.7.2-stable_win64.exe"

[gmc]
exit_on_esc=true
```

The slides follow GMC's rules from [Slides](/gmc/slides/): `attract` is played by MPF's attract mode, and `base` by the
`base` mode's `slide_player`.
