---
title: "Multiball with jackpots"
weight: 1
aliases: ["/examples/multiball-jackpots/"]
summary: "Three targets start a two-ball multiball; the ramps light jackpots, both ramps light a super jackpot, and targets raise the value."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** Hit the target three times to start a two-ball multiball. During the multiball, each ramp is a lit
jackpot worth the current jackpot value (10,000 to start). Collecting both ramps lights the super jackpot in the
scoop, worth five times the jackpot value; collecting it relights both ramps for another round. Every target hit
during the multiball adds 1,000 to the jackpot value. When the multiball ends, so do the jackpots, and the next
multiball needs three new target hits and starts back at 10,000.

**What it uses.** A [counter](/build/events/#something-was-hit-n-times) to start a
[multiball](/build/multiball/#the-multiball), a [mode](/build/modes/) that runs exactly as long as the multiball, and
[shots and a shot group](/build/shots-and-scoring/#shots) for the jackpots, with a player variable holding the
jackpot value.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the scores and states below are from that run.
{{< /tip >}}

## How it works

### Starting the multiball

The `base` mode counts target hits and starts the multiball on the third:

```yaml
counters:
  multiball_targets:
    count_events: s_target_active
    count_complete_value: 3
    events_when_complete: start_multiball
    start_enabled: true
    enable_events: multiball_main_mb_ended

multiballs:
  main_mb:
    ball_count: 2
    start_events: start_multiball
    shoot_again: 5s
```

When a counter completes, it resets and disables itself by default (`reset_on_complete` and `disable_on_complete`), so
target hits during the multiball do not count toward the next one. `enable_events: multiball_main_mb_ended` turns
it back on afterwards. Because the counter now has an `enable_events`, it would otherwise start disabled, so
`start_enabled: true` keeps it on at the start of each ball (`LogicBlock._initialize`).

{{< note >}}
A first version of this example used `disable_on_complete: false` instead. Then the targets hit during the multiball
(to raise the jackpot) also counted toward the next multiball: after two of them, the very first target hit after the
multiball ended started the second multiball.
{{< /note >}}

### A mode for the length of the multiball

All jackpot rules live in a `jackpots` mode that starts and stops with the multiball:

```yaml
mode:
  start_events: multiball_main_mb_started
  stop_events: multiball_main_mb_ended
  priority: 200
```

Its shots, shot group and scoring exist only while the multiball runs, so a ramp outside the multiball scores nothing
here. Each time the mode starts, the jackpot value is set back to 10,000:

```yaml
variable_player:
  mode_jackpots_started:
    jackpot_value:
      int: 10000
      action: set
  s_target_active:
    jackpot_value: 1000
```

### Jackpots and the super jackpot

A two-state profile, `lit` then `collected`, makes each ramp score once:

```yaml
shot_profiles:
  jackpot:
    states:
      - name: lit
      - name: collected
```

```yaml
shots:
  left_jackpot:
    switch: s_left_ramp
    profile: jackpot
  right_jackpot:
    switch: s_right_ramp
    profile: jackpot
  super_jackpot:
    switch: s_scoop
    profile: jackpot
    start_enabled: false
    enable_events: jackpots_collected_complete
    disable_events: super_jackpot_lit_hit
    reset_events: super_jackpot_lit_hit

shot_groups:
  jackpots:
    shots: left_jackpot, right_jackpot
    reset_events: mode_jackpots_started, super_jackpot_lit_hit

variable_player:
  jackpots_lit_hit:
    score: current_player.jackpot_value
  super_jackpot_lit_hit:
    score: current_player.jackpot_value * 5
```

- A ramp hit while `lit` posts `jackpots_lit_hit` through the group (the event uses the state **before** the hit)
  and scores the jackpot. The shot then moves to `collected`, where further hits post `jackpots_collected_hit`
  and score nothing.
- When both ramps are `collected`, the group posts `jackpots_collected_complete`, which enables the super jackpot.
  It starts disabled, so the scoop does nothing before that.
- Collecting the super jackpot scores five times the value, resets both ramps to `lit`, and resets and disables
  itself.
- Shot states are kept per player and would survive into the next multiball, so the group also resets on
  `mode_jackpots_started`.

The `jackpots_lit_complete` event (both ramps lit) is also posted at the start of every round; this example does not
use it. See [shot groups](/build/shots-and-scoring/#shot-groups).

## What happened in the test run

| Step | Score | Jackpot value | Ramps (L, R) | Super jackpot | Balls in play |
|---|---|---|---|---|---|
| Ramp before the multiball | 0 | | (mode not running) | | 1 |
| Three targets: multiball starts | 300 | 10,000 | lit, lit | off | 2 |
| Left ramp: jackpot | 10,300 | 10,000 | collected, lit | off | 2 |
| Left ramp again | 10,300 | | collected, lit | off | |
| Scoop (not lit yet) | 10,300 | | | off | |
| Two targets | 10,500 | 12,000 | | off | |
| Right ramp: jackpot | 22,500 | 12,000 | collected, collected | **on** | |
| Scoop: super jackpot (5 × 12,000) | 82,500 | | lit, lit | off | |
| Scoop again | 82,500 | | | off | |
| Right ramp: jackpot (round 2) | 94,500 | | lit, collected | | |
| One ball drains after `shoot_again`: multiball over | 94,500 | | (mode stopped) | | 1 |
| Ramp after the multiball | 94,500 | | | | 1 |
| Three new targets: second multiball | 94,800 | 10,000 | lit, lit | off | 2 |
| Right ramp: jackpot | 104,800 | 10,000 | lit, collected | | 2 |

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - jackpots

machine:
  balls_installed: 2

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_trough2:
    number:
  s_left_ramp:
    number:
    tags: playfield_active
  s_right_ramp:
    number:
    tags: playfield_active
  s_scoop:
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
    ball_switches: s_trough1, s_trough2
    eject_coil: c_trough_eject
    eject_targets: playfield
    eject_timeouts: 2s
    tags: trough, drain, home

playfields:
  playfield:
    default_source_device: bd_trough
    tags: default

shot_profiles:
  jackpot:
    states:
      - name: lit
      - name: collected

virtual_platform_start_active_switches: s_trough1, s_trough2
```

In a real machine the scoop would be a [ball device](/build/ball-devices/#saucers-and-kickers); here it is a plain
switch to keep the example short.

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

counters:
  multiball_targets:
    count_events: s_target_active
    count_complete_value: 3
    events_when_complete: start_multiball
    start_enabled: true
    enable_events: multiball_main_mb_ended

multiballs:
  main_mb:
    ball_count: 2
    start_events: start_multiball
    shoot_again: 5s

variable_player:
  s_target_active:
    score: 100
```

`modes/jackpots/config/jackpots.yaml`:

```yaml
#config_version=6

mode:
  start_events: multiball_main_mb_started
  stop_events: multiball_main_mb_ended
  priority: 200

shots:
  left_jackpot:
    switch: s_left_ramp
    profile: jackpot
  right_jackpot:
    switch: s_right_ramp
    profile: jackpot
  super_jackpot:
    switch: s_scoop
    profile: jackpot
    start_enabled: false
    enable_events: jackpots_collected_complete
    disable_events: super_jackpot_lit_hit
    reset_events: super_jackpot_lit_hit

shot_groups:
  jackpots:
    shots: left_jackpot, right_jackpot
    reset_events: mode_jackpots_started, super_jackpot_lit_hit

variable_player:
  mode_jackpots_started:
    jackpot_value:
      int: 10000
      action: set
  s_target_active:
    jackpot_value: 1000
  jackpots_lit_hit:
    score: current_player.jackpot_value
  super_jackpot_lit_hit:
    score: current_player.jackpot_value * 5
```
