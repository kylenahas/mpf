"""Check the GMC pages by running MPF and a real Godot + GMC project built from the page.

These tests start Godot with a window, so they only run when you say where things are:

    MPF_DOCS_GODOT   path to the Godot editor binary (e.g. Godot_v4.7.2-stable_win64.exe)
    MPF_DOCS_GMC     path to an mpf-gmc checkout (the folder that contains addons/mpf-gmc)

    venv/Scripts/python -I -m unittest discover -s docs-site/verify -p "test_gmc.py"

Without both variables every test here is skipped, so the normal test run (and CI) is unaffected.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import psutil

from mpf.commands.init import Command as InitCommand

CONTENT = Path(__file__).resolve().parent.parent / "content"
GODOT = os.environ.get("MPF_DOCS_GODOT")
GMC = os.environ.get("MPF_DOCS_GMC")
INSTALL_PAGE = "gmc/install-and-connect.md"
# The `mpf` command from the same environment as this Python, as a user would run it.
MPF_CMD = shutil.which("mpf", path=str(Path(sys.executable).parent))

# A line holding only `path`: , a blank line, then a fenced block of any language.
SLIDES_PAGE = "gmc/slides.md"
CREATED = []   # temp projects made by this run, removed (with their Godot user folders) at the end
# An MPF console log line for a posted event:  12:08:38.842 : INFO [EventManager] Event: ======'name'====== Args={...}
EVENT_LINE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+) : INFO \[EventManager\] Event: ======'([^']+)'====== (.*)$", re.M)

LABELLED = re.compile(r"^`([\w/.-]+)`:[ \t]*\n\s*\n```\w*\s*\n(.*?)^```", re.M | re.S)


def page_files(page):
    return dict(LABELLED.findall((CONTENT / page).read_text(encoding="utf-8")))


def godot_user_dir(project_name):
    """Godot's user data folder for a project (where it keeps logs/godot.log)."""
    if sys.platform == "win32":
        base = Path(os.environ["APPDATA"], "Godot")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Godot"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"), "godot")
    return base / "app_userdata" / project_name


def build_project(files):
    """`mpf init` a temp folder, copy GMC's add-on in, write the given files, and let Godot import the project.

    The project gets a unique name, so this run's Godot log has a folder of its own: launched by `mpf both`, the Windows
    Godot binary doesn't write to the console, so the tests read Godot's log file instead.
    """
    path = Path(tempfile.mkdtemp(prefix="mpf_docs_gmc_"))
    CREATED.append(path)
    InitCommand(["init"], str(path))
    shutil.copytree(Path(GMC, "addons", "mpf-gmc"), path / "addons" / "mpf-gmc")
    files = dict(files)
    if "project.godot" in files:
        files["project.godot"] = re.sub(r'^config/name=".*"$', 'config/name="%s"' % path.name,
                                        files["project.godot"], flags=re.M)
    shutil.rmtree(godot_user_dir(path.name), ignore_errors=True)
    for rel, body in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            (path / rel).write_bytes(body)
        else:
            (path / rel).write_text(body, encoding="utf-8")
    # The page says to open the project in the editor first; that is what imports GMC's images and fonts.
    subprocess.run([GODOT, "--headless", "--path", str(path), "--import"], capture_output=True, timeout=300)
    return path


def with_godot_path(cfg):
    return re.sub(r'^godot_exec_path=".*"$', 'godot_exec_path="%s"' % GODOT.replace("\\", "/"), cfg, flags=re.M)


class BothRun:
    """`mpf both <platform> -t` in a machine folder, with MPF's and Godot's console output collected in one file.

    `-t` turns off MPF's full-screen text UI so MPF prints its log to the console instead (there is no terminal here).
    """

    def __init__(self, path, extra=(), platform="-x"):
        self.path = path
        self.log = path / "both.log"
        self.out = self.log.open("w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen([MPF_CMD, "both", platform, "-t", *extra], cwd=path,
                                     stdout=self.out, stderr=subprocess.STDOUT)

    def events(self):
        """MPF's posted events from the console log, as (seconds since midnight, name, rest of line)."""
        found = []
        for m in EVENT_LINE.finditer(self.text()):
            h, mi, s = m.group(1).split(":")
            found.append((int(h) * 3600 + int(mi) * 60 + float(s), m.group(2), m.group(3)))
        return found

    def text(self):
        """MPF's console output plus Godot's log file."""
        self.out.flush()
        text = self.log.read_text(encoding="utf-8", errors="replace")
        godot_log = godot_user_dir(self.path.name) / "logs" / "godot.log"
        if godot_log.exists():
            text += "\n" + godot_log.read_text(encoding="utf-8", errors="replace")
        return text

    def wait_for(self, needle, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if needle in self.text():
                return True
            if self.proc.poll() is not None:
                break
            time.sleep(.25)
        return needle in self.text()

    def godot(self):
        try:
            return [p for p in psutil.Process(self.proc.pid).children(recursive=True)
                    if "godot" in p.name().lower()]
        except psutil.NoSuchProcess:
            return []

    def stop(self):
        for p in self.godot():
            p.kill()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.out.close()


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestInstallAndConnect(unittest.TestCase):
    """gmc/install-and-connect.md: the project files on the page, started with `mpf both -x`."""

    def files(self):
        files = page_files(INSTALL_PAGE)
        self.assertEqual({"project.godot", "slides/attract.tscn", "gmc.cfg"}, set(files))
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        return files

    def test_connects_and_shows_attract(self):
        run = BothRun(build_project(self.files()))
        try:
            self.assertTrue(run.wait_for("slide_attract_active"), run.text()[-3000:])
            text = run.text()
            self.assertIn("GMC listening on port 5050", text)
            self.assertIn("Connected BCP to 'local_display' localhost:5050", text)
            self.assertNotIn("SCRIPT ERROR", text)
            self.assertNotIn("Unable to find gmc.cfg", text)
            # Closing GMC shuts MPF down
            godot = run.godot()
            self.assertEqual(1, len(godot))
            godot[0].kill()
            self.assertTrue(run.wait_for("BCP client local_display disconnected and exit_on_close is set", 20))
            run.proc.wait(20)
        finally:
            run.stop()

    def test_without_attract_slide_or_gmc_cfg(self):
        files = self.files()
        del files["slides/attract.tscn"]
        del files["gmc.cfg"]
        run = BothRun(build_project(files), extra=["-G", GODOT])
        try:
            self.assertTrue(run.wait_for("Unknown slide name 'attract'"), run.text()[-3000:])
            text = run.text()
            self.assertIn("Unable to find gmc.cfg in the project root.", text)
            self.assertIn("Slide scenes must use (or extend) the MPFSlide script on the root node", text)
        finally:
            run.stop()

    def test_autoload_must_be_named_mpf(self):
        files = self.files()
        files["project.godot"] = files["project.godot"].replace('MPF="*res://', 'Mpf="*res://')
        path = build_project(files)
        result = subprocess.run([GODOT, "--headless", "--path", str(path), "--quit-after", "120"],
                                capture_output=True, text=True, errors="replace", timeout=120)
        self.assertIn('Identifier "MPF" not declared in the current scope', result.stdout + result.stderr)


# Test-only: scripted switch hits (MPF's switch_player), appended to the page's machine config.
SLIDES_SCRIPT = """
switch_player:
  start_event: mode_attract_started
  steps:
    - {time: 1s, switch: s_start, action: hit}
    - {time: 2s, switch: s_ramp, action: hit}
    - {time: 1s, switch: s_target, action: hit}
    - {time: 1s, switch: s_ramp, action: hit}
    - {time: 2s, switch: s_ramp, action: hit}
"""


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestSlides(unittest.TestCase):
    """gmc/slides.md: the page's machine and slides on top of the install page's project, switch hits scripted."""

    def test_stack_removal_and_events(self):
        files = page_files(INSTALL_PAGE)
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        slides = page_files(SLIDES_PAGE)
        self.assertEqual({"config/config.yaml", "modes/base/config/base.yaml", "modes/skillshot/config/skillshot.yaml",
                          "slides/base.tscn", "slides/ramp_lit.tscn", "slides/skillshot.tscn"}, set(slides))
        files.update(slides)
        files["config/config.yaml"] += SLIDES_SCRIPT
        run = BothRun(build_project(files), platform="-X")
        try:
            self.assertTrue(run.wait_for("slide_ramp_lit_removed", 60), run.text()[-3000:])
            time.sleep(8)   # then two more ramp hits (1 s, then 2 s later) and a 3 s expire
            text = run.text()
            self.assertNotIn("SCRIPT ERROR", text)
            ev = run.events()
            names = [n for t, n, a in ev]
            slide = [(t, n, a) for t, n, a in ev if n.startswith("slide_") or n in ("s_ramp_active", "s_target_active")]
            seq = [n for t, n, a in slide]

            # Ball start: the order quoted on the page
            start = seq.index("slide_base_created")
            self.assertEqual(["slide_base_created", "slide_attract_inactive", "slide_base_active", "slide_attract_removed",
                              "slide_skillshot_created", "slide_base_inactive", "slide_skillshot_active"],
                             seq[start:start + 7])
            args = {n: a for t, n, a in slide[start:start + 7]}
            self.assertIn("'is_removing': True", args["slide_attract_inactive"])
            self.assertIn("'is_removing': False", args["slide_base_inactive"])

            # Ramp during the skill shot: created under the banner, never active; the target removes both slides
            r1 = seq.index("s_ramp_active")
            tgt = seq.index("s_target_active")
            self.assertEqual(["s_ramp_active", "slide_ramp_lit_created", "s_target_active"], seq[r1:tgt + 1])
            after_target = seq[tgt + 1:seq.index("s_ramp_active", tgt)]
            self.assertIn("slide_skillshot_removed", after_target)
            self.assertIn("slide_ramp_lit_removed", after_target)
            self.assertIn("slide_base_active", after_target)

            # Two ramp hits 2 s apart: one slide, removed 3 s after the second hit
            ramps = [i for i, n in enumerate(seq) if n == "s_ramp_active"]
            self.assertEqual(3, len(ramps))
            between = seq[ramps[1]:]
            self.assertEqual(1, between.count("slide_ramp_lit_created"))
            removed = [t for t, n, a in slide[ramps[2]:] if n == "slide_ramp_lit_removed"]
            self.assertEqual(1, len(removed))
            self.assertAlmostEqual(3.0, removed[0] - slide[ramps[2]][0], delta=0.3)
            self.assertIn("slide_ramp_lit_active", seq[ramps[1]:ramps[2]])
            self.assertIn("mode_skillshot_started", names)
        finally:
            run.stop()


VARIABLES_PAGE = "gmc/variables.md"

# Test-only autoload: when MPF posts `doc_shot`, print the text of every MPFVariable on screen to Godot's log.
PROBE_GD = """extends Node

var count := 0

func _ready() -> void:
\tMPF.server.status_changed.connect(self._on_status)

func _on_status(status) -> void:
\tif status == MPF.server.ServerStatus.CONNECTED:
\t\tMPF.server.add_event_handler("doc_shot", self._shot)
\t\tMPF.server.add_event_handler("doc_key", self._key)

# Simulate pressing and releasing the L key in the GMC window.
func _key(_message = null) -> void:
\tfor pressed in [true, false]:
\t\tvar ev := InputEventKey.new()
\t\tev.keycode = KEY_L
\t\tev.physical_keycode = KEY_L
\t\tev.key_label = KEY_L
\t\tev.pressed = pressed
\t\tInput.parse_input_event(ev)
\t\tawait get_tree().create_timer(0.1).timeout

func _shot(_message = null) -> void:
\tcount += 1
\tawait get_tree().process_frame
\tawait get_tree().process_frame
\tfor node in get_tree().root.find_children("*", "Label", true, false):
\t\tif node is MPFVariable and node.is_visible_in_tree():
\t\t\tprint("DOC_TEXT %d %s=%s" % [count, node.name, node.text])
\t\telif node.is_visible_in_tree():
\t\t\tprint("DOC_LABEL %d %s=%s" % [count, node.name, node.text])
\tfor node in get_tree().root.find_children("*", "Control", true, false):
\t\tif node is MPFWidget:
\t\t\tprint("DOC_WIDGET %d %s on %s" % [count, node.key, node.get_parent().get_parent().name])
\tfor node in get_tree().root.find_children("*", "Control", true, false):
\t\tif node is MPFCarousel:
\t\t\tvar shown := []
\t\t\tfor c in node.get_children():
\t\t\t\tif c.visible:
\t\t\t\t\tshown.append(str(c.name))
\t\t\tprint("DOC_CAROUSEL %d %s=%s" % [count, node.carousel_name, ",".join(shown)])
\tfor node in get_tree().root.find_children("*", "Control", true, false):
\t\tif node is MPFDisplay:
\t\t\tvar top = node.get_slide()
\t\t\tprint("DOC_DISPLAY %d %s=%s" % [count, node.name, top.key if top else ""])
\t\telif node.name == "filters" and node.get_parent() is MPFWindow:
\t\t\tfor f in node.get_children():
\t\t\t\tprint("DOC_FILTER %d %s=%s" % [count, f.name, f.is_visible_in_tree()])
\tfor bus_name in MPF.media.sound.buses:
\t\tvar idx := AudioServer.get_bus_index(bus_name)
\t\tprint("DOC_BUS %d %s %.2f" % [count, bus_name, db_to_linear(AudioServer.get_bus_volume_db(idx))])
\t\tfor ch in MPF.media.sound.buses[bus_name].channels:
\t\t\tif ch.playing and ch.stream:
\t\t\t\tprint("DOC_SOUND %d %s %s" % [count, bus_name, ch.stream.resource_path.get_file().get_basename()])
\tprint("DOC_DONE %d" % count)
"""

# Test-only: a switch whose hits post `doc_shot`, and the scripted game.
VARIABLES_SCRIPT = """
event_player:
  s_doc_shot_active: doc_shot

switch_player:
  start_event: mode_attract_started
  steps:
    - {time: 1s, switch: s_start, action: hit}
    - {time: 2s, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_ramp, action: hit}
    - {time: 500ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_target, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 2500ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_ramp, action: hit}
    - {time: 2500ms, switch: s_doc_shot, action: hit}
"""


def with_probe(files, script):
    """Add the label probe autoload, a `s_doc_shot` switch and a switch_player script to a page's files."""
    files = dict(files)
    files["doc_probe.gd"] = PROBE_GD
    files["project.godot"] = files["project.godot"].replace(
        'MPF="*res://addons/mpf-gmc/mpf_gmc.gd"', 'MPF="*res://addons/mpf-gmc/mpf_gmc.gd"\nDocProbe="*res://doc_probe.gd"')
    files["config/config.yaml"] = files["config/config.yaml"].replace(
        "switches:\n", "switches:\n  s_doc_shot:\n    number:\n", 1) + script
    return files


def label_texts(text):
    """{shot number: {label name: text}} from the probe's DOC_TEXT lines."""
    shots = {}
    for n, name, value in re.findall(r"^DOC_TEXT (\d+) (\w+)=(.*?)\r?$", text, re.M):
        shots.setdefault(int(n), {})[name] = value
    return shots


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestVariables(unittest.TestCase):
    """gmc/variables.md: the page's machine and slides, with the label texts read back from GMC at five moments."""

    def files(self, change=None):
        files = page_files(INSTALL_PAGE)
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        page = page_files(VARIABLES_PAGE)
        self.assertEqual({"config/config.yaml", "modes/base/config/base.yaml", "slides/base.tscn",
                          "slides/ramp_lit.tscn"}, set(page))
        files.update(page)
        files = with_probe(files, VARIABLES_SCRIPT)
        if change:
            change(files)
        return files

    def run_game(self, files):
        run = BothRun(build_project(files), platform="-X")
        try:
            self.assertTrue(run.wait_for("DOC_TEXT 5 ", 60), run.text()[-3000:])
            time.sleep(1)
            text = run.text()
            self.assertNotIn("SCRIPT ERROR", text)
            return label_texts(text), run.events()
        finally:
            run.stop()

    def test_page_machine(self):
        shots, events = self.run_game(self.files())
        self.assertEqual({"Player": "PLAYER 1", "Score": "0", "Ramps": "RAMPS: 0", "Summary": "Ball 1, 0 points",
                          "Credits": "FREE PLAY"}, shots[1])
        self.assertEqual("FROM EVENT", shots[2]["Award"])     # the event argument beats the token
        self.assertEqual("TARGET 250", shots[3]["Award"])     # action: update
        self.assertEqual({"Score": "1,250", "Ramps": "RAMPS: 1", "Summary": "Ball 1, 1250 points"},
                         {k: shots[4][k] for k in ("Score", "Ramps", "Summary")})
        self.assertNotIn("Award", shots[4])
        self.assertEqual({"Score": "2,250", "Ramps": "RAMPS: 2"}, {k: shots[5][k] for k in ("Score", "Ramps")})
        # update did not restart expire: removed 2 s after the slide was played
        played = [t for t, n, a in events if n == "slide_ramp_lit_created"][0]
        removed = [t for t, n, a in events if n == "slide_ramp_lit_removed"][0]
        self.assertAlmostEqual(2.0, removed - played, delta=0.3)

    def test_format_string_without_variable_name(self):
        def change(files):
            files["slides/base.tscn"] = files["slides/base.tscn"].replace(
                'variable_name = "score"\nformat_string', 'format_string')
        shots, events = self.run_game(self.files(change))
        self.assertEqual("Ball 1, 0 points", shots[4]["Summary"])
        self.assertEqual("Ball 1, 0 points", shots[5]["Summary"])

    def test_without_initial_value(self):
        """Documented GMC bug: the first value of a new player variable doesn't reach a label already on screen."""
        def change(files):
            files["config/config.yaml"] = files["config/config.yaml"].replace(
                "player_vars:\n  ramps:\n    initial_value: 0\n\n", "")
        shots, events = self.run_game(self.files(change))
        self.assertEqual("", shots[4]["Ramps"])
        self.assertEqual("RAMPS: 2", shots[5]["Ramps"])

    @unittest.expectedFailure
    def test_without_initial_value_first_ramp_shown(self):
        """What the label should show (fails until GMCGame.update_player reports first values)."""
        def change(files):
            files["config/config.yaml"] = files["config/config.yaml"].replace(
                "player_vars:\n  ramps:\n    initial_value: 0\n\n", "")
        shots, events = self.run_game(self.files(change))
        self.assertEqual("RAMPS: 1", shots[4]["Ramps"])


WIDGETS_PAGE = "gmc/widgets.md"

WIDGETS_SCRIPT = """
event_player:
  s_doc_shot_active: doc_shot

switch_player:
  start_event: mode_attract_started
  steps:
    - {time: 1s, switch: s_start, action: hit}
    - {time: 2s, switch: s_ramp, action: hit}
    - {time: 500ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_target, action: hit}
    - {time: 1300ms, switch: s_doc_shot, action: hit}
    - {time: 1700ms, switch: s_lock, action: hit}
    - {time: 500ms, switch: s_target, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 1500ms, switch: s_ramp, action: hit}
    - {time: 500ms, switch: s_doc_shot, action: hit}
"""
MODE_LOCK_REMOVE = """  mode_lock_stopped:
    lock_lit:
      slide: _overlay
      action: remove
"""


def widget_list(text):
    """{shot number: sorted ['key on slide', ...]} from the probe's DOC_WIDGET lines (every shot, even if empty)."""
    shots = {int(n): [] for n in re.findall(r"^DOC_DONE (\d+)", text, re.M)}
    for n, entry in re.findall(r"^DOC_WIDGET (\d+) (.*?)\r?$", text, re.M):
        shots.setdefault(int(n), []).append(entry)
    return {n: sorted(v) for n, v in shots.items()}


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestWidgets(unittest.TestCase):
    """gmc/widgets.md: the page's machine, widgets and the slides page's two slides, with widgets read back from GMC."""

    def files(self, change=None):
        files = page_files(INSTALL_PAGE)
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        slides = page_files(SLIDES_PAGE)
        files["slides/base.tscn"] = slides["slides/base.tscn"]
        files["slides/ramp_lit.tscn"] = slides["slides/ramp_lit.tscn"]
        page = page_files(WIDGETS_PAGE)
        self.assertEqual({"config/config.yaml", "modes/base/config/base.yaml", "modes/lock/config/lock.yaml",
                          "widgets/jackpot.tscn", "widgets/lock_lit.tscn"}, set(page))
        files.update(page)
        files = with_probe(files, WIDGETS_SCRIPT)
        if change:
            change(files)
        return files

    def run_game(self, files):
        run = BothRun(build_project(files), platform="-X")
        try:
            self.assertTrue(run.wait_for("DOC_DONE 4", 60), run.text()[-3000:])
            time.sleep(4)   # the second jackpot's 3 s expire
            text = run.text()
            self.assertNotIn("SCRIPT ERROR", text)
            return widget_list(text), run.events(), text
        finally:
            run.stop()

    def test_page_machine(self):
        widgets, events, text = self.run_game(self.files())
        overlay = "DefaultDisplay_overlay_slide"
        self.assertEqual(["jackpot on base"], widgets[1])       # on the active slide
        self.assertEqual(["jackpot on base"], widgets[2])       # still on base after ramp_lit covered and expired
        self.assertEqual(["lock_lit on " + overlay], widgets[3])  # jackpot expired; lock_lit on the overlay
        self.assertEqual(["jackpot on base"], widgets[4])       # lock stopped: removed by the base mode's entry
        names = [n for t, n, a in events]
        self.assertIn("widget_lock_lit_removed", names)
        first = [t for t, n, a in events if n == "widget_jackpot_active"][0]
        gone = [t for t, n, a in events if n == "widget_jackpot_removed"][0]
        self.assertAlmostEqual(3.0, gone - first, delta=0.3)

    def without_remove(self, files):
        files["modes/base/config/base.yaml"] = files["modes/base/config/base.yaml"].replace(MODE_LOCK_REMOVE, "")

    def test_overlay_widget_left_behind(self):
        """Documented GMC bug: a mode's overlay widget survives the mode."""
        widgets, events, text = self.run_game(self.files(self.without_remove))
        self.assertIn("lock_lit on DefaultDisplay_overlay_slide", widgets[4])
        self.assertNotIn("widget_lock_lit_removed", [n for t, n, a in events])

    @unittest.expectedFailure
    def test_overlay_widget_cleared_with_mode(self):
        """What should happen (fails until MPFDisplay._on_clear also clears the overlay slide)."""
        widgets, events, text = self.run_game(self.files(self.without_remove))
        self.assertEqual(["jackpot on base"], widgets[4])

    def test_missing_target_slide(self):
        def change(files):
            files["modes/base/config/base.yaml"] += ("  s_target_active:\n    jackpot:\n      slide: attract\n"
                                                     "      key: jackpot_on_attract\n")
        widgets, events, text = self.run_game(self.files(change))
        self.assertIn("Unable to add widget 'jackpot' because target slide 'attract' is not on this display.", text)
        self.assertNotIn("jackpot_on_attract", " ".join(sum(widgets.values(), [])))


SOUND_PAGE = "gmc/sound.md"

SOUND_SCRIPT = """
event_player:
  s_doc_shot_active: doc_shot

switch_player:
  start_event: mode_attract_started
  steps:
    - {time: 1s, switch: s_start, action: hit}
    - {time: 1500ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_ramp, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_target, action: hit}
    - {time: 100ms, switch: s_doc_shot, action: hit}
    - {time: 1000ms, switch: s_doc_shot, action: hit}
    - {time: 2000ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_lock, action: hit}
    - {time: 1000ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_ramp, action: hit}
    - {time: 500ms, switch: s_doc_shot, action: hit}
"""
HURRY_STOP = "  mode_hurry_stopped:\n    tick:\n      action: stop\n"
RAMP_EVENTS = ("      bus: voice\n      ducking:",
               "      bus: voice\n      events_when_played: ramp_callout_started\n"
               "      events_when_stopped: ramp_callout_done\n      ducking:")


def tone(secs, freqs, rate=22050):
    """A WAV file (bytes) of sine tones, stepping through `freqs` over `secs` seconds."""
    import io, math, struct, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(secs * rate)
        frames = bytearray()
        for i in range(n):
            f = freqs[int(i / n * len(freqs))]
            env = min(1.0, i / 200, (n - i) / 200)
            frames += struct.pack("<h", int(32767 * 0.4 * env * math.sin(2 * math.pi * f * i / rate)))
        w.writeframes(bytes(frames))
    return buf.getvalue()


def sound_list(text):
    """{probe number: (sorted ['bus sound', ...], {bus: volume})} from DOC_SOUND / DOC_BUS lines."""
    shots = {int(n): ([], {}) for n in re.findall(r"^DOC_DONE (\d+)", text, re.M)}
    for n, bus, name in re.findall(r"^DOC_SOUND (\d+) (\S+) (\S+?)\r?$", text, re.M):
        shots.setdefault(int(n), ([], {}))[0].append("%s %s" % (bus, name))
    for n, bus, vol in re.findall(r"^DOC_BUS (\d+) (\S+) ([\d.]+)\r?$", text, re.M):
        shots.setdefault(int(n), ([], {}))[1][bus] = float(vol)
    return {n: (sorted(s), v) for n, (s, v) in shots.items()}


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestSound(unittest.TestCase):
    """gmc/sound.md: the page's machine, buses and gmc.cfg with generated tones; GMC reports what each bus plays."""

    runs = {}

    def files(self, change=None):
        files = page_files(INSTALL_PAGE)
        files["slides/base.tscn"] = page_files(SLIDES_PAGE)["slides/base.tscn"]
        page = page_files(SOUND_PAGE)
        self.assertEqual({"default_bus_layout.tres", "gmc.cfg", "config/config.yaml", "modes/base/config/base.yaml",
                          "modes/hurry/config/hurry.yaml"}, set(page))
        files.update(page)
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        files.update({
            "sounds/music.wav": tone(3.0, [220, 277, 330, 277]),
            "sounds/callout_ramp.wav": tone(1.0, [660, 880]),
            "sounds/callout_target.wav": tone(1.0, [880, 660]),
            "sounds/jackpot.wav": tone(0.5, [990]),
            "sounds/tick.wav": tone(0.5, [1200, 0]),
        })
        files = with_probe(files, SOUND_SCRIPT)
        if change:
            change(files)
        return files

    def run_variant(self, name, change=None):
        """Run a variant once per test run; later tests reuse its results."""
        if name not in self.runs:
            run = BothRun(build_project(self.files(change)), platform="-X")
            try:
                self.assertTrue(run.wait_for("DOC_DONE 7", 60), run.text()[-3000:])
                time.sleep(1.5)
                text = run.text()
                self.runs[name] = (sound_list(text), run.events(), text)
            finally:
                run.stop()
        return self.runs[name]

    @staticmethod
    def base(files, old, new):
        """Replace the first occurrence of `old` in the base mode config (the ramp callout comes first)."""
        key = "modes/base/config/base.yaml"
        assert old in files[key], old
        files[key] = files[key].replace(old, new, 1)

    def test_page_machine(self):
        sounds, events, text = self.run_variant("page")
        self.assertNotIn("SCRIPT ERROR", text)
        self.assertEqual((["music music"], {"Master": 0.5, "music": 1.0, "sfx": 1.0, "voice": 1.0}), sounds[1])
        self.assertEqual(["music music", "voice callout_ramp"], sounds[2][0])
        self.assertAlmostEqual(0.5, sounds[2][1]["music"], delta=0.02)          # ducked
        self.assertEqual(["music music", "sfx jackpot", "voice callout_ramp"], sounds[3][0])  # target queued
        self.assertEqual(["music music", "voice callout_target"], sounds[4][0])  # queued callout played next
        self.assertAlmostEqual(0.5, sounds[4][1]["music"], delta=0.02)
        self.assertEqual((["music music"], 1.0), (sounds[5][0], sounds[5][1]["music"]))  # released
        self.assertIn("sfx tick", sounds[6][0])
        self.assertNotIn("sfx tick", sounds[7][0])                               # stopped from base

    def without_stop(self, files):
        self.base(files, HURRY_STOP, "")

    def test_mode_sound_left_playing(self):
        """Documented GMC bug: a mode with only sound_player leaves its sounds playing when it stops."""
        sounds, events, text = self.run_variant("without_stop", self.without_stop)
        self.assertIn("sfx tick", sounds[7][0])

    @unittest.expectedFailure
    def test_mode_sound_stopped_with_mode(self):
        """What should happen (fails until GMC handles sounds_clear)."""
        sounds, events, text = self.run_variant("without_stop", self.without_stop)
        self.assertNotIn("sfx tick", sounds[7][0])

    def stop_looping(self, files):
        self.base(files, HURRY_STOP, HURRY_STOP.replace("action: stop", "action: stop_looping"))

    def test_stop_looping_plays_again(self):
        """Documented GMC bug: stop_looping starts a second copy."""
        sounds, events, text = self.run_variant("stop_looping", self.stop_looping)
        self.assertEqual(2, sounds[7][0].count("sfx tick"))

    @unittest.expectedFailure
    def test_stop_looping_does_not_add_a_copy(self):
        """What should happen (fails until GMC accepts stop_looping)."""
        sounds, events, text = self.run_variant("stop_looping", self.stop_looping)
        self.assertLessEqual(sounds[7][0].count("sfx tick"), 1)

    def test_events_alone(self):
        def change(files):
            self.base(files, *RAMP_EVENTS)
            key = "modes/base/config/base.yaml"
            start = files[key].index("    callout_target:")
            files[key] = files[key][:start] + files[key][files[key].index("    jackpot: {}"):]
        sounds, events, text = self.run_variant("events_alone", change)
        self.assertNotIn("SCRIPT ERROR", text)
        first_ramp = [t for t, n, a in events if n == "s_ramp_active"][0]
        started = [t for t, n, a in events if n == "ramp_callout_started" and t >= first_ramp]
        done = [t for t, n, a in events if n == "ramp_callout_done" and t < first_ramp + 3]
        self.assertEqual(1, len(done))
        self.assertAlmostEqual(1.0, done[0] - started[0], delta=0.2)

    def events_queued(self, files):
        self.base(files, *RAMP_EVENTS)

    def test_events_when_stopped_with_queue(self):
        """Documented GMC bug: events_when_stopped is posted again when the next sound on the channel ends."""
        sounds, events, text = self.run_variant("events_queued", self.events_queued)
        first_ramp = [t for t, n, a in events if n == "s_ramp_active"][0]
        done = [n for t, n, a in events if n == "ramp_callout_done" and t < first_ramp + 3]
        self.assertEqual(2, len(done))
        self.assertIn("Cannot convert argument 1 from Nil to Callable", text)

    @unittest.expectedFailure
    def test_events_when_stopped_once(self):
        """What should happen (fails until GMCChannel._trigger_events keeps its own callable)."""
        sounds, events, text = self.run_variant("events_queued", self.events_queued)
        first_ramp = [t for t, n, a in events if n == "s_ramp_active"][0]
        self.assertEqual(1, len([n for t, n, a in events if n == "ramp_callout_done" and t < first_ramp + 3]))

    def test_events_when_stopped_on_both_callouts(self):
        """Documented GMC bug: with events_when_stopped on both queued callouts, the second one's event is lost."""
        def change(files):
            key = "modes/base/config/base.yaml"
            files[key] = files[key].replace(*RAMP_EVENTS)   # both callouts
        sounds, events, text = self.run_variant("events_both", change)
        first_ramp = [t for t, n, a in events if n == "s_ramp_active"][0]
        done = [t - first_ramp for t, n, a in events if n == "ramp_callout_done" and t < first_ramp + 3]
        self.assertEqual(1, len(done))
        self.assertAlmostEqual(1.0, done[0], delta=0.2)

    def test_no_default_bus(self):
        def change(files):
            files["gmc.cfg"] = files["gmc.cfg"].replace(', "default": true', "")
        sounds, events, text = self.run_variant("no_default", change)
        self.assertIn("Sound played without bus param and no default bus is specified", text)
        self.assertNotIn("sfx jackpot", sounds[3][0])


CAROUSEL_PAGE = "gmc/carousel.md"

CAROUSEL_SCRIPT = """
event_player:
  s_doc_shot_active: doc_shot

switch_player:
  start_event: mode_attract_started
  steps:
    - {time: 1s, switch: s_start, action: hit}
    - {time: 1500ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_right_flipper, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_right_flipper, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_right_flipper, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_left_flipper, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_left_flipper, action: hit}
    - {time: 100ms, switch: s_left_flipper, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_launch, action: hit}
    - {time: 500ms, switch: s_doc_shot, action: hit}
"""


def carousel_shown(text):
    """{probe number: {carousel name: shown child names}} from DOC_CAROUSEL lines (missing = no carousel on screen)."""
    shots = {int(n): {} for n in re.findall(r"^DOC_DONE (\d+)", text, re.M)}
    for n, name, shown in re.findall(r"^DOC_CAROUSEL (\d+) (\S+)=(.*?)\r?$", text, re.M):
        shots.setdefault(int(n), {})[name] = shown
    return shots


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestCarousel(unittest.TestCase):
    """gmc/carousel.md: the page's machine and award chooser slide, with the shown carousel child read back from GMC."""

    def files(self, change=None):
        files = page_files(INSTALL_PAGE)
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        files["slides/base.tscn"] = page_files(VARIABLES_PAGE)["slides/base.tscn"]
        page = page_files(CAROUSEL_PAGE)
        self.assertEqual({"modes/award_select/config/award_select.yaml", "config/config.yaml",
                          "modes/base/config/base.yaml", "slides/award_select.tscn"}, set(page))
        files.update(page)
        files = with_probe(files, CAROUSEL_SCRIPT)
        if change:
            change(files)
        return files

    def run_game(self, files):
        run = BothRun(build_project(files), platform="-X")
        try:
            self.assertTrue(run.wait_for("DOC_DONE 7", 60), run.text()[-3000:])
            time.sleep(1)
            text = run.text()
            self.assertNotIn("SCRIPT ERROR", text)
            return carousel_shown(text), label_texts(text), run.events(), text
        finally:
            run.stop()

    def test_page_machine(self):
        shown, labels, events, text = self.run_game(self.files())
        self.assertEqual(["extra_points", "light_lock", "double_scoring", "extra_points", "double_scoring",
                          "extra_points"], [shown[n]["award_select"] for n in range(1, 7)])
        self.assertEqual({}, shown[7])                      # chosen: the mode and its slide are gone
        self.assertEqual("5,000", labels[7]["Score"])
        highlighted = [(re.search(r"'item': '(\w+)'", a).group(1), re.search(r"'direction': (\S+?)[,}]", a).group(1))
                       for t, n, a in events if n == "carousel_item_highlighted"]
        self.assertEqual([("extra_points", "None"), ("light_lock", "'forwards'"), ("double_scoring", "'forwards'"),
                          ("extra_points", "'forwards'"), ("double_scoring", "'backwards'"),
                          ("light_lock", "'backwards'"), ("extra_points", "'backwards'")], highlighted)
        selected = [a for t, n, a in events if n == "carousel_item_selected"]
        self.assertEqual(1, len(selected))
        self.assertIn("'item': 'extra_points'", selected[0])

    def test_no_wrap_and_misnamed_child(self):
        def change(files):
            files["modes/award_select/config/award_select.yaml"] = files[
                "modes/award_select/config/award_select.yaml"].replace(
                "  select_item_events: s_launch_active\n", "  select_item_events: s_launch_active\n  wrap_items: false\n")
            files["slides/award_select.tscn"] = files["slides/award_select.tscn"].replace(
                '[node name="double_scoring" type="Label"', '[node name="doublescoring" type="Label"')
        shown, labels, events, text = self.run_game(self.files(change))
        items = [re.search(r"'item': '(\w+)'", a).group(1) for t, n, a in events if n == "carousel_item_highlighted"]
        self.assertEqual(["extra_points", "light_lock", "double_scoring", "light_lock", "extra_points"], items)
        self.assertIn("Carousel could not find a child named 'double_scoring' to highlight.", text)
        self.assertEqual("", shown[3]["award_select"])      # nothing shown for the misnamed item


EVENTS_PAGE = "gmc/events.md"

EVENTS_SCRIPT = """
event_player:
  s_doc_shot_active: doc_shot
  s_doc_key_active: doc_key

switch_player:
  start_event: mode_attract_started
  steps:
    - {time: 1s, switch: s_start, action: hit}
    - {time: 1500ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_doc_key, action: hit}
    - {time: 600ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_ramp, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_target, action: hit}
    - {time: 300ms, switch: s_doc_shot, action: hit}
    - {time: 1200ms, switch: s_doc_shot, action: hit}
    - {time: 2500ms, switch: s_doc_shot, action: hit}
"""


def plain_labels(text):
    """{probe number: {label name: text}} from the probe's DOC_LABEL lines (labels that aren't MPFVariables)."""
    shots = {}
    for n, name, value in re.findall(r"^DOC_LABEL (\d+) (\w+)=(.*?)\r?$", text, re.M):
        shots.setdefault(int(n), {})[name] = value
    return shots


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestEvents(unittest.TestCase):
    """gmc/events.md: the page's machine, scripts and slides; a key press is simulated in Godot."""

    def test_page_machine(self):
        files = page_files(INSTALL_PAGE)
        page = page_files(EVENTS_PAGE)
        self.assertEqual({"slides/jackpot_label.gd", "slides/mystery.gd", "gmc.cfg", "config/config.yaml",
                          "modes/base/config/base.yaml", "slides/done_label.gd", "slides/base.tscn",
                          "slides/mystery.tscn"}, set(page))
        files.update(page)
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        files["config/config.yaml"] = files["config/config.yaml"].replace(
            "switches:\n", "switches:\n  s_doc_key:\n    number:\n", 1)
        files = with_probe(files, EVENTS_SCRIPT)
        run = BothRun(build_project(files), platform="-X")
        try:
            self.assertTrue(run.wait_for("DOC_DONE 6", 60), run.text()[-3000:])
            text = run.text()
            events = run.events()
        finally:
            run.stop()
        self.assertNotIn("SCRIPT ERROR", text)
        labels, variables = plain_labels(text), label_texts(text)
        names = [n for t, n, a in events]
        # keyboard: L -> s_lock -> jackpot_lit with its argument -> the MPFEventHandler label
        self.assertLess(names.index("s_lock_active"), names.index("jackpot_lit"))
        self.assertEqual("JACKPOT LIT: 25000", labels[2]["Jackpot"])
        self.assertEqual("MYSTERY", labels[3]["Result"])
        self.assertEqual("SPINNING...", labels[4]["Result"])   # action: method
        self.assertEqual("MYSTERY: 5000", labels[5]["Result"])
        # Godot -> MPF: mystery_done with its argument, one second after the target, scored at once
        target = [t for t, n, a in events if n == "s_target_active"][0]
        done = [(t, a) for t, n, a in events if n == "mystery_done"]
        self.assertEqual(1, len(done))
        self.assertIn("'points': 5000", done[0][1])
        self.assertIn("'_from_bcp': True", done[0][1])
        self.assertAlmostEqual(1.0, done[0][0] - target, delta=0.2)
        self.assertEqual("5,000", variables[6]["Score"])
        # Godot's own handler for the event it sent ran once
        self.assertEqual("MYSTERY DONE x1: 5000", labels[6]["Done"])


DISPLAYS_PAGE = "gmc/displays.md"

DISPLAYS_SCRIPT = """
event_player:
  s_doc_shot_active: doc_shot

switch_player:
  start_event: mode_attract_started
  steps:
    - {time: 1s, switch: s_doc_shot, action: hit}
    - {time: 100ms, switch: s_start, action: hit}
    - {time: 1500ms, switch: s_doc_shot, action: hit}
"""


def probe_values(text, kind):
    """{probe number: {name: value}} from the probe's DOC_<kind> lines."""
    shots = {}
    for n, name, value in re.findall(r"^DOC_%s (\d+) (\w+)=(.*?)\r?$" % kind, text, re.M):
        shots.setdefault(int(n), {})[name] = value
    return shots


@unittest.skipUnless(GODOT and GMC, "set MPF_DOCS_GODOT and MPF_DOCS_GMC to run the GMC checks")
class TestDisplays(unittest.TestCase):
    """gmc/displays.md: the page's window with two displays, the filter, and spawn_mpf."""

    def files(self, change=None):
        files = page_files(INSTALL_PAGE)
        files["gmc.cfg"] = with_godot_path(files["gmc.cfg"])
        slides = page_files(SLIDES_PAGE)
        files["slides/base.tscn"] = slides["slides/base.tscn"]
        files["config/config.yaml"] = slides["config/config.yaml"].replace("  - base\n  - skillshot\n", "  - base\n")
        page = page_files(DISPLAYS_PAGE)
        self.assertEqual({"project.godot", "window.tscn", "slides/info_bar.tscn", "modes/base/config/base.yaml"},
                         set(page))
        files.update(page)
        files = with_probe(files, DISPLAYS_SCRIPT)
        if change:
            change(files)
        return files

    def run_both(self, files):
        run = BothRun(build_project(files), platform="-X")
        try:
            self.assertTrue(run.wait_for("DOC_DONE 2", 60), run.text()[-3000:])
            text = run.text()
        finally:
            run.stop()
        self.assertNotIn("SCRIPT ERROR", text)
        return text

    def test_two_displays(self):
        text = self.run_both(self.files())
        displays = probe_values(text, "DISPLAY")
        self.assertEqual({"main": "attract", "info": ""}, displays[1])
        self.assertEqual({"main": "base", "info": "info_bar"}, displays[2])
        self.assertEqual("INFO DISPLAY: BALL 1", label_texts(text)[2]["Ball"])
        self.assertEqual({"pixelate": "false"}, probe_values(text, "FILTER")[2])   # no [filter] section

    def test_pixelate_filter(self):
        def change(files):
            files["gmc.cfg"] += '\n[filter]\nfilter="pixelate"\ncolumns=96.0\nrows=72.0\n'
        text = self.run_both(self.files(change))
        self.assertEqual({"pixelate": "true"}, probe_values(text, "FILTER")[2])

    def test_spawn_mpf(self):
        def change(files):
            files["gmc.cfg"] += ('\n[mpf]\nspawn_mpf=true\nexecutable_path="%s"\nmpf_args="-X"\n'
                                 % MPF_CMD.replace("\\", "/"))
        path = build_project(self.files(change))
        godot_log = godot_user_dir(path.name) / "logs" / "godot.log"
        godot = subprocess.Popen([GODOT, "--path", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            end = time.time() + 60
            text = ""
            while time.time() < end and "DOC_DONE 2" not in text:
                time.sleep(.5)
                text = godot_log.read_text(encoding="utf-8", errors="replace") if godot_log.exists() else ""
            self.assertIn("DOC_DONE 2", text, text[-3000:])
            children = psutil.Process(godot.pid).children(recursive=True)
        finally:
            godot.kill()
        self.assertNotIn("SCRIPT ERROR", text)
        self.assertIn("Spawning MPF process...", text)
        executing = re.search(r"Executing (.*?) with args \[(.*?)\]", text)
        self.assertEqual(MPF_CMD.replace("\\", "/").lower(), executing.group(1).lower())
        args = executing.group(2).split(", ")
        self.assertEqual(["-t", "-X", "-l"], args[1:4])
        self.assertIn("Client connected", text)
        self.assertEqual({"main": "base", "info": "info_bar"}, probe_values(text, "DISPLAY")[2])
        if sys.platform == "win32":
            self.assertIn("Unknown process status 'FIND: Parameter format not correct'", text)
        # MPF goes when GMC does
        self.assertTrue(children)
        gone, alive = psutil.wait_procs(children, timeout=15)
        self.assertEqual([], alive)


def tearDownModule():
    for path in CREATED:
        shutil.rmtree(godot_user_dir(path.name), ignore_errors=True)
        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
