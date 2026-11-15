"""Run the configs from the guide pages on MPF and check the behaviour the pages describe.

Each test builds a machine folder the way a reader would (`mpf init`, then the page's complete config), so the page and
the test cannot drift apart: the config is read from the page itself.

Run from the repository root:
  venv/Scripts/python -I -m unittest discover -s docs-site/verify -v
"""
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from ruamel.yaml import YAML

from mpf.commands.init import Command as InitCommand
from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf.tests.MpfGameTestCase import MpfGameTestCase
from mpf.tests.MpfTestCase import expect_startup_error

CONTENT = Path(__file__).resolve().parent.parent / "content"
FENCE = re.compile(r"^```yaml\s*\n(.*?)^```", re.M | re.S)


def yaml_blocks(page):
    return FENCE.findall((CONTENT / page).read_text(encoding="utf-8"))


def full_config(page):
    """The block labelled `config/config.yaml` on the page, else the last block that is a whole config file."""
    labelled = page_files(page).get("config/config.yaml")
    if labelled:
        return labelled
    return [b for b in yaml_blocks(page) if b.startswith("#config_version")][-1]


FILE_BLOCK = re.compile(r"^`((?:modes|config|shows)/[\w/.-]+\.(?:yaml|py))`:[ \t]*\n\s*\n```(?:yaml|python)\s*\n(.*?)^```",
                        re.M | re.S)


def page_files(page):
    """Blocks labelled by a line holding only their file path, e.g. `modes/base/config/base.yaml`: then the block."""
    return dict(FILE_BLOCK.findall((CONTENT / page).read_text(encoding="utf-8")))


def make_machine(text, replace_devices=None, files=None):
    """`mpf init` a temp folder and write `text` as config/config.yaml.

    replace_devices: a YAML snippet like `ball_devices: {bd_plunger: {...}}`; each device in it replaces the device of the
    same name in the config (used for the variants shown on a page).
    files: {relative path: text} written after `mpf init`, e.g. mode configs from page_files().
    """
    path = tempfile.mkdtemp(prefix="mpf_docs_")
    InitCommand(["init"], path)
    for rel, body in (files or {}).items():
        Path(path, rel).parent.mkdir(parents=True, exist_ok=True)
        Path(path, rel).write_text(body, encoding="utf-8")
    if replace_devices:
        config = json.loads(json.dumps(YamlInterface.process(text)))
        for section, devices in YamlInterface.process(replace_devices).items():
            for name, settings in devices.items():
                config[section][name] = json.loads(json.dumps(settings))
        out = Path(path, "config", "config.yaml").open("w", encoding="utf-8")
        out.write("#config_version=6\n")
        YAML(typ="safe", pure=True).dump(config, out)
        out.close()
    else:
        Path(path, "config", "config.yaml").write_text(text, encoding="utf-8")
    return path


class GuideMachine(MpfGameTestCase):
    """Base: a machine folder built from a page. Subclasses set `machine_dir` in setUpClass."""

    machine_dir = None

    @classmethod
    def tearDownClass(cls):
        if cls.machine_dir:
            shutil.rmtree(cls.machine_dir, ignore_errors=True)

    def get_config_file(self):
        return "config.yaml"

    def get_machine_path(self):
        return self.machine_dir

    def get_absolute_machine_path(self):
        return self.machine_dir

    def get_platform(self):
        return "smart_virtual"

    def get_enable_plugins(self):
        return False

    def get_use_bcp(self):
        return False

    def bd(self, name):
        return self.machine.ball_devices[name]


class TestFirstMachine(GuideMachine):
    """get-started/first-machine.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config("get-started/first-machine.md"))

    def test_three_ball_game(self):
        self.advance_time_and_run(1)
        self.assertModeRunning("attract")
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)
        self.start_game()
        self.advance_time_and_run(1)
        self.assertModeRunning("base")
        # no playfield switch: the ball counts as on the playfield after the 10 s default eject timeout
        self.advance_time_and_run(11)
        self.assertEqual(1, self.machine.playfield.balls)
        for ball in (2, 3):
            self.drain_one_ball()
            self.advance_time_and_run(12)
            self.assertBallNumber(ball)
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertGameIsNotRunning()
        self.assertModeRunning("attract")


class TestBallDevices(GuideMachine):
    """build/ball-devices.md: the complete config at the end of the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config("build/ball-devices.md"))

    def test_page_walkthrough(self):
        self.mock_event("ball_search_phase_1")
        self.mock_event("balldevice_bd_saucer_ball_eject_success")
        self.advance_time_and_run(1)
        # 1. counts at boot
        self.assertEqual(3, self.bd("bd_trough").balls)
        self.assertEqual(0, self.bd("bd_plunger").balls)
        # 2. game start: one ball to the plunger lane
        self.start_game()
        self.advance_time_and_run(5)
        self.assertEqual(2, self.bd("bd_trough").balls)
        self.assertEqual(1, self.bd("bd_plunger").balls)
        # 3. the ball waits for the launch button
        self.advance_time_and_run(30)
        self.assertEqual(1, self.bd("bd_plunger").balls)
        self.hit_and_release_switch("s_launch")
        self.advance_time_and_run(1)
        self.assertEqual(0, self.bd("bd_plunger").balls)
        # 4. a playfield switch confirms the ball
        self.hit_and_release_switch("s_left_sling")
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.playfield.balls)
        # 5. the saucer kicks an unexpected ball back out
        self.machine.switch_controller.process_switch("s_saucer", 1)
        self.advance_time_and_run(3)
        self.assertEventCalled("balldevice_bd_saucer_ball_eject_success")
        self.assertEqual(0, self.bd("bd_saucer").balls)
        self.assertEqual(1, self.machine.playfield.balls)
        # 6. ball search after 15 s without a switch hit
        self.advance_time_and_run(10)
        self.assertEventNotCalled("ball_search_phase_1")
        self.advance_time_and_run(6)
        self.assertEventCalled("ball_search_phase_1")
        # 7. drain ends ball 1 and serves ball 2 to the lane
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertBallNumber(2)
        self.assertEqual(1, self.bd("bd_plunger").balls)


def plunger_variant(heading):
    """The ball_devices snippet under a ### heading of the ball devices page."""
    text = (CONTENT / "build/ball-devices.md").read_text(encoding="utf-8")
    section = text.split("### " + heading, 1)[1].split("\n#", 1)[0]
    return [b for b in FENCE.findall(section) if b.lstrip().startswith("ball_devices:")][0]


class TestManualPlunger(GuideMachine):
    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config("build/ball-devices.md"), plunger_variant("Manual plunger"))

    def test_waits_for_player(self):
        self.assertTrue(self.bd("bd_plunger").config["mechanical_eject"])
        self.assertIsNone(self.bd("bd_plunger").ejector)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(35)
        self.assertEqual(1, self.bd("bd_plunger").balls)
        self.machine.switch_controller.process_switch("s_plunger_lane", 0)  # the player pulls the plunger
        self.advance_time_and_run(1)
        self.hit_and_release_switch("s_left_sling")
        self.advance_time_and_run(1)
        self.assertEqual(0, self.bd("bd_plunger").balls)
        self.assertEqual(1, self.machine.playfield.balls)


class TestAutoLauncher(GuideMachine):
    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config("build/ball-devices.md"), plunger_variant("Auto-launcher"))

    def test_fires_without_button(self):
        self.assertFalse(self.bd("bd_plunger").config["player_controlled_eject_event"])
        self.advance_time_and_run(1)
        self.start_game()
        # no button and no playfield switch: on the playfield once the 3 s eject timeout passes
        self.advance_time_and_run(5)
        self.assertEqual(0, self.bd("bd_plunger").balls)
        self.assertEqual(1, self.machine.playfield.balls)


class TestSwitchesAndCoils(GuideMachine):
    """build/switches-and-coils.md: the complete config at the end of the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config("build/switches-and-coils.md"))

    def get_platform(self):
        return "virtual"

    def driver(self, name):
        return self.machine.coils[name].hw_driver.state

    def test_page_walkthrough(self):
        for event in ("knock", "s_action_button_active", "spinner_spin", "sw_flipper_button", "magnet_on",
                      "magnet_off"):
            self.mock_event(event)
        self.advance_time_and_run(1)
        # 1. NC switch reads inactive at boot
        self.assertSwitchState("s_coin_door", 0)
        # 2. button -> knock -> knocker pulses with default_pulse_ms
        self.hit_and_release_switch("s_action_button")
        self.advance_time_and_run(.1)
        self.assertEventCalled("s_action_button_active")
        self.assertEventCalled("knock")
        self.assertEqual("pulsed_25", self.driver("c_knocker"))
        # 3. ignore_window_ms: five hits in 100 ms post one event, a later hit posts again
        for _ in range(5):
            self.hit_and_release_switch("s_spinner")
            self.advance_time_and_run(.02)
        self.assertEventCalled("spinner_spin", times=1)
        self.advance_time_and_run(1)
        self.hit_and_release_switch("s_spinner")
        self.advance_time_and_run(.1)
        self.assertEventCalled("spinner_spin", times=2)
        # 4. timed switch: tag event at once, magnet_on after 2 s
        self.hit_switch_and_run("s_left_flipper", 1)
        self.assertEventCalled("sw_flipper_button")
        self.assertEventNotCalled("magnet_on")
        self.advance_time_and_run(1.1)
        self.assertEventCalled("magnet_on")
        self.assertEqual("enabled", self.driver("c_magnet"))
        # 5. max_hold_duration turns the magnet off while the button is still held
        self.advance_time_and_run(3)
        self.assertEqual("disabled", self.driver("c_magnet"))
        # 6. release posts magnet_off
        self.assertEventNotCalled("magnet_off")
        self.release_switch_and_run("s_left_flipper", .1)
        self.assertEventCalled("magnet_off")


class TestFlippersAndAutofire(GuideMachine):
    """build/flippers-and-autofire.md: the complete config at the end of the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config("build/flippers-and-autofire.md"))

    def rules(self):
        switches = {s.hw_switch: n for n, s in self.machine.switches.items()}
        coils = {c.hw_driver: n for n, c in self.machine.coils.items()}
        return {(switches[s], coils[d]): r for (s, d), r in self.machine.default_platform.rules.items()}

    def test_page_walkthrough(self):
        self.advance_time_and_run(1)
        # 1. no rules in attract
        self.assertEqual({}, self.rules())
        # 2. rules written at ball start
        self.start_game()
        self.advance_time_and_run(1)
        self.assertEqual({
            ("s_left_flipper", "c_left_flipper"): "pulse_on_hit_and_enable_and_release",
            ("s_right_flipper", "c_right_flipper_hold"): "pulse_on_hit_and_enable_and_release",
            ("s_right_flipper", "c_right_flipper_main"): "pulse_on_hit_and_release_and_disable",
            ("s_right_flipper_eos", "c_right_flipper_main"): "pulse_on_hit_and_release_and_disable",
            ("s_left_sling", "c_left_sling"): "pulse_on_hit",
            ("s_pop", "c_pop"): "pulse_on_hit",
            ("s_left_outlane", "c_kickback"): "pulse_on_hit",
        }, self.rules())
        # 3. kickback fires once, disables itself, comes back on light_kickback
        self.mock_event("kickback_left_kickback_fired")
        self.hit_and_release_switch("s_left_outlane")
        self.advance_time_and_run(.1)
        self.assertEventCalled("kickback_left_kickback_fired")
        self.assertNotIn(("s_left_outlane", "c_kickback"), self.rules())
        self.post_event("light_kickback")
        self.advance_time_and_run(.1)
        self.assertIn(("s_left_outlane", "c_kickback"), self.rules())

    def test_timeout_same_instant(self):
        """Hits at one instant do trip the timeout (what MPF's own test checks)."""
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        for _ in range(10):
            self.hit_and_release_switch("s_pop")
            self.machine_run()
        self.assertNotIn(("s_pop", "c_pop"), self.rules())
        self.advance_time_and_run(2.1)
        self.assertIn(("s_pop", "c_pop"), self.rules())

    @unittest.expectedFailure
    def test_timeout_real_spacing(self):
        """The warning on the page: 10 hits 50 ms apart (inside timeout_watch_time: 1s) should disable the pop bumper.

        Fails on MPF 0.82.0.dev0 (timeout_watch_time is divided by 1000 twice). If this starts passing, MPF was fixed:
        remove the expectedFailure and the warning on the page.
        """
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        for _ in range(10):
            self.hit_and_release_switch("s_pop")
            self.advance_time_and_run(.05)
        self.assertNotIn(("s_pop", "c_pop"), self.rules())


class TestSingleWoundFlipperWithoutHoldPower(GuideMachine):
    """build/flippers-and-autofire.md: a single-wound flipper coil with no hold power stops at ball start."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config("build/flippers-and-autofire.md"),
                                       "coils:\n  c_left_flipper:\n    number:\n    default_pulse_ms: 30\n")

    def test_error(self):
        self.advance_time_and_run(1)
        with self.assertRaisesRegex(Exception, "hold_power 0.0"):
            self.start_game()
            self.advance_time_and_run(1)


MODES_PAGE = "build/modes.md"


def modes_machine(extra=None):
    files = {k: v for k, v in page_files(MODES_PAGE).items() if k.startswith("modes/")}
    files.update(extra or {})
    return make_machine(full_config(MODES_PAGE), files=files)


class TestModes(GuideMachine):
    """build/modes.md: machine config plus the four mode files, all read from the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = modes_machine()

    def running(self):
        return {m.name: m.priority for m in self.machine.mode_controller.active_modes}

    def test_page_walkthrough(self):
        self.assertEqual(4, len([k for k in page_files(MODES_PAGE) if k.startswith("modes/")]))
        self.mock_event("skillshot_made")
        self.mock_event("skillshot_lit")
        self.advance_time_and_run(1)
        self.assertEqual({"attract": 10}, self.running())
        # game mode outside a game is ignored
        self.post_event("start_hurry_up")
        self.advance_time_and_run(.1)
        self.assertEqual({"attract": 10}, self.running())
        # non-game mode runs in attract
        self.post_event("start_lamp_test")
        self.advance_time_and_run(.1)
        self.assertEqual({"attract": 10, "lamp_test": 100}, self.running())
        self.post_event("stop_lamp_test")
        self.advance_time_and_run(.1)
        # skill shot's event_player does not exist outside the mode
        self.hit_and_release_switch("s_upper_lane")
        self.advance_time_and_run(.1)
        self.assertEventNotCalled("skillshot_made")
        # ball 1
        self.start_game()
        self.advance_time_and_run(2)
        self.assertEqual({"game": 20, "base": 100, "skillshot": 200}, self.running())
        self.assertEventCalled("skillshot_lit")
        self.hit_and_release_switch("s_upper_lane")
        self.advance_time_and_run(.1)
        self.assertEventCalled("skillshot_made", times=1)
        self.assertEqual({"game": 20, "base": 100}, self.running())
        self.hit_and_release_switch("s_upper_lane")
        self.advance_time_and_run(.1)
        self.assertEventCalled("skillshot_made", times=1)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(.1)
        self.assertEqual({"game": 20, "base": 100, "hurry_up": 300}, self.running())
        # ball 2: hurry_up restarted
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.assertEqual({"game": 20, "base": 100, "skillshot": 200, "hurry_up": 300}, self.running())
        self.hit_and_release_switch("s_left_sling")
        self.advance_time_and_run(.1)
        self.assertNotIn("skillshot", self.running())
        self.post_event("hurry_up_collected")
        self.advance_time_and_run(.1)
        self.assertEqual({"game": 20, "base": 100}, self.running())
        # ball 3: collected hurry_up does not come back
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(3)
        self.assertEqual({"game": 20, "base": 100, "skillshot": 200}, self.running())
        # any other playfield_active switch ends the skill shot too
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(.1)
        self.assertNotIn("skillshot", self.running())
        self.hit_and_release_switch("s_upper_lane")
        self.advance_time_and_run(.1)
        self.assertEventCalled("skillshot_made", times=1)


class TestModeErrors(unittest.TestCase):
    """build/modes.md: the two startup errors quoted on the page."""

    def boot(self, machine_dir):
        class Boot(GuideMachine):
            def runTest(self):
                pass
        Boot.machine_dir = machine_dir
        test = Boot("runTest")
        try:
            test.setUp()
        finally:
            try:
                test.tearDown()
            except Exception:  # noqa: BLE001  (machine may not have started)
                pass
            shutil.rmtree(machine_dir, ignore_errors=True)

    def test_missing_mode_folder(self):
        path = modes_machine()
        cfg = Path(path, "config", "config.yaml")
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("  - lamp_test\n", "  - lamp_test\n  - bonus_round\n"),
                       encoding="utf-8")
        with self.assertRaisesRegex(Exception, "No config found for mode 'bonus_round'"):
            self.boot(path)

    def test_game_mode_must_stop_on_ball_end(self):
        path = modes_machine({"modes/hurry_up/config/hurry_up.yaml":
                              "#config_version=6\nmode:\n  start_events: start_hurry_up\n  stop_on_ball_end: false\n"})
        with self.assertRaisesRegex(Exception, "All game modes need to stop at ball end"):
            self.boot(path)


EVENTS_PAGE = "build/events.md"


class TestEvents(GuideMachine):
    """build/events.md: the complete config (base mode from `mpf init`)."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config(EVENTS_PAGE))

    def test_page_walkthrough(self):
        order = []
        self.machine.events.add_handler("target_first", lambda **kwargs: order.append("first"))
        self.machine.events.add_handler("target_second", lambda **kwargs: order.append("second"))
        for event in ("target_hit", "big_award", "lane_done", "second_ball_started", "ball_report"):
            self.mock_event(event)
        self.advance_time_and_run(1)
        # 1. attract: priority order, condition on current_player is false
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(.1)
        self.assertEventCalled("target_hit")
        self.assertEqual(["first", "second"], order)
        self.assertEventNotCalled("big_award")
        # 2. ball 1
        self.start_game()
        self.advance_time_and_run(1)
        self.assertEventCalledWith("ball_report", which=1, priority=0)
        self.assertEventNotCalled("second_ball_started")
        # 3. target on ball 1
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(.1)
        self.assertEventNotCalled("big_award")
        # 4. delayed post
        self.hit_and_release_switch("s_lane")
        self.advance_time_and_run(1.5)
        self.assertEventNotCalled("lane_done")
        self.advance_time_and_run(1)
        self.assertEventCalled("lane_done")
        # 5. ball 2
        self.advance_time_and_run(10)  # ball reaches the playfield (eject timeout) so the drain ends the ball
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.assertEventCalled("second_ball_started")
        self.assertEventCalledWith("ball_report", which=2, priority=0)
        # 6. big_award on ball 2, knocker 500 ms later
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(.1)
        self.assertEventCalled("big_award")
        self.assertEqual("disabled", self.machine.coils["c_knocker"].hw_driver.state)
        self.advance_time_and_run(.5)
        self.assertTrue(self.machine.coils["c_knocker"].hw_driver.state.startswith("pulsed_"))


def merge_config(text, additions):
    """Merge a YAML snippet into a whole config: lists are extended, named entries added or replaced."""
    config = json.loads(json.dumps(YamlInterface.process(text)))
    for section, value in json.loads(json.dumps(YamlInterface.process(additions))).items():
        if isinstance(value, list):
            config.setdefault(section, []).extend(value)
        elif isinstance(value, dict):
            config.setdefault(section, {}).update(value)
        else:
            config[section] = value
    stream = io.StringIO()
    stream.write("#config_version=6\n")
    YAML(typ="safe", pure=True).dump(config, stream)
    return stream.getvalue()


def examples_machine(additions_extra=""):
    additions = [b for b in yaml_blocks(EVENTS_PAGE) if b.startswith("# Added to config/config.yaml")][0]
    files = {k: v for k, v in page_files(EVENTS_PAGE).items() if k.startswith("modes/")}
    return make_machine(merge_config(merge_config(full_config(EVENTS_PAGE), additions), additions_extra or "{}"),
                        files=files)


class TestEventExamples(GuideMachine):
    """build/events.md "More examples": additions block and the examples mode, read from the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = examples_machine()

    def test_examples(self):
        for event in ("lower_bank_complete", "one_more_ramp", "ramp_jackpot_lit", "logicblock_ramp_counter_complete",
                      "hurry_up_halfway", "hurry_up_missed", "hurry_up_collected", "show_status"):
            self.mock_event(event)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(2)
        self.assertModeRunning("examples")
        # drop target bank
        self.hit_switch_and_run("s_drop1", .6)
        self.hit_switch_and_run("s_drop2", .6)
        self.assertEventNotCalled("lower_bank_complete")
        self.hit_switch_and_run("s_drop3", .6)
        self.assertEventCalled("lower_bank_complete")
        # counter: hit event with count, events_when_complete replaces the default
        self.hit_and_release_switch("s_ramp")
        self.advance_time_and_run(.1)
        self.assertEventNotCalled("one_more_ramp")
        self.hit_and_release_switch("s_ramp")
        self.advance_time_and_run(.1)
        self.assertEventCalled("one_more_ramp")
        self.assertEventNotCalled("ramp_jackpot_lit")
        self.hit_and_release_switch("s_ramp")
        self.advance_time_and_run(.1)
        self.assertEventCalled("ramp_jackpot_lit")
        self.assertEventNotCalled("logicblock_ramp_counter_complete")
        # the 3rd ramp started the timer but did not collect (condition sees state before the event)
        self.assertTrue(self.machine.timers["hurry_up_timer"].running)
        self.assertEventNotCalled("hurry_up_collected")
        self.advance_time_and_run(4.5)
        self.assertEventNotCalled("hurry_up_halfway")
        self.advance_time_and_run(1)
        self.assertEventCalled("hurry_up_halfway")
        self.advance_time_and_run(5)
        self.assertEventCalled("hurry_up_missed")
        # a ramp after the timer ended does not collect
        self.hit_and_release_switch("s_ramp")
        self.advance_time_and_run(.1)
        self.assertEventNotCalled("hurry_up_collected")
        # both flipper buttons -> built-in flipper_cancel
        self.hit_switch_and_run("s_left_flipper", .1)
        self.hit_switch_and_run("s_right_flipper", .1)
        self.assertEventCalled("show_status")

    def test_collect_while_running(self):
        self.mock_event("hurry_up_collected")
        self.mock_event("hurry_up_missed")
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(2)
        for _ in range(3):
            self.hit_and_release_switch("s_ramp")
            self.advance_time_and_run(.1)
        self.advance_time_and_run(3)
        self.hit_and_release_switch("s_ramp")
        self.advance_time_and_run(.1)
        self.assertEventCalled("hurry_up_collected")
        self.assertFalse(self.machine.timers["hurry_up_timer"].running)
        self.advance_time_and_run(10)
        self.assertEventNotCalled("hurry_up_missed")

class TestCounterValueConditionLags(GuideMachine):
    """build/events.md warning: an event_player line `s_ramp_active{device.counters.ramp_counter.value==2}` in the
    examples mode is true on the third hit, because the counter has not counted that hit yet."""

    @classmethod
    def setUpClass(cls):
        mode_file = "modes/examples/config/examples.yaml"
        lagging = page_files(EVENTS_PAGE)[mode_file].replace(
            "event_player:\n", "event_player:\n  s_ramp_active{device.counters.ramp_counter.value==2}: lagging\n")
        additions = [b for b in yaml_blocks(EVENTS_PAGE) if b.startswith("# Added to config/config.yaml")][0]
        cls.machine_dir = make_machine(merge_config(full_config(EVENTS_PAGE), additions), files={mode_file: lagging})

    def test_lags_one_hit(self):
        self.mock_event("lagging")
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(2)
        for _ in (1, 2):
            self.hit_and_release_switch("s_ramp")
            self.advance_time_and_run(.1)
            self.assertEventNotCalled("lagging")
        self.hit_and_release_switch("s_ramp")
        self.advance_time_and_run(.1)
        self.assertEventCalled("lagging")


class TestOwnBothFlippersCombo(GuideMachine):
    """build/events.md warning: a combo switch named both_flippers is merged into MPF's built-in one."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = examples_machine(
            "combo_switches:\n  both_flippers:\n    switches_1: s_left_flipper\n    switches_2: s_right_flipper\n")

    def test_merged(self):
        self.mock_event("both_flippers_both")
        self.mock_event("flipper_cancel")
        self.advance_time_and_run(1)
        self.hit_switch_and_run("s_left_flipper", .1)
        self.hit_switch_and_run("s_right_flipper", .1)
        self.assertEqual("both", self.machine.combo_switches["both_flippers"].state)
        self.assertEventCalled("flipper_cancel")
        self.assertEventNotCalled("both_flippers_both")


SHOTS_PAGE = "build/shots-and-scoring.md"


class TestShotsAndScoring(GuideMachine):
    """build/shots-and-scoring.md: machine config and both mode files, read from the page."""

    @classmethod
    def setUpClass(cls):
        files = {k: v for k, v in page_files(SHOTS_PAGE).items() if k.startswith("modes/")}
        cls.machine_dir = make_machine(full_config(SHOTS_PAGE), files=files)

    def lanes(self):
        return [self.machine.shots[n].state_name for n in ("lane1", "lane2", "lane3")]

    def hit(self, switch):
        self.hit_and_release_switch(switch)
        self.advance_time_and_run(.1)

    def test_page_walkthrough(self):
        self.assertEqual(2, len([k for k in page_files(SHOTS_PAGE) if k.startswith("modes/")]))
        for event in ("lane1_hit", "lane1_unlit_hit", "lane1_default_hit", "lane1_default_unlit_hit",
                      "top_lanes_complete", "top_lanes_unlit_complete", "top_lanes_lit_complete"):
            self.mock_event(event)
        self.advance_time_and_run(1)
        self.hit("s_lane1")
        self.assertEventNotCalled("lane1_hit")
        self.start_game()
        self.advance_time_and_run(1)
        player = self.machine.game.player
        # group "complete" with all unlit at game start
        self.assertEventCalled("top_lanes_complete")
        self.assertEventCalled("top_lanes_unlit_complete")
        self.assertEqual(0, player.score)
        self.hit("s_left_sling")
        self.assertEqual(10, player.score)
        self.hit("s_lane1")
        self.assertEqual(110, player.score)
        self.assertEqual(["lit", "unlit", "unlit"], self.lanes())
        for event in ("lane1_hit", "lane1_unlit_hit", "lane1_default_hit", "lane1_default_unlit_hit"):
            self.assertEventCalled(event)
        self.hit("s_lane1")
        self.assertEqual(210, player.score)
        self.assertEqual(["lit", "unlit", "unlit"], self.lanes())
        self.hit("s_left_flipper")
        self.assertEqual(["unlit", "unlit", "lit"], self.lanes())
        self.hit("s_right_flipper")
        self.assertEqual(["lit", "unlit", "unlit"], self.lanes())
        self.assertEventNotCalled("top_lanes_lit_complete")
        self.hit("s_lane2")
        self.hit("s_lane3")
        self.assertEventCalled("top_lanes_lit_complete")
        self.assertEqual(5410, player.score)
        self.assertEqual(["unlit", "unlit", "unlit"], self.lanes())
        for _ in range(4):
            self.hit("s_ramp")
        self.assertEqual(61410, player.score)
        self.assertEqual("super", self.machine.shots["ramp"].state_name)
        self.assertEqual(2, player.ramp_supers)
        # |block in the higher-priority mode
        self.post_event("start_double_scoring")
        self.advance_time_and_run(.1)
        self.hit("s_left_sling")
        self.assertEqual(61430, player.score)
        self.post_event("stop_double_scoring")
        self.advance_time_and_run(.1)
        self.hit("s_left_sling")
        self.assertEqual(61440, player.score)
        # shot state kept for the player on the next ball
        self.advance_time_and_run(10)
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.assertEqual("super", self.machine.shots["ramp"].state_name)
        self.assertEqual(61440, player.score)


SHOWS_PAGE = "build/shows.md"


def shows_machine(mode_text_change=None):
    files = {k: v for k, v in page_files(SHOWS_PAGE).items() if k.startswith(("modes/", "shows/"))}
    if mode_text_change:
        key = "modes/base/config/base.yaml"
        files[key] = mode_text_change(files[key])
    return make_machine(full_config(SHOWS_PAGE), files=files)


class ShowsMachine(GuideMachine):
    def color(self, light):
        return self.machine.lights[light].get_color().hex

    def start_ball_now(self):
        """Press start without the 1 s MpfGameTestCase.start_game() advances, so show timing can be sampled."""
        self.hit_and_release_switch("s_start")
        self.machine_run()
        self.assertIsNotNone(self.machine.game)


class TestShows(ShowsMachine):
    """build/shows.md: machine config, show file and base mode, read from the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = shows_machine()

    def test_page_walkthrough(self):
        self.assertEqual({"modes/base/config/base.yaml", "shows/flash_light.yaml", "shows/blink.yaml",
                          "shows/lane_number.yaml"},
                         {k for k in page_files(SHOWS_PAGE) if not k.startswith("config/")})
        self.mock_event("target_flash_done")
        self.mock_event("start_pulse_done")
        # attract sweep
        self.advance_time_and_run(.1)
        self.assertEqual(("ffffff", "000000"), (self.color("l_lane1"), self.color("l_lane2")))
        self.advance_time_and_run(.5)
        self.assertEqual(("000000", "ffffff"), (self.color("l_lane1"), self.color("l_lane2")))
        self.advance_time_and_run(.5)
        self.assertEqual(("ffffff", "000000"), (self.color("l_lane1"), self.color("l_lane2")))
        # game: sweep stopped, start_pulse fades in and plays once
        self.start_ball_now()
        self.advance_time_and_run(.1)
        self.assertEqual("00007f", self.color("l_start"))
        self.assertEqual(("000000", "000000"), (self.color("l_lane1"), self.color("l_lane2")))
        self.advance_time_and_run(.1)
        self.assertEqual("0000ff", self.color("l_start"))
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.color("l_start"))
        self.advance_time_and_run(3)
        self.assertEqual("000000", self.color("l_start"))
        self.assertEventCalled("start_pulse_done", times=1)
        # shot light follows the shot state
        self.hit_and_release_switch("s_lane1")
        self.advance_time_and_run(.1)
        self.assertEqual(("ffffff", "000000"), (self.color("l_lane1"), self.color("l_lane2")))
        # target flash: three red flashes, then done and off
        self.hit_and_release_switch("s_target")
        samples = []
        for _ in range(14):
            self.advance_time_and_run(.125)
            samples.append(self.color("l_target"))
        self.assertEqual(["ff0000", "000000", "000000", "ff0000", "ff0000", "000000", "000000", "ff0000", "ff0000",
                          "000000", "000000", "000000", "000000", "000000"], samples)
        self.assertEventCalled("target_flash_done")
        # lane light still lit on ball 2
        self.advance_time_and_run(10)
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.assertEqual("ffffff", self.color("l_lane1"))


def shows_snippet(first_line, contains):
    blocks = [b for b in yaml_blocks(SHOWS_PAGE) if b.startswith(first_line) and contains in b]
    assert len(blocks) == 1, (first_line, contains)
    return blocks[0]


class TestShowTokensAndTags(ShowsMachine):
    """build/shows.md "How tokens work" and "Tags": blink, lane_number, lanes_orange and the flash_lanes player."""

    @classmethod
    def setUpClass(cls):
        play = shows_snippet("show_player:", "flash_lanes")
        config = merge_config(full_config(SHOWS_PAGE), shows_snippet("shows:", "lanes_orange"))
        cls.machine_dir = make_machine(config, files={
            **{k: v for k, v in page_files(SHOWS_PAGE).items() if k.startswith(("modes/", "shows/"))},
            "modes/base/config/base.yaml": page_files(SHOWS_PAGE)["modes/base/config/base.yaml"].replace(
                "show_player:\n", play, 1)})

    def lanes(self):
        return self.color("l_lane1"), self.color("l_lane2"), self.color("l_target")

    def test_tokens_and_tags(self):
        shows = self.machine.shows
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(5)
        # tag as a token value: both lanes flash red three times
        self.post_event("flash_lanes")
        samples = []
        for _ in range(14):
            self.advance_time_and_run(.125)
            samples.append(self.lanes())
        red, off = ("ff0000", "ff0000", "000000"), ("000000", "000000", "000000")
        self.assertEqual([red, off, off, red, red, off, off, red, red, off, off, off, off, off], samples)
        # token as part of a name
        shows["lane_number"].play(show_tokens={"num": "2"}, priority=1000)
        self.advance_time_and_run(.1)
        self.assertEqual(("000000", "008000", "000000"), self.lanes())
        # tag directly in a step
        shows["lanes_orange"].play(priority=2000)
        self.advance_time_and_run(.1)
        self.assertEqual(("ffa500", "ffa500", "000000"), self.lanes())
        # token mismatches
        with self.assertRaisesRegex(ValueError, 'Token mismatch while playing show "blink"'):
            shows["blink"].play(show_tokens={"light": "l_target", "colour": "red"})
        shows["blink"].play(show_tokens={"color": "blue"}, priority=3000)
        self.advance_time_and_run(.1)
        self.assertEqual(("ffa500", "ffa500", "000000"), self.lanes())
        with self.assertRaisesRegex(Exception, r"Invalid color \(color\).*CFE-light_player-1"):
            shows["blink"].play(show_tokens={"light": "l_target"}, priority=3000)
            self.advance_time_and_run(.1)

    def test_unknown_light_or_tag(self):
        self.advance_time_and_run(1)
        with self.assertRaisesRegex(Exception, "Could not find a lights device with name or tag l_nope.*CFE-light_player-101"):
            self.machine.shows["blink"].play(show_tokens={"light": "l_nope", "color": "red"})
            self.advance_time_and_run(.1)

    def test_builtin_color_shows(self):
        self.advance_time_and_run(1)
        self.machine.shows["led_color"].play(show_tokens={"light": "lane_lights", "color": "purple"})
        self.advance_time_and_run(.1)
        self.assertEqual("800080", self.color("l_lane2"))
        self.machine.shows["flash_color"].play(show_tokens={"light": "l_target", "color": "red"})
        self.advance_time_and_run(.5)
        self.assertEqual("ff0000", self.color("l_target"))
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.color("l_target"))
        self.advance_time_and_run(1)
        self.assertEqual("ff0000", self.color("l_target"))


class TestShowNameTaken(unittest.TestCase):
    """build/shows.md: a show file named flash_color clashes with MPF's built-in show."""

    def test_duplicate(self):
        files = {k: v for k, v in page_files(SHOWS_PAGE).items() if k.startswith(("modes/", "shows/"))}
        files["shows/flash_color.yaml"] = files.pop("shows/blink.yaml")
        machine_dir = make_machine(full_config(SHOWS_PAGE), files=files)

        class Machine(ShowsMachine):
            def runTest(self):
                pass
        Machine.machine_dir = machine_dir
        with self.assertRaisesRegex(AssertionError, "Duplicate show flash_color"):
            Machine("runTest").setUp()


class TestShowWithoutLoops(ShowsMachine):
    """build/shows.md warning: without `loops`, start_pulse repeats every 2 s."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = shows_machine(lambda text: text.replace("      loops: 0\n", ""))

    def test_repeats(self):
        self.advance_time_and_run(1)
        self.start_ball_now()
        self.advance_time_and_run(.5)
        self.assertEqual("0000ff", self.color("l_start"))
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.color("l_start"))
        self.advance_time_and_run(1)
        self.assertEqual("0000ff", self.color("l_start"))


HOW_EVENTS_PAGE = "architecture/how-events-work.md"
QUEUE_RELAY = "queue_relay_player:\n  ball_ending:\n    post: bonus_start\n    wait_for: bonus_done\n"


def how_events_machine(config_extra=None, files_extra=None):
    files = {k: v for k, v in page_files(HOW_EVENTS_PAGE).items() if k.startswith("modes/")}
    files.update(files_extra or {})
    config = full_config(HOW_EVENTS_PAGE)
    if config_extra:
        config = merge_config(config, config_extra)
    return make_machine(config, files=files)


class HowEventsMachine(GuideMachine):
    def setUp(self):
        from mpf.core.events import EventManager
        self.posted = []
        original = EventManager._post
        posted = self.posted

        def recording_post(manager, event, ev_type, callback, **kwargs):
            posted.append(event)
            return original(manager, event, ev_type, callback, **kwargs)

        self._original_post = original
        EventManager._post = recording_post
        super().setUp()

    def tearDown(self):
        from mpf.core.events import EventManager
        EventManager._post = self._original_post
        super().tearDown()

    def press_start(self):
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(1)


class TestHowEventsWork(HowEventsMachine):
    """architecture/how-events-work.md: machine config, base mode, bonus and start_lock modes with their code."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = how_events_machine()

    def test_files_on_page(self):
        self.assertEqual({"config/config.yaml", "modes/base/config/base.yaml", "modes/bonus/config/bonus.yaml",
                          "modes/bonus/code/bonus.py", "modes/start_lock/config/start_lock.yaml",
                          "modes/start_lock/code/start_lock.py"}, set(page_files(HOW_EVENTS_PAGE)))

    def test_depth_first_order(self):
        order = []
        for name in ("chain_a", "chain_a_child", "chain_a_grandchild", "chain_b"):
            self.machine.events.add_handler(name, lambda name=name, **kwargs: order.append(name))
        self.advance_time_and_run(1)
        self.machine.events.post("chain_a")
        self.machine.events.post("chain_b")
        self.advance_time_and_run(.1)
        self.assertEqual(["chain_a", "chain_a_child", "chain_a_grandchild", "chain_b"], order)

    def test_boolean_start_lock(self):
        self.mock_event("start_refused")
        self.advance_time_and_run(1)
        self.hit_switch_and_run("s_coin_door", .1)
        self.press_start()
        self.assertIsNone(self.machine.game)
        self.assertEventCalledWith("start_refused", reason="coin door open")
        self.release_switch_and_run("s_coin_door", .1)
        self.press_start()
        self.assertIsNotNone(self.machine.game)

    def test_relay_ball_save(self):
        seen = []
        self.machine.events.add_handler("ball_drain", lambda balls, **kwargs: seen.append(balls), priority=0)
        self.mock_event("ball_save_first_save_saving_ball")
        self.advance_time_and_run(1)
        self.press_start()
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.drain_all_balls()
        self.advance_time_and_run(1)
        self.assertEqual([0], seen)
        self.assertEventCalled("ball_save_first_save_saving_ball")
        self.assertBallNumber(1)
        self.advance_time_and_run(12)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.drain_all_balls()
        self.advance_time_and_run(4)
        self.assertEqual([0, 1], seen)
        self.assertBallNumber(2)

    def test_bonus_queue_and_timeline(self):
        times = {}
        self.mock_event("bonus_advanced")
        self.advance_time_and_run(1)
        self.press_start()
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(12)
        self.assertEventCalledWith("bonus_advanced", source="target")
        for name in ("ball_will_end", "bonus_counting", "bonus_counted", "ball_ended", "ball_started"):
            self.machine.events.add_handler(
                name, lambda name=name, **kwargs: times.setdefault(name, self.machine.clock.get_time()), priority=-100)
        drained = self.machine.clock.get_time()
        self.drain_all_balls()
        self.advance_time_and_run(4)
        rel = {k: round(v - drained, 1) for k, v in times.items()}
        self.assertEqual(rel["ball_will_end"], rel["bonus_counting"])
        for name in ("bonus_counted", "ball_ended", "ball_started"):
            self.assertAlmostEqual(rel["bonus_counting"] + 2, rel[name], delta=.11)
        # the rest of the game, then check the documented timeline is an ordered subsequence of what was posted
        for _ in (2, 3):
            self.hit_and_release_switch("s_target")
            self.advance_time_and_run(12)
            self.drain_all_balls()
            self.advance_time_and_run(4)
        self.assertGameIsNotRunning()
        timeline = [
            "init_phase_1", "init_phase_5", "init_done", "machine_reset_phase_1", "machine_reset_phase_3",
            "reset_complete", "mode_attract_will_start", "mode_attract_starting", "mode_attract_started",
            "collecting_balls_complete",
            "request_to_start_game", "game_start", "mode_game_will_start", "mode_game_starting", "mode_attract_will_stop",
            "mode_attract_stopping", "mode_attract_stopped", "mode_game_started", "game_will_start", "game_starting",
            "player_add_request", "player_adding", "player_added", "game_started", "player_turn_will_start",
            "player_turn_starting", "player_turn_started",
            "ball_will_start", "ball_starting", "mode_base_will_start", "mode_base_starting", "mode_base_started",
            "balls_in_play", "ball_started", "ball_save_first_save_enabled", "single_player_ball_started",
            "ball_start_target", "balldevice_balls_available", "balldevice_bd_trough_ejecting_ball",
            "playfield_active", "balldevice_bd_trough_ball_eject_success", "balldevice_playfield_ball_enter",
            "ball_save_first_save_grace_period", "ball_save_first_save_disabled",
            "balldevice_captured_from_playfield", "balldevice_bd_trough_ball_enter", "ball_drain", "ball_will_end",
            "mode_base_will_stop", "mode_base_stopping", "mode_base_stopped", "ball_ending", "ball_ended",
            "player_turn_will_end", "player_turn_ending", "player_turn_ended",
            "game_will_end", "game_ending", "game_ended", "mode_game_will_stop", "mode_game_stopping",
            "mode_attract_will_start", "mode_attract_starting", "mode_attract_started", "collecting_balls_complete",
            "mode_game_stopped"]
        position = 0
        for name in timeline:
            self.assertIn(name, self.posted[position:], "timeline event {} missing after position {}".format(
                name, position))
            position = self.posted.index(name, position) + 1


class TestQueueRelayInMachineConfig(HowEventsMachine):
    """The queue_relay_player example, added to the machine config: the ball waits for bonus_done."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = how_events_machine(config_extra=QUEUE_RELAY)

    def test_holds_ball_ending(self):
        self.assertIn(QUEUE_RELAY.strip(), "\n".join(yaml_blocks(HOW_EVENTS_PAGE)))
        self.mock_event("bonus_start")
        self.advance_time_and_run(1)
        self.press_start()
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(12)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertEventCalled("bonus_start")
        self.assertBallNumber(1)
        self.post_event("bonus_done")
        self.advance_time_and_run(1)
        self.assertBallNumber(2)


class TestQueueRelayInBaseMode(HowEventsMachine):
    """The warning: in the base mode (stops on ball_will_end) the same queue_relay_player never sees ball_ending."""

    @classmethod
    def setUpClass(cls):
        base = page_files(HOW_EVENTS_PAGE)["modes/base/config/base.yaml"] + "\n" + QUEUE_RELAY
        cls.machine_dir = how_events_machine(files_extra={"modes/base/config/base.yaml": base})

    def test_never_posts(self):
        self.mock_event("bonus_start")
        self.advance_time_and_run(1)
        self.press_start()
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(12)
        self.drain_all_balls()
        self.advance_time_and_run(4)
        self.assertEventNotCalled("bonus_start")
        self.assertBallNumber(2)


class TestModeOwnStartEvent(GuideMachine):
    """The note: a mode's player keyed to the mode's own start event is refused when the mode first starts."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = modes_machine({"modes/skillshot/config/skillshot.yaml":
                                         page_files(MODES_PAGE)["modes/skillshot/config/skillshot.yaml"].replace(
                                             "event_player:\n", "event_player:\n  ball_started: oops\n")})

    def test_refused_at_mode_start(self):
        self.advance_time_and_run(1)
        self.assertModeRunning("attract")
        with self.assertRaisesRegex(Exception, 'Change the event_player: ball_started: event name to\\s+'
                                               '"mode_skillshot_started:"'):
            self.start_game()
            self.advance_time_and_run(1)


MB_PAGE = "build/multiball.md"
MB_RESET = "    reset_count_for_current_player_events: multiball_main_mb_started\n"


def mb_machine(without_reset=False):
    files = {k: v for k, v in page_files(MB_PAGE).items() if k.startswith("modes/")}
    if without_reset:
        files["modes/base/config/base.yaml"] = files["modes/base/config/base.yaml"].replace(MB_RESET, "")
    return make_machine(full_config(MB_PAGE), files=files)


class MultiballMachine(GuideMachine):
    def counts(self):
        g = self.machine.game
        return (self.machine.ball_devices["bd_trough"].balls, self.machine.ball_devices["bd_lock"].balls,
                self.machine.playfield.balls, g.balls_in_play, self.machine.multiball_locks["vuk_lock"].locked_balls)

    def lock_ball(self):
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(5)

    def play_to_ball_2(self):
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.lock_ball()
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.lock_ball()
        self.advance_time_and_run(12)
        for _ in range(3):
            self.drain_one_ball()
            self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)


class TestMultiball(MultiballMachine):
    """build/multiball.md: machine config and base mode, read from the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = mb_machine()

    def test_page_walkthrough(self):
        self.assertIn(MB_RESET, page_files(MB_PAGE)["modes/base/config/base.yaml"])
        for event in ("multiball_lock_vuk_lock_locked_ball", "multiball_lock_vuk_lock_full",
                      "multiball_main_mb_started", "multiball_main_mb_shoot_again", "multiball_main_mb_shoot_again_ended",
                      "multiball_main_mb_ball_lost", "multiball_main_mb_lost_ball", "multiball_main_mb_ended"):
            self.mock_event(event)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        player = self.machine.game.player
        self.assertEqual((2, 0, 1, 1, 0), self.counts())
        self.assertEqual(0, player.score)
        self.lock_ball()
        self.assertEqual((1, 1, 1, 1, 1), self.counts())
        self.assertEventCalledWith("multiball_lock_vuk_lock_locked_ball", total_balls_locked=1)
        self.assertEqual(1000, player.score)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.assertEqual(1000, player.score)
        self.lock_ball()
        self.assertEventCalled("multiball_lock_vuk_lock_full")
        self.assertEventCalledWith("multiball_main_mb_started", balls=3)
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(3, self.machine.game.balls_in_play)
        self.assertEqual(0, self.machine.multiball_locks["vuk_lock"].locked_balls)
        self.assertEqual(2000, player.score)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.assertEqual(2100, player.score)
        # drain inside shoot_again is replaced
        self.drain_one_ball()
        self.advance_time_and_run(4)
        self.assertEventCalled("multiball_main_mb_shoot_again")
        self.assertEqual((0, 0, 3, 3), self.counts()[:4])
        self.advance_time_and_run(8)
        self.assertEventCalled("multiball_main_mb_shoot_again_ended")
        # drains after the window
        self.drain_one_ball()
        self.advance_time_and_run(2)
        self.assertEqual((1, 0, 2, 2), self.counts()[:4])
        self.assertEventCalled("multiball_main_mb_ball_lost")
        self.assertEventNotCalled("multiball_main_mb_lost_ball")
        self.assertEventNotCalled("multiball_main_mb_ended")
        self.drain_one_ball()
        self.advance_time_and_run(2)
        self.assertEqual((2, 0, 1, 1), self.counts()[:4])
        self.assertEventCalled("multiball_main_mb_ended")
        self.drain_one_ball()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        # the lock works again on ball 2
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.lock_ball()
        self.assertEqual((1, 1, 1, 1, 1), self.counts())
        self.assertEqual(3100, player.score)


class TestMultiballWithoutReset(MultiballMachine):
    """build/multiball.md warning: without the reset, the lock stays full and ball 2's lock does nothing."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = mb_machine(without_reset=True)

    def test_lock_stays_full(self):
        self.mock_event("multiball_lock_vuk_lock_locked_ball")
        self.play_to_ball_2()
        self.assertEqual(2, self.machine.multiball_locks["vuk_lock"].locked_balls)
        before = self._events["multiball_lock_vuk_lock_locked_ball"]
        score = self.machine.game.player.score
        self.lock_ball()
        self.assertEqual(before, self._events["multiball_lock_vuk_lock_locked_ball"])
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(score, self.machine.game.player.score)


BS_PAGE = "build/ball-saves-and-extra-balls.md"
GROUP_LIMIT = "    max_per_game: 1\n"


def bs_machine(without_group_limit=False):
    files = {k: v for k, v in page_files(BS_PAGE).items() if k.startswith("modes/")}
    config = full_config(BS_PAGE)
    if without_group_limit:
        config = config.replace("    award_lit_events: s_eb_collect_active\n" + GROUP_LIMIT,
                                "    award_lit_events: s_eb_collect_active\n")
    return make_machine(config, files=files)


class BallSaveMachine(GuideMachine):
    def setUp(self):
        super().setUp()
        self.log = []
        self.t0 = 0
        for name in ("ball_save_start_save_enabled", "ball_save_start_save_timer_start", "ball_save_start_save_hurry_up",
                     "ball_save_start_save_grace_period", "ball_save_start_save_disabled",
                     "ball_save_start_save_saving_ball", "extra_ball_target_eb_lit", "extra_ball_group_main_lit_awarded",
                     "extra_ball_group_main_lit", "extra_ball_group_main_unlit", "extra_ball_group_main_awarded",
                     "extra_ball_awarded", "extra_ball_award_disabled", "extra_ball_target_eb_award_disabled",
                     "extra_ball_group_main_award_disabled", "ball_started", "ball_ended"):
            self.machine.events.add_handler(
                name, lambda name=name, **kwargs: self.log.append(
                    (round(self.machine.clock.get_time() - self.t0, 1), name,
                     {k: v for k, v in kwargs.items() if k in ("ball", "is_extra_ball", "balls", "early_save")})),
                priority=-50)

    def names(self, since=0):
        return [n for t, n, a in self.log if t >= since]

    def eb_names(self, start=0):
        return [n for t, n, a in self.log[start:] if n.startswith("extra_ball")]

    def eb_round(self):
        self.hit_and_release_switch("s_eb_target")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("s_eb_collect")
        self.advance_time_and_run(.5)


class TestBallSavesAndExtraBalls(BallSaveMachine):
    """build/ball-saves-and-extra-balls.md: machine config and base mode, read from the page."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = bs_machine()

    def test_ball_save_timeline_and_saves(self):
        self.advance_time_and_run(1)
        self.t0 = self.machine.clock.get_time()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(2)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(14)
        timeline = [(t, n) for t, n, a in self.log if n.startswith("ball_save") or n == "ball_started"]
        self.assertEqual([(0.0, "ball_started"), (0.0, "ball_save_start_save_enabled"),
                          (2.0, "ball_save_start_save_timer_start"), (9.0, "ball_save_start_save_hurry_up"),
                          (12.0, "ball_save_start_save_grace_period"), (14.0, "ball_save_start_save_disabled")],
                         timeline)
        # ball 2: a drain during the save is saved once, the next drain ends the ball
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(2)
        self.drain_all_balls()
        self.advance_time_and_run(4)
        saving = [a for t, n, a in self.log if n == "ball_save_start_save_saving_ball"]
        self.assertEqual([{"balls": 1, "early_save": False}], saving)
        self.assertBallNumber(2)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.drain_all_balls()
        self.advance_time_and_run(4)
        self.assertBallNumber(3)
        # ball 3: early save on the outlane
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(1)
        self.hit_and_release_switch("s_left_outlane")
        self.advance_time_and_run(4)
        self.assertEqual({"balls": 1, "early_save": True},
                         [a for t, n, a in self.log if n == "ball_save_start_save_saving_ball"][-1])
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.game.balls_in_play)
        self.drain_one_ball()
        self.advance_time_and_run(3)
        self.assertBallNumber(3)

    def test_extra_ball(self):
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        player = self.machine.game.player
        start = len(self.log)
        self.hit_and_release_switch("s_eb_target")
        self.advance_time_and_run(.5)
        self.assertEqual(["extra_ball_target_eb_lit", "extra_ball_group_main_lit_awarded", "extra_ball_group_main_lit"],
                         self.eb_names(start))
        self.hit_and_release_switch("s_eb_collect")
        self.advance_time_and_run(.5)
        self.assertEqual(["extra_ball_target_eb_lit", "extra_ball_group_main_lit_awarded", "extra_ball_group_main_lit",
                          "extra_ball_group_main_unlit", "extra_ball_group_main_awarded", "extra_ball_awarded"],
                         self.eb_names(start))
        self.assertEqual(1, player.extra_balls)
        # the group limit refuses a second one: the light is refused, the collect finds nothing lit
        start = len(self.log)
        self.hit_and_release_switch("s_eb_target")
        self.advance_time_and_run(.5)
        self.assertEqual(["extra_ball_award_disabled", "extra_ball_target_eb_award_disabled",
                          "extra_ball_group_main_award_disabled"], self.eb_names(start))
        start = len(self.log)
        self.hit_and_release_switch("s_eb_collect")
        self.advance_time_and_run(.5)
        self.assertEqual(["extra_ball_group_main_award_disabled"], self.eb_names(start))
        self.assertEqual(1, player.extra_balls)
        # the unformatted player variable from the note
        self.assertEqual(0, player["extra_ball_group_{}_num_lit"])
        # drain ball 1 (save is still running from ball start, so wait it out): the same ball is played again
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(13)
        start = len(self.log)
        self.drain_all_balls()
        self.advance_time_and_run(4)
        started = [a for t, n, a in self.log[start:] if n == "ball_started"]
        self.assertEqual([{"ball": 1, "is_extra_ball": True}], started)
        self.assertEqual(0, player.extra_balls)


class TestBallSaveTimerOnPlayfieldActive(BallSaveMachine):
    """build/ball-saves-and-extra-balls.md warning: with playfield_active, a first switch after the eject timeout
    never starts the timer, so the save lasts for the whole ball."""

    @classmethod
    def setUpClass(cls):
        files = {k: v for k, v in page_files(BS_PAGE).items() if k.startswith("modes/")}
        key = "modes/base/config/base.yaml"
        files[key] = files[key].replace("timer_start_events: balldevice_bd_trough_ball_eject_success",
                                        "timer_start_events: playfield_active")
        cls.machine_dir = make_machine(full_config(BS_PAGE), files=files)

    def test_never_times_out(self):
        self.assertIn("timer_start_events: balldevice_bd_trough_ball_eject_success",
                      page_files(BS_PAGE)["modes/base/config/base.yaml"])
        self.advance_time_and_run(1)
        self.t0 = self.machine.clock.get_time()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(5)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(12)
        self.assertNotIn("ball_save_start_save_timer_start", self.names())
        self.drain_all_balls()
        self.advance_time_and_run(2)
        self.assertIn("ball_save_start_save_saving_ball", self.names())
        self.assertBallNumber(1)


class TestBallSaveTimerOnEjectSuccessLate(BallSaveMachine):
    """The page's event starts the timer even when the eject timeout confirms the ball (3.1 s, off at 15.1 s)."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = bs_machine()

    def test_starts_on_timeout(self):
        self.advance_time_and_run(1)
        self.t0 = self.machine.clock.get_time()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(5)
        self.hit_and_release_switch("s_target")
        self.advance_time_and_run(12)
        times = {n: t for t, n, a in self.log}
        self.assertAlmostEqual(3.1, times["ball_save_start_save_timer_start"], delta=.11)
        self.assertAlmostEqual(15.1, times["ball_save_start_save_disabled"], delta=.11)


class TestExtraBallWithoutGroupLimit(BallSaveMachine):
    """build/ball-saves-and-extra-balls.md warning: without a group limit, the extra ball's own max_per_game
    (default 1) does not stop light-and-collect."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = bs_machine(without_group_limit=True)

    def test_unlimited(self):
        self.assertIn(GROUP_LIMIT, full_config(BS_PAGE))
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        for _ in range(3):
            self.eb_round()
        self.assertEqual(3, self.machine.game.player.extra_balls)
        self.assertNotIn("extra_ball_award_disabled", self.names())
        # lit but not collected: lit again when the next ball starts
        self.hit_and_release_switch("s_eb_target")
        self.advance_time_and_run(15)
        start = len(self.log)
        self.drain_all_balls()
        self.advance_time_and_run(4)
        self.assertIn("ball_started", [n for t, n, a in self.log[start:]])
        self.assertIn("extra_ball_group_main_lit", self.eb_names(start))


def example_machine(page, config_change=None, file_changes=None):
    """A machine from an examples page: its labelled machine config and every labelled mode file."""
    files = {k: v for k, v in page_files(page).items() if k.startswith("modes/")}
    for key, change in (file_changes or {}).items():
        files[key] = change(files[key])
    config = full_config(page)
    if config_change:
        config = config_change(config)
    return make_machine(config, files=files)


class ExampleMachine(GuideMachine):
    def hit(self, switch, times=1):
        for _ in range(times):
            self.hit_and_release_switch(switch)
            self.advance_time_and_run(.1)

    def running(self):
        return sorted(m.name for m in self.machine.mode_controller.active_modes if m.name not in ("game", "base"))


BONUS_PAGE = "examples/scoring/end-of-ball-bonus.md"


class TestExampleBonus(ExampleMachine):
    """examples/scoring/end-of-ball-bonus.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(BONUS_PAGE)

    def test_walkthrough(self):
        log = []
        t0 = [0.0]
        for name in ("bonus_start", "bonus_entry", "ball_started"):
            self.machine.events.add_handler(
                name, lambda name=name, **kwargs: log.append(
                    (round(self.machine.clock.get_time() - t0[0], 2), name, kwargs.get("entry"), kwargs.get("score"),
                     kwargs.get("bonus_score"))), priority=-9)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        player = self.machine.game.player
        self.hit("s_ramp", 3)
        self.hit("s_target", 2)
        lanes = self.machine.shot_groups["bonus_lanes"].config["shots"]
        self.hit("s_lane_left")
        self.assertEqual(["lit", "unlit", "unlit"], [s.state_name for s in lanes])
        self.hit("s_lane_left")   # already lit: stays lit
        self.assertEqual(["lit", "unlit", "unlit"], [s.state_name for s in lanes])
        self.assertEqual(1, player.bonus_multiplier)
        self.hit("s_left_flipper")  # lane change: the lit lane wraps to the right
        self.assertEqual(["unlit", "unlit", "lit"], [s.state_name for s in lanes])
        self.hit("s_lane_left")
        self.hit("s_lane_center")
        self.assertEqual(["unlit", "unlit", "unlit"], [s.state_name for s in lanes])  # reset on complete
        self.assertEqual(2, player.bonus_multiplier)
        self.assertEqual(7100, player.score)  # 1500 + 200 + 4 lane hits + 5000
        t0[0] = self.machine.clock.get_time()
        del log[:]
        self.drain_all_balls()
        self.advance_time_and_run(10)
        self.assertEqual([
            (0.5, "bonus_start", None, None, None),
            (1.5, "bonus_entry", "ball_bonus", 1000, 1000),
            (2.5, "bonus_entry", "ramps", 3000, 4000),
            (3.5, "bonus_entry", "targets", 500, 4500),
            (4.5, "bonus_entry", "subtotal", 4500, None),
            (5.5, "bonus_entry", "multiplier", 2, None),
            (6.5, "bonus_entry", "total", 9000, None),
            (7.5, "ball_started", None, None, None)], log)
        self.assertEqual(16100, player.score)
        self.assertEqual((0, 0, 1), (player.ramps, player.targets, player.bonus_multiplier))
        # ball 2: multiplier capped at 5, flipper_cancel hurries the count
        self.hit("s_ramp")
        for _ in range(6):
            for lane in ("s_lane_left", "s_lane_center", "s_lane_right"):
                self.hit(lane)
        self.assertEqual(5, player.bonus_multiplier)
        self.assertEqual(16100 + 500 + 1800 + 30000, player.score)
        t0[0] = self.machine.clock.get_time()
        del log[:]
        self.drain_all_balls()
        self.advance_time_and_run(1.2)
        self.hit_switch_and_run("s_left_flipper", .05)
        del log[:]
        self.hit_switch_and_run("s_right_flipper", 0)  # flipper_cancel: time the hurried lines from here
        t0[0] = self.machine.clock.get_time()
        self.advance_time_and_run(2)
        self.assertEqual([
            (0.0, "bonus_entry", "ball_bonus", 1000), (0.1, "bonus_entry", "ramps", 1000),
            (0.2, "bonus_entry", "subtotal", 2000), (0.3, "bonus_entry", "multiplier", 5),
            (0.4, "bonus_entry", "total", 10000), (0.5, "ball_started", None, None)],
            [(t, n, e, s) for t, n, e, s, b in log])

        self.assertEqual(58400, player.score)


class TestExampleBonusWithoutInitialMultiplier(ExampleMachine):
    """The page: without player_vars, the first completed set of lanes only brings the multiplier to 1."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(BONUS_PAGE, config_change=lambda c: c.replace(
            "player_vars:\n  bonus_multiplier:\n    initial_value: 1\n\n", ""))

    def test_first_lane_gives_1x(self):
        self.assertNotIn("player_vars", full_config(BONUS_PAGE).replace(
            "player_vars:\n  bonus_multiplier:\n    initial_value: 1\n\n", ""))
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        for expected in (1, 2):
            for lane in ("s_lane_left", "s_lane_center", "s_lane_right"):
                self.hit(lane)
            self.assertEqual(expected, self.machine.game.player.bonus_multiplier)


JACKPOTS_PAGE = "examples/multiball/multiball-jackpots.md"


class JackpotsMachine(ExampleMachine):
    def state(self):
        shots = self.machine.shots
        player = self.machine.game.player
        jackpot = player.jackpot_value if player.is_player_var("jackpot_value") else None
        return (player.score, jackpot,
                shots["left_jackpot"].state_name, shots["right_jackpot"].state_name,
                shots["super_jackpot"].enabled, self.machine.game.balls_in_play)

    def begin(self):
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)


class TestExampleJackpots(JackpotsMachine):
    """examples/multiball/multiball-jackpots.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(JACKPOTS_PAGE)

    def test_walkthrough(self):
        self.mock_event("jackpots_lit_complete")
        self.begin()
        self.hit("s_left_ramp")
        self.assertEqual(0, self.machine.game.player.score)
        self.assertNotIn("jackpots", self.running())
        self.hit("s_target", 3)
        self.advance_time_and_run(4)
        self.assertEqual((300, 10000, "lit", "lit", False, 2), self.state())
        self.assertEventCalled("jackpots_lit_complete")  # "also posted at the start of every round"
        self.hit("s_left_ramp")
        self.assertEqual((10300, 10000, "collected", "lit", False, 2), self.state())
        self.hit("s_left_ramp")
        self.hit("s_scoop")
        self.assertEqual((10300, 10000, "collected", "lit", False, 2), self.state())
        self.hit("s_target", 2)
        self.assertEqual((10500, 12000, "collected", "lit", False, 2), self.state())
        self.hit("s_right_ramp")
        self.assertEqual((22500, 12000, "collected", "collected", True, 2), self.state())
        self.hit("s_scoop")
        self.assertEqual((82500, 12000, "lit", "lit", False, 2), self.state())
        self.hit("s_scoop")
        self.assertEqual(82500, self.machine.game.player.score)
        self.hit("s_right_ramp")
        self.assertEqual((94500, 12000, "lit", "collected", False, 2), self.state())
        self.advance_time_and_run(6)
        self.drain_one_ball()
        self.advance_time_and_run(2)
        self.assertEqual(1, self.machine.game.balls_in_play)
        self.assertNotIn("jackpots", self.running())
        self.hit("s_left_ramp")
        self.assertEqual(94500, self.machine.game.player.score)
        self.hit("s_target", 2)
        self.assertEqual(1, self.machine.game.balls_in_play)
        self.hit("s_target")
        self.advance_time_and_run(4)
        self.assertEqual((94800, 10000, "lit", "lit", False, 2), self.state())
        self.hit("s_right_ramp")
        self.assertEqual((104800, 10000, "lit", "collected", False, 2), self.state())


class TestExampleJackpotsCounterNotDisabled(JackpotsMachine):
    """The note: with disable_on_complete: false, targets during the multiball count toward the next one."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(JACKPOTS_PAGE, file_changes={
            "modes/base/config/base.yaml": lambda t: t.replace(
                "    start_enabled: true\n    enable_events: multiball_main_mb_ended\n",
                "    disable_on_complete: false\n")})

    def test_next_multiball_after_one_target(self):
        self.begin()
        self.hit("s_target", 3)
        self.advance_time_and_run(4)
        self.hit("s_target", 2)
        self.advance_time_and_run(6)
        self.drain_one_ball()
        self.advance_time_and_run(2)
        self.assertEqual(1, self.machine.game.balls_in_play)
        self.hit("s_target")
        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.game.balls_in_play)


MISSIONS_PAGE = "examples/game-flow/mission-ladder.md"


class MissionsMachine(ExampleMachine):
    def state(self):
        a = self.machine.achievements

        def show(name):
            return a[name].state + ("*" if a[name].selected else "")
        return self.machine.game.player.score, show("ramps"), show("targets"), self.running()


class TestExampleMissions(MissionsMachine):
    """examples/game-flow/mission-ladder.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(MISSIONS_PAGE)

    def test_walkthrough(self):
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        self.assertEqual((0, "enabled*", "enabled", []), self.state())
        self.hit("s_left_sling")
        self.assertEqual((0, "enabled", "enabled*", []), self.state())
        self.hit("s_left_sling")
        self.assertEqual((0, "enabled*", "enabled", []), self.state())
        self.hit("s_scoop")
        self.assertEqual((0, "started", "enabled", ["mission_ramps"]), self.state())
        self.hit("s_left_sling")
        self.hit("s_scoop")
        self.assertEqual((0, "started", "enabled", ["mission_ramps"]), self.state())
        self.advance_time_and_run(21)
        self.assertEqual((0, "stopped*", "enabled", []), self.state())
        self.hit("s_scoop")
        self.assertEqual((0, "started", "enabled", ["mission_ramps"]), self.state())
        self.hit("s_ramp", 3)
        self.assertEqual((65000, "completed", "enabled*", []), self.state())
        self.advance_time_and_run(10)
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.assertEqual((65000, "completed", "enabled*", []), self.state())
        self.hit("s_scoop")
        self.assertEqual((65000, "completed", "started", ["mission_targets"]), self.state())
        self.hit("s_target", 2)
        self.assertEqual((125000, "completed", "completed", ["wizard"]), self.state())
        self.hit("s_ramp")
        self.assertEqual(225000, self.machine.game.player.score)
        self.hit("s_scoop")
        self.assertEqual((1225000, "enabled*", "enabled", []), self.state())
        self.hit("s_scoop")
        self.assertEqual((1225000, "started", "enabled", ["mission_ramps"]), self.state())

    def test_drain_during_mission(self):
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(1)
        self.hit("s_scoop")
        self.hit("s_ramp")
        self.assertEqual(1, self.machine.counters["mission_ramp_count"].value)
        self.advance_time_and_run(8)
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertBallNumber(2)
        self.assertEqual((5000, "stopped*", "enabled", []), self.state())
        self.hit("s_scoop")
        self.assertEqual(["mission_ramps"], self.running())
        self.assertEqual(0, self.machine.counters["mission_ramp_count"].value)


class TestEventCorrectionsStillHold(unittest.TestCase):
    """gen_reference.EVENT_CORRECTIONS: each annotated name still differs from what the code posts."""

    def test_multiball_lost_ball(self):
        source = (Path(__file__).resolve().parents[2] / "mpf" / "devices" / "multiball.py").read_text(encoding="utf-8")
        self.assertIn('"multiball_{}_ball_lost".format(self.name)', source)
        self.assertIn("event: multiball_(name)_lost_ball", source)


DEBUG_PAGE = "build/debugging.md"
FIRST = "get-started/first-machine.md"

# (name, replacement applied to the first-machine config, text quoted on the debugging page, fails at boot?)
MISTAKES = [
    ("tab", ("  s_start:\n    number:", "  s_start:\n\tnumber:"),
     "while scanning for the next token found character that cannot start any token"),
    ("indent", ("    eject_targets: playfield\n", "   eject_targets: playfield\n"),
     "while parsing a block mapping"),
    ("duplicate", ("  s_trough3:\n    number:\n", "  s_trough3:\n    number:\n  s_trough3:\n    number:\n"),
     'found duplicate key "s_trough3"'),
    ("colon", ("  balls_installed: 3", "  balls_installed 3"),
     'Your config contains a value for the setting "machine:b", but this is not a valid setting name.'),
    ("version", ("#config_version=6\n", ""), "Version mismatch. Expected: #config_version=6 Actual:"),
    ("section", ("switches:", "switchs:"),
     'but that section name is unknown. Did you mean "switches:" instead?'),
    ("setting", ("    eject_coil: c_trough_eject\n", "    eject_coil: c_trough_eject\n    eject_coils: c_trough_eject\n"),
     'Your config contains a value for the setting "ball_devices:bd_trough:eject_coils", but this is not a valid '
     'setting name.'),
    ("device", ("eject_coil: c_trough_eject", "eject_coil: c_trough_ejct"),
     'Device "c_trough_ejct" not found in "coils:" section in your config.'),
    ("device_path", ("eject_coil: c_trough_eject", "eject_coil: c_trough_ejct"),
     'Entry ball_device_ejector_pulse:ball_device_ejector_pulse:eject_coil = "c_trough_ejct"'),
    ("event_space", ("    tags: trough, drain, home\n", "    tags: trough, drain, home\n    eject_all_events: ball started\n"),
     'Cannot handle events with spaces in the event name, please remedy "ball started"'),
    ("time", ("    tags: trough, drain, home\n", "    tags: trough, drain, home\n    eject_timeouts: 2 secs\n"),
     "Cannot convert value to ms."),
    ("bool", ("    tags: start\n", "    tags: start\n    ignore_during_ball_search: maybe\n"),
     "Cannot convert value to boolean."),
    ("bool_full", ("    tags: start\n", "    tags: start\n    ignore_during_ball_search: maybe\n"),
     'Config File Error in ConfigValidator: Config validation error: Entry switches:s_start:ignore_during_ball_search = '
     '"maybe" is not valid. Cannot convert value to boolean. Error Code: CFE-ConfigValidator-13'),
    ("empty_item", ("ball_switches: s_trough1, s_trough2, s_trough3", "ball_switches: s_trough1, , s_trough3"),
     "List contains an empty element."),
    ("number", ("  s_trough1:\n    number:\n", "  s_trough1:\n    tags: x\n"),
     'Required setting "number:" is missing from section "switches:s_trough1:" in your config.'),
    ("no_eject", ("    eject_coil: c_trough_eject\n", ""),
     'Configuration error in bd_trough ball device. Device needs an eject_coil, a hold_coil, or "mechanical_eject: '
     'True"'),
]


def squash(text):
    return " ".join(str(text).split())


class TestDebuggingMessages(unittest.TestCase):
    """build/debugging.md: each mistake stops MPF at startup with the message quoted on the page."""

    def boot_error(self, config):
        class Boot(GuideMachine):
            def runTest(self):
                pass
        Boot.machine_dir = make_machine(config)
        test = Boot("runTest")
        try:
            test.setUp()
            test.advance_time_and_run(1)
        except BaseException as e:  # noqa: BLE001
            parts, cause = [str(e)], e.__cause__ or e.__context__
            while cause is not None:
                parts.append(str(cause))
                cause = cause.__cause__ or cause.__context__
            return squash(" ".join(parts))
        finally:
            try:
                test.tearDown()
            except BaseException:  # noqa: BLE001
                pass
            shutil.rmtree(Boot.machine_dir, ignore_errors=True)
        return None

    def test_messages(self):
        page = squash((CONTENT / DEBUG_PAGE).read_text(encoding="utf-8"))
        base = full_config(FIRST)
        for name, (old, new), quoted in MISTAKES:
            with self.subTest(name):
                self.assertIn(old, base)
                self.assertIn(squash(quoted), page, "page does not quote this message")
                message = self.boot_error(base.replace(old, new, 1))
                self.assertIsNotNone(message, "MPF started without an error")
                self.assertIn(squash(quoted), message)


class TestDebuggingLateErrors(GuideMachine):
    """build/debugging.md: missing default_source_device passes startup and fails when a game starts."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config(FIRST).replace("    default_source_device: bd_trough\n", ""))

    def test_fails_at_game_start(self):
        quoted = "Missing a source device to request a ball. Did you define a default_source_device in your playfield?"
        self.assertIn(quoted, (CONTENT / DEBUG_PAGE).read_text(encoding="utf-8"))
        self.advance_time_and_run(1)
        self.assertModeRunning("attract")
        with self.assertRaisesRegex(Exception, re.escape(quoted)):
            self.hit_and_release_switch("s_start")
            self.advance_time_and_run(1)


class TestDebuggingEmptyTrough(GuideMachine):
    """build/debugging.md: with the trough empty, start is refused (message checked against the source)."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config(FIRST).replace(
            "virtual_platform_start_active_switches: s_trough1, s_trough2, s_trough3\n", ""))

    def test_refused(self):
        source = (Path(__file__).resolve().parents[2] / "mpf" / "core" / "ball_controller.py").read_text(
            encoding="utf-8")
        self.assertIn("BallController denies game start. Not enough \"\n                             \"balls.", source)
        self.assertIn("BallController denies game start. Balls are not \"\n                             \"in their "
                      "home positions.", source)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.ball_devices["bd_trough"].balls)
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(1)
        self.assertIsNone(self.machine.game)


class TestEventLowercaseTrue(GuideMachine):
    """build/events.md: lower-case true boots, then fails when the condition is first evaluated."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = make_machine(full_config(EVENTS_PAGE).replace("{ball==2}", "{true}"))

    def test_error_at_first_evaluation(self):
        self.advance_time_and_run(1)
        self.assertModeRunning("attract")
        with self.assertRaisesRegex(Exception, "Placeholder use Python syntax"):
            self.start_game()
            self.advance_time_and_run(1)


KICKBACK_PAGE = "examples/ball-in-play/ball-save-and-kickback.md"


class KickbackMachine(ExampleMachine):
    WATCH = ("ball_started", "ball_save_start_save_saving_ball", "ball_save_start_save_timer_start",
             "kickback_left_kickback_fired", "kickback_targets_lit_complete")

    def begin(self):
        self.log = []
        for name in self.WATCH:
            self.machine.events.add_handler(
                name, lambda name=name, **kwargs: self.log.append((name, kwargs.get("early_save"))), priority=-9)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(3)

    def state(self):
        game = self.machine.game
        events = [n for n, a in self.log]
        del self.log[:]
        return (game.player.score, game.player.ball, self.machine.kickbacks["left_kickback"]._enabled, events)

    def targets(self, *numbers):
        for number in numbers:
            self.hit("s_kick_target_%d" % number)


class TestExampleKickback(KickbackMachine):
    """examples/ball-in-play/ball-save-and-kickback.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(KICKBACK_PAGE)

    def test_walkthrough(self):
        self.begin()
        self.assertEqual((0, 1, False, ["ball_started", "ball_save_start_save_timer_start"]), self.state())
        self.targets(1, 1, 2)
        lit = [s.state_name for s in self.machine.shot_groups["kickback_targets"].config["shots"]]
        self.assertEqual(["lit", "lit", "unlit"], lit)
        self.assertEqual((3000, 1, False, []), self.state())
        self.targets(3)
        self.assertEqual((29000, 1, True, ["kickback_targets_lit_complete"]), self.state())
        self.assertEqual(["unlit"] * 3,
                         [s.state_name for s in self.machine.shot_groups["kickback_targets"].config["shots"]])
        self.hit("s_left_outlane")
        self.advance_time_and_run(1)
        self.assertEqual((34000, 1, False, ["kickback_left_kickback_fired"]), self.state())
        self.hit("s_left_outlane")
        self.assertEqual((39000, 1, False, []), self.state())
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertEqual((39000, 1, False, ["ball_save_start_save_saving_ball"]), self.state())
        self.advance_time_and_run(20)
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertEqual((39000, 2, False, ["ball_started", "ball_save_start_save_timer_start"]), self.state())
        self.hit("s_right_outlane")
        self.assertIn(("ball_save_start_save_saving_ball", True), self.log)
        self.assertEqual((44000, 2, False, ["ball_save_start_save_saving_ball"]), self.state())
        self.advance_time_and_run(3)
        self.assertEqual((2, 1), (self.machine.playfield.balls, self.machine.game.balls_in_play))
        self.drain_one_ball()
        self.advance_time_and_run(3)
        self.assertEqual((44000, 2, False, []), self.state())
        self.targets(1, 2, 3)
        self.assertEqual((72000, 2, True, ["kickback_targets_lit_complete"]), self.state())
        self.advance_time_and_run(20)
        self.drain_one_ball()
        self.advance_time_and_run(3)
        self.assertEqual((72000, 3, False, ["ball_started", "ball_save_start_save_timer_start"]), self.state())
        self.hit("s_left_outlane")
        self.assertEqual((77000, 3, False, []), self.state())


class TestExampleKickbackBothOutlanesEarly(KickbackMachine):
    """The page's note: early-saving the kickback's outlane too puts a second ball on the playfield."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(KICKBACK_PAGE, file_changes={
            "modes/base/config/base.yaml": lambda t: t.replace(
                "early_ball_save_events: s_right_outlane_active\n",
                "early_ball_save_events: s_left_outlane_active, s_right_outlane_active\n", 1)})

    def test_two_balls(self):
        self.begin()
        self.targets(1, 2, 3)
        self.state()
        self.hit("s_left_outlane")
        self.advance_time_and_run(3)
        events = self.state()[3]
        self.assertIn("kickback_left_kickback_fired", events)
        self.assertIn("ball_save_start_save_saving_ball", events)
        self.assertEqual((2, 1), (self.machine.playfield.balls, self.machine.game.balls_in_play))


class TestExampleKickbackPlayfieldActiveTag(GuideMachine):
    """The page's note: a kickback switch with the playfield_active tag stops MPF with CFE-kickback-1."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(KICKBACK_PAGE, config_change=lambda c: c.replace(
            "  s_left_outlane:\n    number:\n", "  s_left_outlane:\n    number:\n    tags: playfield_active\n", 1))

    @expect_startup_error()
    def test_refused(self):
        self.assertRegex(str(self.startup_error), "CFE-kickback-1")


DROPS_PAGE = "examples/ball-in-play/drop-targets-extra-ball.md"


class DropsMachine(ExampleMachine):
    WATCH = ("ball_started", "drop_target_bank_main_bank_down", "drop_target_bank_main_bank_up",
             "drop_target_bank_main_bank_mixed", "light_bank_extra_ball", "extra_ball_group_main_lit_awarded",
             "extra_ball_group_main_lit", "extra_ball_awarded")

    def begin(self):
        self.log = []
        for name in self.WATCH:
            self.machine.events.add_handler(
                name, lambda name=name, **kwargs: self.log.append((name, kwargs.get("is_extra_ball"))), priority=-9)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(3)
        del self.log[:]

    def drop(self, *names):
        for name in names:
            self.hit_switch_and_run("s_dt_" + name, .1)

    def clear(self):
        self.drop("left", "center", "right")
        self.advance_time_and_run(2)

    def drain(self):
        self.drain_all_balls()
        self.advance_time_and_run(3)

    def state(self):
        player = self.machine.game.player
        events = [n for n, a in self.log]
        del self.log[:]
        return player.score, player.ball, player.bank_value, events


class TestExampleDropTargets(DropsMachine):
    """examples/ball-in-play/drop-targets-extra-ball.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(DROPS_PAGE)

    def test_walkthrough(self):
        self.begin()
        bank = self.machine.drop_target_banks["main_bank"]
        self.drop("left", "center")
        self.assertEqual((1000, 1, 5000, ["drop_target_bank_main_bank_mixed"] * 2), self.state())
        self.drop("right")
        self.assertEqual((6500, 1, 10000, ["drop_target_bank_main_bank_down"]), self.state())
        self.assertEqual(3, bank.down)
        self.advance_time_and_run(2)
        self.assertEqual((6500, 1, 10000, ["drop_target_bank_main_bank_up"]), self.state())
        self.assertEqual(0, bank.down)
        self.clear()
        self.assertEqual((18000, 1, 15000), self.state()[:3])
        self.drop("left")
        self.drain()
        self.assertEqual((18500, 2, 15000, ["drop_target_bank_main_bank_mixed", "ball_started",
                                            "drop_target_bank_main_bank_up"]), self.state())
        self.assertEqual(0, bank.down)
        self.hit("s_scoop")
        self.assertEqual((18500, 2, 15000, []), self.state())
        self.clear()
        score, ball, value, events = self.state()
        self.assertEqual((35000, 2, 20000), (score, ball, value))
        self.assertEqual(["light_bank_extra_ball", "extra_ball_group_main_lit_awarded", "extra_ball_group_main_lit"],
                         [e for e in events if "extra" in e])
        self.drain()
        self.assertEqual((35000, 3, 20000, ["ball_started", "extra_ball_group_main_lit"]), self.state())
        self.hit("s_scoop")
        self.assertEqual((35000, 3, 20000, ["extra_ball_awarded"]), self.state())
        self.assertEqual(1, self.machine.game.player.extra_balls)
        self.drain()
        self.assertIn(("ball_started", True), self.log)
        self.assertEqual((35000, 3, 20000, ["ball_started"]), self.state())
        self.clear()
        score, ball, value, events = self.state()
        self.assertEqual((56500, 3, 25000), (score, ball, value))
        self.assertEqual([], [e for e in events if "extra" in e])


class TestExampleDropTargetsValueOnUp(DropsMachine):
    """The page's note: raising the value on _up also raises it when the bank resets at the start of a ball."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(DROPS_PAGE, file_changes={
            "modes/base/config/base.yaml": lambda t: t.replace(
                "    score: current_player.bank_value\n    bank_value: 5000\n",
                "    score: current_player.bank_value\n  drop_target_bank_main_bank_up:\n    bank_value: 5000\n", 1)})

    def test_raised_without_a_clear(self):
        self.begin()
        self.clear()
        self.clear()
        self.assertEqual(15000, self.machine.game.player.bank_value)
        self.drop("left")
        self.drain()
        self.assertEqual(20000, self.machine.game.player.bank_value)


class TestExampleDropTargetPlayfieldActiveTag(GuideMachine):
    """The page: a drop target switch with the playfield_active tag stops MPF with CFE-drop_target-1."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(DROPS_PAGE, config_change=lambda c: c.replace(
            "    tags: drop_target\n", "    tags: drop_target, playfield_active\n", 1))

    @expect_startup_error()
    def test_refused(self):
        self.assertRegex(str(self.startup_error), "CFE-drop_target-1")


COMBOS_PAGE = "examples/scoring/combos.md"


class TestExampleCombos(ExampleMachine):
    """examples/scoring/combos.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(COMBOS_PAGE)

    def state(self):
        player = self.machine.game.player
        events = list(self.log)
        del self.log[:]
        return player.score, player.vars.get("combo_count"), events

    def test_walkthrough(self):
        self.log = []
        for name in ("mode_combo_started", "timer_combo_window_complete", "mode_combo_stopped"):
            self.machine.events.add_handler(name, lambda name=name, **kwargs: self.log.append(name), priority=-9)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(3)
        self.hit("s_left_ramp")
        self.assertEqual((1000, 0, ["mode_combo_started"]), self.state())
        self.advance_time_and_run(2)
        self.hit("s_right_ramp")
        self.assertEqual((12000, 1, []), self.state())
        self.advance_time_and_run(3)
        self.hit("s_orbit")
        self.assertEqual((33000, 2, []), self.state())
        self.advance_time_and_run(1)
        self.hit("s_target")
        self.assertEqual((33100, 2, []), self.state())
        self.advance_time_and_run(2)
        self.hit("s_left_ramp")
        self.assertEqual((64100, 3, []), self.state())
        self.advance_time_and_run(3.8)  # 3.9 s after the shot: still open; 4.3 s: closed
        self.assertModeRunning("combo")
        self.advance_time_and_run(.4)
        self.assertModeNotRunning("combo")
        self.assertEqual((64100, 3, ["timer_combo_window_complete", "mode_combo_stopped"]), self.state())
        self.advance_time_and_run(1)
        self.hit("s_right_ramp")
        self.assertEqual((65100, 0, ["mode_combo_started"]), self.state())
        self.advance_time_and_run(1)
        self.hit("s_right_ramp")
        self.assertEqual((76100, 1, []), self.state())


class TestExampleCombosStartEventInVariablePlayer(ExampleMachine):
    """The page: a variable_player entry on the mode's own start event stops MPF at the first major shot."""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(COMBOS_PAGE, file_changes={
            "modes/combo/config/combo.yaml": lambda t: t.replace(
                "  sw_major_shot_active:\n    combo_count: 1\n", "  sw_major_shot:\n    combo_count: 1\n", 1)})

    def test_refused(self):
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(3)
        message = ('combo mode\'s variable_player: section contains a "sw_major_shot:" event which is also in the '
                   'start_events: for the combo mode. Change the variable_player: sw_major_shot: event name to '
                   '"mode_combo_started:"')
        self.assertIn(message, (CONTENT / COMBOS_PAGE).read_text(encoding="utf-8"))
        with self.assertRaises(Exception) as caught:
            self.hit("s_left_ramp")
        self.assertIn(message, str(caught.exception))


HURRY_PAGE = "examples/scoring/hurry-up.md"


class TestExampleHurryUp(ExampleMachine):
    """examples/scoring/hurry-up.md"""

    @classmethod
    def setUpClass(cls):
        cls.machine_dir = example_machine(HURRY_PAGE)

    def state(self):
        player = self.machine.game.player
        events = list(self.log)
        del self.log[:]
        return player.score, player.vars.get("hurry_up_value"), events

    def test_walkthrough(self):
        self.log = []
        ticks = []
        self.machine.events.add_handler("timer_hurry_up_clock_tick",
                                        lambda **kwargs: ticks.append(kwargs["ticks"]), priority=-9)
        for name in ("mode_hurry_up_started", "mode_hurry_up_stopped", "timer_hurry_up_clock_complete",
                     "hurry_up_collected"):
            self.machine.events.add_handler(name, lambda name=name, **kwargs: self.log.append(name), priority=-9)
        self.advance_time_and_run(1)
        self.start_game()
        self.advance_time_and_run(3)
        self.hit("s_scoop")
        self.assertEqual((500, 200000, ["mode_hurry_up_started"]), self.state())
        self.assertEqual([0], ticks)  # the tick posted when the timer starts
        self.advance_time_and_run(2.3)
        self.assertEqual((500, 180000, []), self.state())
        self.hit("s_scoop")
        self.assertEqual((1000, 175000, []), self.state())
        self.advance_time_and_run(1.5)
        self.hit("s_right_ramp")
        self.assertEqual((162000, 160000, ["hurry_up_collected", "mode_hurry_up_stopped"]), self.state())
        self.advance_time_and_run(1)
        self.hit("s_right_ramp")
        self.assertEqual((163000, 160000, []), self.state())
        del ticks[:]
        self.hit("s_scoop")
        self.assertEqual((163500, 200000, ["mode_hurry_up_started"]), self.state())
        self.advance_time_and_run(14.7)
        self.assertEqual((163500, 55000, []), self.state())
        self.advance_time_and_run(.5)
        self.assertEqual((163500, 55000, ["timer_hurry_up_clock_complete", "mode_hurry_up_stopped"]), self.state())
        self.assertEqual(list(range(0, 30)), ticks)  # no tick for step 30
        self.hit("s_right_ramp")
        self.assertEqual((164500, 55000, []), self.state())
        self.hit("s_scoop")
        self.advance_time_and_run(3)
        self.assertEqual((165000, 170000, ["mode_hurry_up_started"]), self.state())
        self.drain_all_balls()
        self.advance_time_and_run(3)
        self.assertEqual(2, self.machine.game.player.ball)
        self.assertEqual((165000, 165000, ["mode_hurry_up_stopped"]), self.state())
        self.hit("s_right_ramp")
        self.assertEqual((166000, 165000, []), self.state())


if __name__ == "__main__":
    unittest.main()
