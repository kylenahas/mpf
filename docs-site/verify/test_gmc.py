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

func _shot(_message = null) -> void:
\tcount += 1
\tawait get_tree().process_frame
\tawait get_tree().process_frame
\tfor node in get_tree().root.find_children("*", "Label", true, false):
\t\tif node is MPFVariable and node.is_visible_in_tree():
\t\t\tprint("DOC_TEXT %d %s=%s" % [count, node.name, node.text])
\tfor node in get_tree().root.find_children("*", "Control", true, false):
\t\tif node is MPFWidget:
\t\t\tprint("DOC_WIDGET %d %s on %s" % [count, node.key, node.get_parent().get_parent().name])
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


def tearDownModule():
    for path in CREATED:
        shutil.rmtree(godot_user_dir(path.name), ignore_errors=True)
        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
