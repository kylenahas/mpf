"""Run the configs from the guide pages on MPF and check the behaviour the pages describe.

Each test builds a machine folder the way a reader would (`mpf init`, then the page's complete config), so the page and
the test cannot drift apart: the config is read from the page itself.

Run from the repository root:
  venv/Scripts/python -I -m unittest discover -s docs-site/verify -v
"""
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
    """The last block on the page that is a whole config file (starts with #config_version)."""
    return [b for b in yaml_blocks(page) if b.startswith("#config_version")][-1]


def make_machine(text, replace_devices=None):
    """`mpf init` a temp folder and write `text` as config/config.yaml.

    replace_devices: a YAML snippet like `ball_devices: {bd_plunger: {...}}`; each device in it replaces the device of the
    same name in the config (used for the variants shown on a page).
    """
    path = tempfile.mkdtemp(prefix="mpf_docs_")
    InitCommand(["init"], path)
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


if __name__ == "__main__":
    unittest.main()
