---
title: "Sound and sound_player"
weight: 6
summary: "Set up audio buses for music, effects and callouts, play sounds from MPF with sound_player, duck the music under callouts, and stop sounds."
verified: "GMC 1.0.0, Godot 4.7.2, MPF 0.82.0.dev0 (both programs run together)"
---

GMC plays sound through Godot's audio system. You sort sounds onto **buses** (music, effects, voice callouts), tell
GMC how each bus behaves, and play sounds from MPF with `sound_player`. This page sets up three buses and plays music,
callouts and effects during a game.

{{< tip >}}
**Verified.** The machine at the end of this page was run with GMC and MPF together on the smart virtual platform,
with the switch hits scripted. Instead of listening, a test-only script asked GMC, at set moments, which sound each bus
was playing and how loud each bus was; the results below are from those runs.
{{< /tip >}}

It builds on [Slides and slide_player](/gmc/slides/): the same machine and `base` slide, with sounds added.

## Sound files

Sounds go in a `sounds/` folder (in the project, or in `modes/<mode>/sounds/`). GMC picks up `.wav`, `.ogg` and
`.mp3` files, and the file name without its extension is the sound's name: `sounds/callout_ramp.wav` is the sound
`callout_ramp` (`GMCMedia.generate_traversal`). The example uses five short WAV files: `music`, `callout_ramp`,
`callout_target`, `jackpot` and `tick`.

A sound can also be an `.tres` file holding an **MPFSoundAsset** resource, which wraps an audio file with default
settings (bus, fades, loops, ducking). If a `.tres` and an audio file have the same name, the `.tres` wins. MPFSoundAsset
wasn't run for this page.

## Audio buses

A bus is a channel in Godot's mixer with its own volume. GMC needs two things for each bus: the bus itself in Godot,
and a line in `gmc.cfg` saying how GMC uses it.

### 1. Make the buses in Godot

Open the **Audio** panel at the bottom of the editor, add a bus for each kind of sound, name them, and save the layout.
Godot saves it as `default_bus_layout.tres` in the project root. The example has `music`, `sfx` and `voice`, all
sending to `Master`:

{{< scenefile "default_bus_layout.tres" >}}
`default_bus_layout.tres`:

```ini
[gd_resource type="AudioBusLayout" format=3]

[resource]
bus/1/name = &"music"
bus/1/solo = false
bus/1/mute = false
bus/1/bypass_fx = false
bus/1/volume_db = 0.0
bus/1/send = &"Master"
bus/2/name = &"sfx"
bus/2/solo = false
bus/2/mute = false
bus/2/bypass_fx = false
bus/2/volume_db = 0.0
bus/2/send = &"Master"
bus/3/name = &"voice"
bus/3/solo = false
bus/3/mute = false
bus/3/bypass_fx = false
bus/3/volume_db = 0.0
bus/3/send = &"Master"
```
{{< /scenefile >}}

### 2. Describe them in gmc.cfg

A `[sound_system]` section in `gmc.cfg` has one line per bus, named after the bus, with a Godot dictionary of settings.
This is the whole `gmc.cfg` for this page; the first two sections are from the
[install page](/gmc/install-and-connect/#6-add-gmccfg):

`gmc.cfg`:

```ini
[cli]
godot_exec_path="C:/Tools/Godot/Godot_v4.7.2-stable_win64.exe"

[gmc]
exit_on_esc=true

[sound_system]
music={"type": "solo"}
sfx={"type": "simultaneous", "simultaneous_sounds": 4, "default": true}
voice={"type": "sequential"}
```

| Setting | What it does |
|---|---|
| `type` | Required. How the bus plays sounds, see the next table. |
| `simultaneous_sounds` | For `simultaneous` and `sequential` buses: how many sounds can play at once. Default 1. |
| `default` | `true` on one bus: sounds without a `bus:` play here. |
| `duck_default` | `true` on one bus: ducking without a `bus:` lowers this one. |

| `type` | Behaviour | In the test run |
|---|---|---|
| `solo` | One sound at a time; a new sound stops the one playing (read from the code). For music. | `music` looped on its own. |
| `simultaneous` | Up to `simultaneous_sounds` at once, each in its own channel. For effects. | `jackpot` played on `sfx`, the default bus, with no `bus:` setting. |
| `sequential` | One at a time, with the rest queued and played in order. For callouts that shouldn't talk over each other. | A target callout played while the ramp callout was still going waited, then played as soon as the first finished. |

Every bus in `[sound_system]` must exist in Godot's bus layout; GMC stops with `Sound system does not have an audio bus
'<name>' configured.` if one doesn't (`initialize` in `scripts/sound_player.gd`, read from the code). Playing a sound with no `bus:`
and no `default` bus is an error too: `Sound played without bus param and no default bus is specified`.

### Volume from MPF

GMC follows MPF's volume machine variables: `master_volume` sets Godot's `Master` bus, and `<bus>_volume` sets a bus
of that name (`_on_volume` in `scripts/sound_player.gd`). In the test run `Master` was at 50%, MPF's default `master_volume` of 0.5.

## Playing sounds

```yaml
sound_player:
  mode_base_started:
    music:
      bus: music
      loops: -1
  s_target_active:
    jackpot: {}
```

Each entry is an event, then one or more sounds with their settings. `{}` means "no settings": `jackpot` plays once on
the default bus. These are the settings GMC uses:

| Setting | What it does |
|---|---|
| `action` | `play` (default), `stop`, or `replace` (stop everything on the bus, then play this). |
| `bus` | The bus to play on. |
| `loops` | `-1` repeats until stopped. Other values set a number of loops; only `-1` was run. |
| `fade_in`, `fade_out` | Fade times. `fade_out` is used when the sound is stopped. |
| `start_at` | Start this far into the file. |
| `max_queue_time` | On a sequential bus, give up if the sound has waited this long. |
| `ducking` | Lower another bus while this sound plays, see [below](#ducking). |
| `events_when_played`, `events_when_stopped` | Events GMC posts to MPF when the sound starts and ends. |
| `key` | An identity for `stop`, if not the sound's name. |

MPF's `sound_player` also accepts `volume`, `pan`, `delay`, `priority`, `block`, `about_to_finish_time`,
`events_when_looping` and `events_when_about_to_finish`, but GMC's sound code doesn't read them, so they have no effect
(searched in `scripts/sound_player.gd` and `scripts/audio/`).

## Ducking

Ducking lowers one bus while a sound plays on another, so a callout can be heard over the music:

```yaml
sound_player:
  s_ramp_active:
    callout_ramp:
      bus: voice
      ducking:
        bus: music
        attenuation: 0.5
        attack: 100ms
        release: 300ms
        release_point: 0
```

| Setting | What it does |
|---|---|
| `bus` | The bus to lower. |
| `attenuation` | How much to lower it, from `0.0` (not at all) to `1.0` (silent). `0.5` halves its volume. |
| `attack` | How long the bus takes to go down. |
| `release` | How long it takes to come back up. |
| `release_point` | Start coming back up this long before the sound ends. |
| `delay` | Wait this long before going down. |

MPF requires all of these except `delay`. In the test run, the `music` bus was at 100% before the ramp, 50% while the
ramp callout and then the queued target callout played, and back at 100% after both had finished. It was at 50% at both checks taken during the callouts, one during each.

## Stopping sounds

`action: stop` stops a sound:

```yaml
sound_player:
  mode_hurry_stopped:
    tick:
      action: stop
```

`stop` looks for the sound on its bus (the default bus here) and stops it, fading it out first if it has a `fade_out`
(read from the code).

{{< warn >}}
**A mode's sounds may keep playing after the mode stops.** The `hurry` mode in the example plays a looping `tick` and
has no other players. When it stopped, the tick carried on (in the test run, still playing after the mode had
stopped). When a mode stops, MPF sends GMC a `sounds_clear` command for it, which GMC ignores; GMC stops a mode's sounds
only on the `slides_clear` and `widgets_clear` commands (`_thread_poll` in `scripts/bcp_server.gd`), which MPF sends only for modes that
use `slide_player` or `widget_player`.

Stop such sounds explicitly. The example does it from the `base` mode, with the `mode_hurry_stopped` entry above; with
it, the tick stopped when `hurry` did.
{{< /warn >}}

{{< warn >}}
**`action: stop_looping` plays the sound again instead of letting it finish.** MPF accepts `stop_looping`, but GMC only
acts on an action named `loop_stop` (`play_sounds` in `scripts/sound_player.gd`), so `stop_looping` is treated like `play`. In a test
run with `stop_looping` in place of `stop` above, a second `tick` started alongside the first, and both kept looping.
Use `stop` (with a `fade_out` if you want it to end gently).
{{< /warn >}}

## Events GMC sends back

`events_when_played` and `events_when_stopped` name events for GMC to post when the sound starts and when it ends.
With the ramp callout on its own:

```yaml
sound_player:
  s_ramp_active:
    callout_ramp:
      bus: voice
      events_when_played: ramp_callout_started
      events_when_stopped: ramp_callout_done
```

In the test run `ramp_callout_started` arrived as the ramp was hit and `ramp_callout_done` 1.0 seconds later, the
length of the file.

{{< warn >}}
**`events_when_stopped` misfires when another sound follows on the same channel.** With the target callout queued
behind the ramp callout on the `voice` bus, `ramp_callout_done` was posted twice: once when the ramp callout ended and
again when the target callout ended. Godot also logged `Invalid type in function 'disconnect' in base 'Signal'. Cannot
convert argument 1 from Nil to Callable.` The handler that posts the event looks for its settings on the channel's
current sound, which by then is the next one (`GMCChannel._trigger_events`). In another run, where both callouts had
`events_when_stopped`, the first callout's event was posted once and the second callout's was never posted. Don't rely
on `events_when_stopped` for sounds that can be followed directly by another on the same bus.
{{< /warn >}}

## The complete machine

The machine config is the one from [Slides and slide_player](/gmc/slides/#the-complete-machine) with a `hurry` mode
and its switch; `gmc.cfg` and `default_bus_layout.tres` are above.

`config/config.yaml`:

```yaml
#config_version=6

modes:
  - base
  - hurry

machine:
  balls_installed: 1

switches:
  s_start:
    number:
    tags: start
  s_trough1:
    number:
  s_ramp:
    number:
    tags: playfield_active
  s_target:
    number:
    tags: playfield_active
  s_lock:
    number:
    tags: playfield_active

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

sound_player:
  mode_base_started:
    music:
      bus: music
      loops: -1
  s_ramp_active:
    callout_ramp:
      bus: voice
      ducking:
        bus: music
        attenuation: 0.5
        attack: 100ms
        release: 300ms
        release_point: 0
  s_target_active:
    callout_target:
      bus: voice
      ducking:
        bus: music
        attenuation: 0.5
        attack: 100ms
        release: 300ms
        release_point: 0
    jackpot: {}
  mode_hurry_stopped:
    tick:
      action: stop
```

`modes/hurry/config/hurry.yaml`:

```yaml
#config_version=6

mode:
  start_events: s_lock_active
  stop_events: s_ramp_active
  priority: 200

sound_player:
  mode_hurry_started:
    tick:
      loops: -1
```

The `base` slide is `slides/base.tscn` from the [slides page](/gmc/slides/#the-complete-machine). The sound files are
any short WAV files with the names above; the test run used generated tones (`music` 3 s, the callouts 1 s, `jackpot`
and `tick` 0.5 s).
