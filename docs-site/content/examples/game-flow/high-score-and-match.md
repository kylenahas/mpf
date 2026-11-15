---
title: "High scores, match and credits"
weight: 2
summary: "Coins buy credits, high scores ask for initials at the end of the game, and a match draw can win a free credit."
verified: "MPF 0.82.0.dev0, smart virtual platform"
---

**The rule.** The machine is on credit play: one coin buys one credit, and each player added costs a credit. At the end
of the game, every player whose score makes the high score table is asked for their initials. Then comes the match: a
two-digit number is drawn, and each player whose score ends in those two digits wins a free credit.

**What it uses.** MPF's built-in `credits`, `high_score` and `match` modes. All three come with MPF; this example
switches them on and configures them.

{{< tip >}}
**Verified.** Run on MPF 0.82.0.dev0 with `MpfGameTestCase`; the events, scores and credits below are from that run.
The match draw is random, so the test fixed its outcome (see [the test run](#what-happened-in-the-test-run)).
{{< /tip >}}

## How it works

### The modes

```yaml
modes:
  - base
  - credits
  - high_score
  - match
```

`credits` runs all the time. `high_score` and `match` both start on `game_ending` and hold the end of the game until
they're done (`use_wait_queue`). `high_score` has the higher priority (1500 against 1000), so it runs first, then the
match.

### Credits

```yaml
switches:
  s_coin:
    number:

credits:
  free_play: false
  switches:
    - switch: s_coin
      value: 0.50
      type: money
  pricing_tiers:
    - price: 0.50
      credits: 1
  events:
    - event: match_has_match
      credits: winners
      type: match
```

- `free_play: false` turns credit play on: the start button only starts a game, and adds a player, if there is a
  credit. MPF's default is free play.
- Each coin is worth 0.50, and a 0.50 tier buys one credit.
- `events` gives credits on an event. `credits` can use the event's arguments: `match_has_match` has `winners`, the
  number of players who matched, so each winner gets one.

In the test run, the start button did nothing with no credits. Two coins made 2 credits (the machine variable
`credits_string` read `CREDITS 2`), starting a game and adding a second player used both, and a third press of start
did nothing.

### High scores

The `high_score` mode's table is set in the mode's own config, which you copy into your machine as
`modes/high_score/config/high_score.yaml` (see
[Changing a built-in mode](/build/modes/#changing-a-built-in-mode)):

```yaml
#config_version=6

high_score:
  enter_initials_timeout: 30
  categories:
    _overwrite: true
    score:
      - GRAND CHAMPION
      - HIGH SCORE 1
      - HIGH SCORE 2
      - HIGH SCORE 3
  defaults:
    _overwrite: true
    score:
      - AAA: 10000
      - BBB: 5000
      - CCC: 2000
      - DDD: 1000
```

{{< warn >}}
**`_overwrite: true` is needed in both lists.** MPF appends a list in your copy of a built-in mode to its own. In a first
version without `_overwrite`, the table started with MPF's own five default scores (`BRI`, `GHK`, ...), the four
defaults above were added after them, and a player in fifth place was offered `HIGH SCORE 4`, a place from MPF's list.
{{< /warn >}}

- `categories` lists the places in order. `score` is the player variable that's compared; another category can rank
  any other player variable.
- `defaults` fills the table the first time, and again when `high_scores_reset` is posted.
- For each player who places, the mode posts `high_score_enter_initials` and waits up to `enter_initials_timeout`
  seconds for `text_input_high_score_complete` with the initials in `text`. A player who doesn't finish in time isn't
  added to the table.
- After each entry it posts `high_score_award_display` and waits `award_slide_display_time` (4 s by default).

Entering initials is up to the media controller: MPF's `high_score` mode plays a `high_score` slide on
`high_score_enter_initials`, and turns the flipper buttons and start into `text_input` events to move through the
letters. GMC 1.0.0 comes with a `high_score` slide and an `MPFTextInput` node that sends `text_input_high_score_complete`
(`addons/mpf-gmc/slides/high_score.tscn`, `classes/mpf_text_input.gd`). That part wasn't run here: the test posted
`text_input_high_score_complete` itself.

The table is kept in machine variables, `score1_name` and `score1_value` for the first place and so on, which a display
can show in attract mode. MPF saves it in the machine folder as `data/high_scores.yaml` (`paths: high_scores` in `mpf/mpfconfig.yaml`), so
it survives a restart; the test run doesn't write that file.

### The match

The match needs no config. It takes the last two digits of each player's score and draws a number, ending in 0 (`00`
to `90`) unless someone matches. It posts `match_has_match` or `match_no_match`, with `winner_number`, `winners`, and
for each player `match_number<n>` and `match_number<n>_won`, counting players from 0. The draw is also kept in the
machine variable `match_number`.

How often there's a match is the `match_percentage` operator setting, 10% by default (`Match.__init__`).

Every score in this machine ends in 00 except the standup target's 10, so the target is what makes the match digits
differ between players.

## What happened in the test run

A two-player game, three balls each. The match draw was fixed in the test with a mock of Python's `random`, so that
the match landed on player 2's number.

| Step | Credits | What happened |
|---|---|---|
| Machine starts | 0 | The table holds the four defaults: AAA 10,000, BBB 5,000, CCC 2,000, DDD 1,000 |
| Start button | 0 | Nothing: no credit |
| Two coins | 2 | `credits_added` twice |
| Start, start | 0 | `game_started` with two players |
| Start again | 0 | Nothing: no credit for a third player |
| Three balls each | 0 | Player 1 ends on 15,060, player 2 on 3,150 |
| The last ball drains | 0 | `high_score_enter_initials` for player 1, `GRAND CHAMPION`, 15,060 |
| `ACE` entered | 0 | `high_score_award_display` with `player_name: ACE`; 4 s later `high_score_enter_initials` for player 2, `HIGH SCORE 3`, 3,150 |
| 30 s with no initials | 0 | Player 2 isn't added. `match_has_match` with `winner_number: 50`, `winners: 1`, `match_number0: 60`, `match_number1: 50` |
| | 1 | `credits_added`: one credit for the match, then `game_ended` |

The table afterwards: ACE 15,060, AAA 10,000, BBB 5,000, CCC 2,000; the machine variable `match_number` was 50.

## The complete machine

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - credits
  - high_score
  - match

machine:
  balls_installed: 2

switches:
  s_start:
    number:
    tags: start
  s_coin:
    number:
  s_trough1:
    number:
  s_trough2:
    number:
  s_ramp:
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

credits:
  free_play: false
  switches:
    - switch: s_coin
      value: 0.50
      type: money
  pricing_tiers:
    - price: 0.50
      credits: 1
  events:
    - event: match_has_match
      credits: winners
      type: match

virtual_platform_start_active_switches: s_trough1, s_trough2
```

`modes/base/config/base.yaml`:

```yaml
#config_version=6

mode:
  start_events: ball_starting
  stop_events: ball_will_end
  priority: 100

variable_player:
  s_ramp_active:
    score: 1000
  s_target_active:
    score: 10
```

`modes/high_score/config/high_score.yaml`:

```yaml
#config_version=6

high_score:
  enter_initials_timeout: 30
  categories:
    _overwrite: true
    score:
      - GRAND CHAMPION
      - HIGH SCORE 1
      - HIGH SCORE 2
      - HIGH SCORE 3
  defaults:
    _overwrite: true
    score:
      - AAA: 10000
      - BBB: 5000
      - CCC: 2000
      - DDD: 1000
```
