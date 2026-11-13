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
        self.assertEqual({"modes/base/config/base.yaml", "shows/flash_light.yaml"},
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


if __name__ == "__main__":
    unittest.main()
