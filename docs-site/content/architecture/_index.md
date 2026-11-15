---
title: "For developers"
weight: 6
summary: "How MPF works inside, and how to extend it: events, mode code, custom code, testing, devices, startup and config, BCP and platforms."
---

This section is for when config isn't enough, or when you want to know why MPF behaves the way it does. Each page is
written so that config writers can follow it, and like the rest of the site, every page was checked by running MPF.

**Writing code for your machine**

- [Writing mode code](/architecture/mode-code/): a Python class for a mode, its lifecycle, handlers and delays that
  clean up after themselves, the player, and settings from the mode's config.
- [Machine-wide custom code](/architecture/custom-code/): code that runs from startup and between games, and when to
  use it instead of mode code.
- [Testing your machine](/architecture/testing/): automated tests for your own rules with MPF's test classes, in
  simulated time.

**How MPF works inside**

- [How events work](/architecture/how-events-work/): the event queue, handler order, the four kinds of events, a full
  game's event timeline, and events in custom code.
- [Devices](/architecture/devices/): collections, machine-wide and mode devices, control events and their delays, and
  the attributes conditions can read.
- [From boot to game](/architecture/boot-and-config/): loading and merging config files, the config cache, the init
  phases and the reset into attract mode.
- [BCP: talking to a media controller](/architecture/bcp/): what travels between MPF and GMC, and what a media
  controller can ask MPF to do.
- [Platforms and hardware rules](/architecture/platforms/): choosing hardware platforms, the rules that fire flippers
  and slingshots, and the virtual platforms.
