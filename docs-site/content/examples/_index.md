---
title: "Examples"
weight: 4
summary: "Complete rule sets that combine several devices, modeled on rules found in many pinball machines."
---

Each guide in [Build a machine](/build/) explains one area. These examples put several of them together into a rule a
player would recognize from real machines: a bonus count at the end of the ball, a multiball with jackpots, a set of
missions that leads to a wizard mode. The rules are generic patterns, not copies of any particular game.

Every example is a complete machine folder: a machine config and its mode files, all shown on the page, run on
MPF 0.82.0.dev0 with `MpfGameTestCase`. The "what happened" table on each page is from that run, and
`docs-site/verify/test_guides.py` repeats it.

| Example | Combines |
|---|---|
| [End-of-ball bonus](/examples/end-of-ball-bonus/) | `variable_player`, player variables, a shot group with lane change, the built-in `bonus` mode, conditions, `flipper_cancel` |
| [Multiball with jackpots](/examples/multiball-jackpots/) | counters, `multiballs`, a mode tied to the multiball, shots, shot groups, a growing jackpot value |
| [Missions and a wizard mode](/examples/mission-ladder/) | achievements, achievement groups, one mode per mission, counters, timers, `\|block` |

To try one, run `mpf init` in a new folder, replace `config/config.yaml` and the mode files with the ones on the page,
and start it with `mpf game -X`. The [switch player](/get-started/first-machine/#5-press-start-without-hardware) can
press the switches for you.
