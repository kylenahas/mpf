---
title: "Examples"
weight: 4
summary: "Complete rule sets that combine several devices, modeled on rules found in many pinball machines."
---

Each guide in [Build a machine](/build/) explains one area. These examples put several of them together into a rule a
player would recognize from real machines: a bonus count at the end of the ball, a multiball with jackpots, a kickback, a set of
missions that leads to a wizard mode. The rules are generic patterns, not copies of any particular game.

Every example is a complete machine folder: a machine config and its mode files, all shown on the page, run on
MPF 0.82.0.dev0 with `MpfGameTestCase`. The "what happened" table on each page is from that run, and
`docs-site/verify/test_guides.py` repeats it.

The examples are grouped by kind of rule:

| Group | Examples |
|---|---|
| [Scoring](/examples/scoring/) | [End-of-ball bonus](/examples/scoring/end-of-ball-bonus/), [Combos](/examples/scoring/combos/), [Hurry-up](/examples/scoring/hurry-up/) |
| [Multiball](/examples/multiball/) | [Multiball with jackpots](/examples/multiball/multiball-jackpots/) |
| [Keeping the ball in play](/examples/ball-in-play/) | [Ball save, kickback and outlanes](/examples/ball-in-play/ball-save-and-kickback/), [Drop target bank and extra ball](/examples/ball-in-play/drop-targets-extra-ball/) |
| [Game flow](/examples/game-flow/) | [Missions and a wizard mode](/examples/game-flow/mission-ladder/) |

To try one, run `mpf init` in a new folder, replace `config/config.yaml` and the mode files with the ones on the page,
and start it with `mpf game -X`. The [switch player](/get-started/first-machine/#5-press-start-without-hardware) can
press the switches for you.
