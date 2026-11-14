---
title: "Install GMC and connect it to MPF"
weight: 1
summary: "Set up a Godot project with the GMC add-on in your machine folder, add a first slide, and start MPF and GMC together with mpf both."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

This page takes an MPF machine folder (from [`mpf init`](/get-started/install-and-run/#create-a-project-folder)) and
turns it into a Godot project that shows a slide when MPF starts. At the end, one command starts both programs.

{{< tip >}}
**Verified.** Everything below was run: a machine folder made with `mpf init`, the Godot project files shown on this
page, GMC copied from the `mpf-gmc` repository, and `mpf both -x`. The messages quoted are from those runs.
{{< /tip >}}

## Versions

| Piece | Version used here | Rule |
|---|---|---|
| Godot | 4.7.2 | Godot 4.5 and later need GMC 0.1.6 or later (from the GMC changelog). |
| GMC | 1.0.0 | MPF tells GMC the lowest GMC version it accepts (`__gmc_version__` in `mpf/_version.py`, `1.0.0` here). |
| MPF | 0.82.0.dev0 | GMC refuses MPF older than 0.80.0 (`MPF_MIN_VERSION` in `mpf_gmc.gd`). |

When either side is too old, GMC logs `MPF <version> does not meet GMC's minimum version requirement 0.80.0` or
`GMC <version> does not meet MPF's minimum version requirement <version>` and stops listening (`_on_connect` in
`scripts/bcp_server.gd`). That check was read from the code, not run.

## 1. Get Godot

Download the Godot editor from [godotengine.org](https://godotengine.org). GMC is written in GDScript, so the standard
build is enough; the .NET build isn't needed. Godot is a single program with no installer: put it somewhere
permanent, because `mpf both` will need its path (step 6).

## 2. Make the machine folder a Godot project

The Godot project lives **in the machine folder itself**, next to `config/` and `modes/`. In Godot's project manager,
create a new project and choose your machine folder as its path. Godot writes a `project.godot` file there, which
makes the folder a Godot project.

When you're done with this page, the folder looks like this:

```text
my_machine/
  project.godot          the Godot project
  gmc.cfg                GMC settings (step 6)
  addons/mpf-gmc/        the GMC add-on (step 3)
  slides/attract.tscn    your first slide (step 5)
  config/config.yaml     MPF, as before
  modes/attract/...      MPF, as before
  modes/base/...
```

Keeping them together is what `mpf both` expects: it looks for `project.godot` in the machine folder unless you give it
another folder with `-g`.

## 3. Add the GMC add-on

GMC is the `addons/mpf-gmc` folder of the [mpf-gmc repository](https://github.com/missionpinball/mpf-gmc). Copy that
folder into your project so it ends up at `my_machine/addons/mpf-gmc/` (the same path inside your project as inside the
repository). GMC is also published in Godot's Asset Library, which installs to the same folder; that route wasn't
tried for this page.

Then open the project in the Godot editor. Opening it is also what makes Godot import the add-on's images and fonts;
GMC's startup screen needs them.

## 4. Turn GMC on in the project settings

GMC needs three settings, all under **Project > Project Settings**:

| Setting | Where | Value |
|---|---|---|
| The plugin | **Plugins** tab | Enable **Godot MC**. This adds GMC's node types (`MPFSlide`, `MPFWidget`, `MPFVariable` and others) to the editor. |
| The autoload | **Globals** tab, **Autoload** | Path `res://addons/mpf-gmc/mpf_gmc.gd`, name **`MPF`**, enabled. |
| The main scene | **General** tab, **Application > Run > Main Scene** | `res://addons/mpf-gmc/slides/window.tscn`, GMC's window. |

{{< warn >}}
**The autoload must be named exactly `MPF`.** Every GMC script refers to it by that name. In a test run with the
autoload named `Mpf`, the project didn't start at all: Godot stopped with `Parse Error: Identifier "MPF" not declared in
the current scope`.
{{< /warn >}}

The window scene opens GMC's connection: when it starts, GMC listens on port 5050 and shows a "Waiting for MPF..."
screen until MPF connects.

The parts of `project.godot` these settings produce (Godot adds more lines of its own; these are the ones that matter
to GMC):

`project.godot`:

```ini
config_version=5

[application]

config/name="my_machine"
run/main_scene="res://addons/mpf-gmc/slides/window.tscn"
config/features=PackedStringArray("4.7")

[autoload]

MPF="*res://addons/mpf-gmc/mpf_gmc.gd"

[editor_plugins]

enabled=PackedStringArray("res://addons/mpf-gmc/plugin.cfg")
```

The window takes its size from **Display > Window > Size** (`MPFWindow._ready` sets its minimum size to the viewport
width and height). Godot's default is 1152 × 648, which is what the screenshots on this page show.

## 5. Add an attract slide

The attract mode that `mpf init` writes already asks for a slide:

```yaml
slide_player:
  mode_attract_started: attract
```

GMC has no slide called `attract` of its own, so it has to come from your project. Without one, the test run logged
`Assertion failed: Unknown slide name 'attract'` in Godot as soon as MPF connected, and the screen went blank grey.

A slide is a Godot scene whose root node is an `MPFSlide`. GMC finds slides by file name in the project's `slides/`
folder (and in `modes/<mode>/slides/`), so `slides/attract.tscn` is the slide named `attract`. In the editor:

1. **Scene > New Scene**, then choose **Other Node** and pick `MPFSlide` as the root.
2. Add what the slide shows. This one has a `ColorRect` for the background and a `Label` reading "PRESS START".
3. Save it as `slides/attract.tscn`.

The scene file from the test run, for reference (you'd normally build this in the editor rather than type it):

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
color = Color(0.05, 0.1, 0.3, 1)

[node name="Title" type="Label" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
theme_override_font_sizes/font_size = 96
text = "PRESS START"
horizontal_alignment = 1
vertical_alignment = 1
```

(`MPFSlide` is a `Control` with the `mpf_slide.gd` script, which is why the root node's type in the file is `Control`.)

## 6. Add gmc.cfg

`gmc.cfg` in the project root holds GMC's settings. Without it GMC still runs, but logs `Unable to find gmc.cfg in the
project root.` at startup. `mpf both` reads the same file for its own settings in the `[cli]` section.

`gmc.cfg`:

```ini
[cli]
godot_exec_path="C:/Tools/Godot/Godot_v4.7.2-stable_win64.exe"

[gmc]
exit_on_esc=true
```

| Setting | What it does |
|---|---|
| `[cli] godot_exec_path` | The Godot program `mpf both` starts. Without it, `mpf both` runs `godot` from your `PATH`. Put your own path here; on macOS and Linux, use the path to the Godot binary. |
| `[gmc] exit_on_esc` | Close GMC with the Escape key (`MPFGMC._input`). Handy while developing. |

GMC's own editor panels (the **GMC** and **MPF** docks) write settings such as fullscreen and log levels into this file
too. Settings that only apply to one computer can go in a `gmc.local.cfg` in Godot's user data folder; GMC reads it
after `gmc.cfg` and its values win (`MPFGMC.get_config_value`).

## 7. Start both

From the machine folder:

```bash
mpf both -x
```

`mpf both` (`mpf/commands/both.py`) starts Godot on the project first, then starts MPF; any options it doesn't know
(here `-x`, the virtual platform) go to MPF. In the test run:

1. The GMC window opened on its startup screen, "Waiting for MPF...".
2. MPF tried to connect to `localhost:5050`, kept trying while Godot was starting, and connected about 2.5 seconds later
   (`Connected BCP to 'local_display' localhost:5050` in the MPF log). MPF retries every 0.1 seconds with no time
   limit (`BCPClientSocket._setup_client_socket`), so it doesn't matter which program starts first.
3. Attract mode started, `slide_player` sent the `attract` slide, and GMC showed it (MPF logged
   `slide_attract_active`).

![The attract slide from this page, as GMC showed it once MPF had connected](/images/gmc/attract-slide.png)

Closing the GMC window (or pressing Escape, with `exit_on_esc`) shut MPF down too, with `Shutdown reason: BCP client
local_display disconnected and exit_on_close is set`. MPF's built-in BCP connection to GMC is marked `required` and
`exit_on_close` (`bcp: connections: local_display` in `mpfconfig.yaml`), so MPF won't run on without its display.

| `mpf both` option | What it does |
|---|---|
| `-g <folder>` | The Godot project folder, if it isn't the machine folder. Also `[cli] gmc_project_path` in `gmc.cfg`. |
| `-G <path>` | The Godot program. Also `[cli] godot_exec_path`; default `godot`. |
| anything else | Passed to MPF, as with `mpf game` (`-x`, `-X`, `-v` and so on). |

### Starting them separately

You can also start the two yourself: run the project from the Godot editor (it opens on "Waiting for MPF..."), then
run `mpf -x` in the machine folder. That's the same as what `mpf both` does, and it's handy when you're editing slides
and want to restart only one side. The test run started GMC first and MPF three seconds later, and they connected as
above.

To run MPF with no media controller at all, use `mpf -b`: it skips the BCP connection.

## When it doesn't connect

MPF's messages appear in the terminal you started it from. Godot's messages appear in the editor's **Output** panel
when you run the project from the editor. When `mpf both` starts Godot on Windows, Godot's messages didn't appear in the
terminal in the test runs; they were in Godot's log file, `logs/godot.log` in the project's user data folder
(`%APPDATA%\Godot\app_userdata\<project name>\` on Windows). The editor's **Project > Open User Data Folder** opens
that folder.

| What you see | Why |
|---|---|
| `Unable to find Godot executable at 'godot'` from `mpf both` | No `[cli] godot_exec_path` and no `godot` on your `PATH`. Set one of them, or pass `-G`. |
| `Unable to find GMC project.godot file in '...'` from `mpf both` | The Godot project isn't in the machine folder. Move it, or pass `-g`. |
| `Identifier "MPF" not declared in the current scope` in Godot | The autoload is missing or not named `MPF` (step 4). |
| `Unknown slide name 'attract'` in Godot | No `slides/attract.tscn` (step 5). The same message names any slide a `slide_player` asks for that GMC can't find. |
| `Slide scenes must use (or extend) the MPFSlide script on the root node` | The scene's root node isn't an `MPFSlide`. In the test run this also followed a missing slide. |
| MPF waits on `Connecting BCP to 'local_display' at localhost:5050...` and goes no further | GMC isn't running, or its window scene isn't the main scene, so nothing is listening. MPF keeps retrying until something does. |

The two `mpf both` messages are from `mpf/commands/both.py`; they weren't triggered for this page.
