---
title: "Media controller (GMC)"
weight: 3
summary: "Screens and sound with the Godot Media Controller: install it, connect it to MPF, build slides."
---

MPF runs the rules; it does not draw anything on a screen or play sound itself. A **media controller** does that, and
the current one is the **Godot Media Controller (GMC)**: an add-on for the [Godot](https://godotengine.org) game
engine. You build slides, widgets and sounds in the Godot editor, and MPF tells GMC what to show and play with config
sections such as `slide_player`.

MPF and GMC are two programs that talk over a local network connection using MPF's BCP protocol. GMC listens on port
5050; MPF connects to it as it starts.

These pages were checked with GMC 1.0.0, Godot 4.7.2 and MPF 0.82.0.dev0, by running both programs together.

| Page | What it covers |
|---|---|
| [Install GMC and connect it to MPF](/gmc/install-and-connect/) | Godot, the add-on, the project settings GMC needs, a first slide, and starting both with `mpf both`. |
| [Slides and slide_player](/gmc/slides/) | Where slides live, playing and removing them, priorities and the slide stack, and the events GMC sends back. |
| [Showing scores and variables](/gmc/variables/) | `MPFVariable` labels for player and machine variables, formatting, and values from events, `tokens` and `action: update`. |
| [Widgets and widget_player](/gmc/widgets/) | Small scenes placed on a slide: position, expiry, the overlay above every slide, and what happens as slides and modes change. |
| [Sound and sound_player](/gmc/sound/) | Audio buses for music, effects and callouts, playing and stopping sounds, ducking, and the events GMC sends back. |
| [Choosing from a list: carousels](/gmc/carousel/) | MPF's Carousel mode and GMC's `MPFCarousel` node: an award chooser moved with the flippers. |
| [Events between MPF and Godot](/gmc/events/) | `MPFEventHandler`, calling a slide's code with `action: method`, sending events to MPF, and keyboard keys. |
| [Displays, filters and running GMC on the machine](/gmc/displays/) | Your own window with several displays, `target`, screen filters, window settings, `spawn_mpf` and exporting. |
| [A 128×32 DMD](/gmc/dmd/) | Slides at DMD resolution, the DMD look on a screen with GMC's filter, and frames for a physical DMD through MPF. |
