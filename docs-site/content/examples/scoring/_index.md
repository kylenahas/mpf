---
title: "Scoring"
weight: 1
summary: "Rules that build up points: an end-of-ball bonus, combos, a hurry-up, super pops and a playfield multiplier."
---

Rules that build up points during the ball and award them.

| Example | Combines |
|---|---|
| [End-of-ball bonus](/examples/scoring/end-of-ball-bonus/) | `variable_player`, player variables, a shot group with lane change, the built-in `bonus` mode, conditions, `flipper_cancel` |
| [Combos](/examples/scoring/combos/) | switch tags, a mode for the combo window, a timer restarted by each shot, a player variable for the chain |
| [Hurry-up](/examples/scoring/hurry-up/) | a mode, a timer whose ticks lower a player variable, `event_player` to stop the mode after scoring |
| [Pop bumpers and super pops](/examples/scoring/super-pops/) | autofire coils, a switch tag, two counters with `persist_state`, a timed mode |
| [Playfield multiplier](/examples/scoring/playfield-multiplier/) | a player variable in every score, a timed mode, a timer restarted by each hit, a condition capping the multiplier |
