---
title: "Working in Godot"
weight: 1
summary: "A first look at Godot for GMC: the handful of ideas everything is built from, a tour of the editor and GMC's docks, how to lay out and style a slide, media, scripts, animation, resolution, how a GMC project is organised, and where to learn more."
---

New to Godot? Start here, before installing GMC. This page explains the few Godot ideas you need for GMC,
walks through the editor, and points to the parts of Godot's own documentation worth reading. You don't need to learn
all of Godot: 3D, physics, tilemaps, game input and most of the game-making parts never come up in GMC work.

Every link on this page goes to the "stable" version of the Godot documentation, which matches the Godot 4 releases GMC
works with (see [Versions](/gmc/install-and-connect/#versions)).

## The ideas you need

Godot is built from a few ideas, and almost everything in GMC is one of them:

| Idea | What it is | In GMC |
|---|---|---|
| **Node** | One building block with one job: a coloured rectangle (`ColorRect`), a piece of text (`Label`), an image (`TextureRect`), a sound player. Each node has a type and a set of **properties** (its size, colour, text and so on). | Everything on screen. GMC adds its own node types, all named `MPF...`. |
| **Scene** | A tree of nodes saved together as one `.tscn` file. One node is the **root**; the rest are its children, their children, and so on. A child is drawn on top of its parent and moves with it. | Every slide, widget and window is a scene. |
| **Resource** | A piece of data a node uses, rather than something on screen: a font, a theme, an image, a sound. A resource can live in its own file or inside a scene. | Fonts, themes, images and sounds. |
| **Script** | Code (in Godot's language, GDScript) attached to one node, adding behaviour to it. | Rarely needed; GMC's node types already have their own. |
| **Signal** | A message a node sends when something happens (a button pressed, a timer finished), which other nodes can listen for. | Godot's signals are separate from MPF's events; see [Events between MPF and Godot](/gmc/events/). |

So making a slide means: create a scene whose root is GMC's `MPFSlide` node, add child nodes for the background and
text, set their properties, and save it in the `slides/` folder.

Learn more: [Overview of Godot's key concepts](https://docs.godotengine.org/en/stable/getting_started/introduction/key_concepts_overview.html)
(a short read, and the best place to start).

## A tour of the editor

When you open a project, the Godot editor looks like this (here with the first slide you'll make in [the install guide](/gmc/install-and-connect/#5-add-an-attract-slide)):

![The Godot editor with a slide open: the Scene panel top left, the FileSystem panel below it, the 2D view in the middle, and the Inspector on the right](/images/gmc/editor/install-attract-title.png)

| Part | Where | What you use it for |
|---|---|---|
| **Scene** panel | Top left | The open scene's tree of nodes. Click a node to select it. Add a child node with **+**, rename one by double-clicking, reorder by dragging, and right-click for everything else. |
| **FileSystem** panel | Bottom left | The project's files. Double-click a scene to open it; drag an image or font from here onto a property in the Inspector to use it. |
| **2D** view | Middle | The open scene as it will look. Click and drag nodes to move them, drag the handles to resize. Scroll to zoom; hold the middle mouse button to pan. |
| **Inspector** | Right | The properties of whatever is selected. Properties are grouped by node type, the node's own type first: a `Label` shows its **Label** properties, then the **Control** ones every user-interface node shares. A changed property gets a circular-arrow button that puts it back to the default. |
| Scene tabs | Above the 2D view | One tab per open scene (here **window** and **attract**). |
| Main screens | Top centre | **2D** for building slides, **Script** for code. You won't need **3D**, **Game** or **Asset Store** for GMC. |
| Bottom panel | Bottom | **Output** for messages and errors, and panels such as **Animation** and **Audio** that open when you need them. |

The keys worth learning first:

| Key | Does |
|---|---|
| Ctrl+A | Add a child node to the selected node (the **+** button). |
| Ctrl+Shift+A | Add another scene as a child (the chain-link button). |
| F2 / Ctrl+D / Delete | Rename, duplicate, or delete the selected node. |
| Ctrl+S | Save the open scene. Changes aren't saved until you do; an unsaved scene's tab shows `(*)`. |
| Ctrl+Z | Undo. |
| F5 / F8 | Run the project / stop it. |

Learn more: [First look at the editor](https://docs.godotengine.org/en/stable/getting_started/introduction/first_look_at_the_editor.html),
[Editor manual](https://docs.godotengine.org/en/stable/tutorials/editor/index.html).

### GMC's docks

With GMC's plugin enabled ([the install guide](/gmc/install-and-connect/#4-turn-gmc-on-in-the-project-settings)), the editor gets two more tabs
next to the Scene panel, and a bottom panel:

- **GMC** dock: GMC's own settings, saved to the `[gmc]` section of `gmc.cfg` as you change them: full screen, the
  logging level, and closing with Escape.

  ![The GMC dock: Fullscreen Mode, Global Logging Level, Show All Loggers, and Exit Game on ESC](/images/gmc/editor/godot-gmc-dock.png)

- **MPF** dock: settings for GMC starting MPF itself, saved to the `[mpf]` section of `gmc.cfg` with **Save Changes**.
  See [GMC starting MPF](/gmc/displays/#gmc-starting-mpf).

  ![The MPF dock: Launch MPF with GMC, Virtual Mode, Verbose Logging, and the executable, machine path and argument fields](/images/gmc/editor/godot-mpf-dock.png)

- **MPF Output** at the bottom: MPF's console output, when GMC starts MPF.

### Running

**Run Project** (F5, or the play button at the top right) opens GMC's window, which waits for MPF to connect. Start
MPF with `mpf both`, or on its own (see [Start both](/gmc/install-and-connect/#7-start-both)). Errors from your slides
show in the **Output** and **Debugger** panels.

Use F5, not **Run Current Scene** (F6): F6 starts only the scene you have open, without GMC's window or MPF, so slides
don't get their values or their place on a display.

While the project runs, the Scene panel gets a **Remote** tab showing the running game's node tree: which slides are on
which display, and their properties as they are right now. When a slide doesn't appear as you expect, look there first.

Learn more: [Overview of debugging tools](https://docs.godotengine.org/en/stable/tutorials/scripting/debug/overview_of_debugging_tools.html)
(the remote scene tree).

## Building a scene

Each GMC page walks through building its scenes step by step, with screenshots; [Slides and slide
players](/gmc/slides/) is the first. The steps are always the same few:

1. **Make the scene.** **Scene > New Scene**, then choose the root node's type. The root's type decides what the scene
   is to GMC: an `MPFSlide` root makes a slide, `MPFWidget` a widget, `MPFWindow` a window. GMC's types are in the
   **Create New Node** dialog with Godot's own; type the name in its search box.
2. **Add child nodes.** Select a node and press Ctrl+A to add a child under it. Nodes lower in the Scene panel are drawn
   on top, so add the background first.
3. **Set properties** in the Inspector: the text, a colour, a font. For an image or font, drag the file from the
   FileSystem panel onto the property.
4. **Save** with Ctrl+S, into the right folder (`slides/`, `widgets/`), with a snake_case file name. The file name is
   the name MPF's config uses (see [Project conventions](#project-conventions)).

**Reuse with child scenes.** A scene can include another scene as one of its nodes (Ctrl+Shift+A). Use this for
anything that appears on several slides, such as a score panel: change the panel's own scene and every slide that
includes it changes too.

**Node names** are mostly just labels (Godot's convention is PascalCase: `Background`, `Title`), but GMC reads them in
a few places, and there they're case-sensitive: a carousel's item nodes are named after the items
([carousels](/gmc/carousel/#the-slide)), and a display's name is what `target:` uses
([displays](/gmc/displays/#aiming-slides-at-a-display)).

Learn more: [Nodes and scenes](https://docs.godotengine.org/en/stable/getting_started/step_by_step/nodes_and_scenes.html),
[Creating instances](https://docs.godotengine.org/en/stable/getting_started/step_by_step/instancing.html).

## Laying out a slide

Slides are made of Godot's user-interface nodes, called **Control** nodes: `ColorRect`, `Label`, `TextureRect` and the
containers below. (Godot's tutorials often use `Node2D`, `Sprite2D` and similar nodes, which are for game worlds; slides
don't need them.)

You can drag Control nodes into place, but a slide laid out that way only fits one screen size. Two Godot features lay
things out for you:

- **Anchors** tie a node's edges to its parent's. With a node selected, the **Anchor preset** menu in the 2D view's
  toolbar sets the common ones: **Full Rect** fills the parent (use it for every slide's root and for backgrounds),
  **Center** keeps the node in the middle, **Bottom Wide** makes a strip along the bottom, and so on. A slide built with
  anchors fits any display.
- **Containers** are nodes that place their children for you: a `VBoxContainer` stacks them top to bottom, an
  `HBoxContainer` side by side, a `MarginContainer` adds space around them, a `GridContainer` makes a grid. The
  [variables page](/gmc/variables/#the-base-slide) stacks its labels in a `VBoxContainer`. Inside a container, the
  container sets each child's position and size, and the Inspector shows sizing options for the child instead.

Learn more: [Size and anchors](https://docs.godotengine.org/en/stable/tutorials/ui/size_and_anchors.html),
[Using containers](https://docs.godotengine.org/en/stable/tutorials/ui/gui_containers.html).

## Text, fonts and themes

A `Label` shows text. Its font, size and colour are under **Theme Overrides** in the Inspector, and the pages in this
guide set them there, label by label. That's fine for a few labels, but for a whole machine there are two better
options:

- A **Theme** is a resource holding fonts, sizes and colours for every kind of node. Set it on a slide's root (or on
  the window) and every node below it uses it. Change the theme and every slide follows.
- A **LabelSettings** resource styles one label, or several that share it, and adds an outline and a shadow.

To use your own font, copy the `.ttf` or `.otf` file into the project folder and drag it from the FileSystem panel onto
a font property. For a DMD or other pixel-art look, use a pixel font and turn off antialiasing in its import settings
(see [A 128×32 DMD](/gmc/dmd/)).

Learn more: [Using fonts](https://docs.godotengine.org/en/stable/tutorials/ui/gui_using_fonts.html),
[Introduction to GUI skinning](https://docs.godotengine.org/en/stable/tutorials/ui/gui_skinning.html) (themes),
[Using the theme editor](https://docs.godotengine.org/en/stable/tutorials/ui/gui_using_theme_editor.html),
[LabelSettings](https://docs.godotengine.org/en/stable/classes/class_labelsettings.html).

## Images, sound and video

To use a file, copy it into the project folder (in Explorer or Finder is fine). Godot notices it and **imports** it:
it converts the file into a form the engine uses, and keeps the settings for that in a `.import` file next to it. To
change those settings, for example to loop a music file, select the file in the FileSystem panel, open the **Import**
tab next to the Scene tab, change the setting and click **Reimport**.

- **Images** go on a slide with a `TextureRect` node: drag the image onto its **Texture** property.
- **Sounds** go in a `sounds/` folder, where GMC's `sound_player` finds them (see [Sound](/gmc/sound/#sound-files)).
- **Video** plays with GMC's `MPFVideoPlayer` node, which is Godot's `VideoStreamPlayer`. Godot plays Ogg Theora
  (`.ogv`) video, so convert other formats first.

Learn more: [Importing images](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html),
[Importing audio samples](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_audio_samples.html),
[Playing videos](https://docs.godotengine.org/en/stable/tutorials/animation/playing_videos.html),
[Audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html).

## Scripts

Most GMC content needs no code: GMC's node types do the work, and you set them up in the Inspector. When you do want
code, it's GDScript, a Python-like language built into Godot. You attach a script to a node with right-click >
**Attach Script** (or **Extend Script**, on a node that already has one of GMC's scripts), and it opens in the
**Script** screen.

The parts of GDScript that come up with GMC:

- **`extends`** at the top names the node type the script adds to: `extends Label`, or `extends MPFSlide` for a slide's
  root ([Events](/gmc/events/#calling-a-slides-code-from-slide_player)).
- **`@export`** before a variable makes it a property in the Inspector. That's where GMC's node types get their
  settings: **Variable Name** on an `MPFVariable` is an `@export` in GMC's script.
- **`_ready()`** runs when the node appears; **`$Name`** gets a child node by name; **`await`** waits for a timer or a
  signal.
- **The `MPF` autoload.** An autoload is a node Godot creates when the game starts and makes available to every script
  under its name. GMC's is named `MPF` (which is why the install guide insists on that exact name): `MPF.server` sends
  and receives events, `MPF.game` holds the game's state, such as players and running modes, and `MPF.media` finds
  slides, widgets and sounds.

Godot's style is snake_case for file, function and variable names, and PascalCase for node and type names.

Learn more: [Learn to code with GDScript](https://docs.godotengine.org/en/stable/getting_started/introduction/learn_to_code_with_gdscript.html)
(if you haven't programmed before),
[Creating your first script](https://docs.godotengine.org/en/stable/getting_started/step_by_step/scripting_first_script.html),
[GDScript reference](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_basics.html),
[GDScript exported properties](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_exports.html),
[Using signals](https://docs.godotengine.org/en/stable/getting_started/step_by_step/signals.html),
[Singletons (Autoload)](https://docs.godotengine.org/en/stable/tutorials/scripting/singletons_autoload.html),
[GDScript style guide](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_styleguide.html).

## Animation

To animate a slide (a title sliding in, a colour fading), add an **AnimationPlayer** node to it. Selecting it opens the
**Animation** panel at the bottom, where you make named animations: each is a timeline on which you set a node's
property to different values at different times, and Godot moves smoothly between them.

GMC can play these for you. Slides and widgets have an **Animation Player** property in the **MPFSceneBase** section of
the Inspector; point it at the AnimationPlayer, and GMC plays the animations with these names when the slide changes
(from `MPFSceneBase` in GMC's code; not run for this guide):

| Animation name | Plays when |
|---|---|
| `created` | The slide or widget is added. |
| `active` | It becomes the top slide on its display. |
| `removed` | It's removed. GMC waits for the animation to finish before taking it away. |

GMC's code comments also describe an `inactive` animation, for when another slide covers this one, but nothing in GMC
1.0.0 plays it (`MPFSceneBase` only triggers `created`, `active` and `removed`).

Learn more: [Introduction to the animation features](https://docs.godotengine.org/en/stable/tutorials/animation/introduction.html).

## Resolution and windows

The window's size, and how its contents scale when the window is a different size, are Godot project settings
(**Project > Project Settings**, **Display > Window**), not GMC settings. GMC fills whatever size the project has:
[Displays](/gmc/displays/#your-own-window-scene) divides a window into several displays, and
[A 128×32 DMD](/gmc/dmd/#a-128--32-canvas) uses Godot's stretch settings to design at DMD size and show it larger.

Learn more: [Multiple resolutions](https://docs.godotengine.org/en/stable/tutorials/rendering/multiple_resolutions.html)
(stretch modes), [Using viewports](https://docs.godotengine.org/en/stable/tutorials/rendering/viewports.html).

## Shaders

A shader is a small program that changes how something is drawn, pixel by pixel. GMC's screen filters (`pixelate`,
`virtual_dmd`, `dmd_dots`) are shaders, and a `.gdshader` file of your own can be used as a filter too (see
[Screen filters](/gmc/displays/#screen-filters)). You can use GMC's filters without knowing how shaders work.

Learn more: [Introduction to shaders](https://docs.godotengine.org/en/stable/tutorials/shaders/introduction_to_shaders.html),
[CanvasItem shaders](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/canvas_item_shader.html).

## Project conventions

A Godot **project** is a folder with a `project.godot` file in it. For GMC, that folder is your machine folder, so MPF's
files and Godot's sit side by side. GMC finds content by folder and file name:

| In the project | What it is |
|---|---|
| `project.godot` | Godot's project file, next to MPF's `config/` and `modes/`. |
| `gmc.cfg` | GMC's settings ([Add gmc.cfg](/gmc/install-and-connect/#6-add-gmccfg)). |
| `slides/`, `widgets/`, `sounds/` | GMC's media. The file name (without `.tscn` or the sound's extension) is the name MPF's config uses. |
| `modes/<mode>/slides/`, `.../widgets/`, `.../sounds/` | The same, kept with a mode. |
| `addons/mpf-gmc/` | GMC itself. Don't edit it: updating GMC replaces it. Copy what you want to change into your own folders. |
| `.godot/` | Godot's cache of imported files, rebuilt as needed. |

- **File names are names in MPF's config**, so use snake_case and keep them unique: `slides/ramp_lit.tscn` is the
  slide `ramp_lit`, and two slides with the same file name in different folders replace one another
  ([Slides](/gmc/slides/#making-a-slide)).
- **Move and rename files in the FileSystem panel**, not in Explorer or Finder, so Godot can update the scenes that use
  them.
- **Paths.** Inside Godot, files are written as `res://` paths, starting from the project folder:
  `res://slides/attract.tscn`. `user://` is a separate folder for each computer user, outside the project, where Godot
  writes its log file and GMC looks for `gmc.local.cfg`.
- **Version control.** Commit the project's files, including `.tscn`, `.gd`, `.import` and `.uid` files, and leave out
  `.godot/`. Godot's version-control page lists what to ignore.

Learn more: [Project organization](https://docs.godotengine.org/en/stable/tutorials/best_practices/project_organization.html),
[File paths in Godot projects](https://docs.godotengine.org/en/stable/tutorials/io/data_paths.html),
[Version control systems](https://docs.godotengine.org/en/stable/tutorials/best_practices/version_control_systems.html),
[Exporting projects](https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html)
(see also [Exporting](/gmc/displays/#exporting)).

## Learning more

To go further than this page, start with Godot's [Step by step](https://docs.godotengine.org/en/stable/getting_started/step_by_step/index.html)
section: the pages on nodes and scenes, instances, scripting and signals. The rest of "Getting started" builds a small
2D game; it's good practice with the editor, but it uses game nodes rather than the Control nodes slides are made of.
After that, the user-interface pages linked above (anchors, containers, fonts and themes) cover most of what slides
need.

Inside the editor, **Help > Search Help** (F1) opens the reference page for any node type, GMC's included.
