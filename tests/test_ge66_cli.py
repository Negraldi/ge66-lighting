"""CLI behavior. Every test runs with --dry-run or a refusal path; os.open is guarded so a
test that reached a /dev/hidraw node would fail instead of touching hardware."""
import contextlib
import io
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ge66_lighting import cli, hid  # noqa: E402


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


def lines(text):
    return [line for line in text.splitlines() if line.strip()]


class CliBase(unittest.TestCase):
    def setUp(self):
        guard = mock.patch("os.open", side_effect=AssertionError("tests must not open devices"))
        guard.start()
        self.addCleanup(guard.stop)


class Spec(unittest.TestCase):
    def test_parse_spec(self):
        self.assertEqual(cli.parse_spec("left=ff0000, 3=00ff00"), {"left": "ff0000", "3": "00ff00"})
        with self.assertRaises(ValueError):
            cli.parse_spec("left")

    def test_retry_waits_until_the_device_shows_up(self):
        calls, clock = [], [0.0]

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise hid.DeviceNotFound("not yet")
            return "ok"

        def sleep(seconds):
            clock[0] += seconds

        self.assertEqual(cli.retry(flaky, 10, interval=1, sleep=sleep, clock=lambda: clock[0]), "ok")
        self.assertEqual(len(calls), 3)

    def test_retry_gives_up(self):
        clock = [0.0]

        def never():
            raise hid.DeviceNotFound("nope")

        def sleep(seconds):
            clock[0] += seconds

        with self.assertRaises(hid.DeviceNotFound):
            cli.retry(never, 3, interval=1, sleep=sleep, clock=lambda: clock[0])


class Bar(CliBase):
    def test_static_prints_table_then_reset(self):
        code, out, _ = run("--dry-run", "bar", "static", "ff0000")
        self.assertEqual(code, 0)
        rows = lines(out)
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0].startswith("feature 524B  0e 00 23 00 ff 00 00"))
        self.assertTrue(rows[1].startswith("output   64B  0d 00 02"))

    def test_options_after_the_subcommand(self):
        code, out, _ = run("bar", "static", "ff0000", "--dry-run")
        self.assertEqual((code, len(lines(out))), (0, 2))

    def test_colorshift_wave(self):
        code, out, _ = run("--dry-run", "bar", "colorshift", "--colors", "rainbow", "--speed", "198",
                           "--direction", "radial", "--invert", "--focal", "585", "0", "--scale", "78")
        rows = lines(out)
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 4)  # slot, coordinates, table, reset
        self.assertIn("0b 00 00 00", rows[0])
        self.assertIn("0d 00 23 00", rows[1])

    def test_breathe_with_color_list_and_no_coordinates(self):
        code, out, _ = run("--dry-run", "bar", "breathe", "--colors", "ff0000", "0000ff", "--direction", "horizontal",
                           "--no-coordinates", "--zones", "left", "--slot", "4")
        self.assertEqual((code, len(lines(out))), (0, 3))

    def test_persist_is_opt_in(self):
        _, plain, _ = run("--dry-run", "bar", "static", "ff0000")
        _, saved, _ = run("--dry-run", "bar", "static", "ff0000", "--persist")
        self.assertNotIn("output   64B  09 ", plain)
        self.assertIn("output   64B  09 ", saved)

    def test_save_requires_persist(self):
        code, out, err = run("--dry-run", "bar", "save")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--persist", err)
        code, out, _ = run("--dry-run", "bar", "save", "--persist")
        self.assertEqual((code, len(lines(out))), (0, 1))

    def test_simple_commands(self):
        for argv, prefix in ((("brightness", "255"), "0c 00 ff"), (("color-scale",), "51 00 ff ff 99"),
                             (("color-scale", "ff0000"), "51 00 ff 00 00"), (("reset",), "0d 00 02"),
                             (("restart",), "0d 00 00"), (("reset-device",), "f1 00"),
                             (("fill", "010203"), "50 00 01 02 03"), (("lid", "close"), "0c 00"),
                             (("lid", "open"), "f1 00"), (("init",), "51 00 ff ff 99")):
            code, out, _ = run("--dry-run", "bar", *argv)
            self.assertEqual(code, 0, argv)
            self.assertIn(prefix, lines(out)[0], argv)

    def test_direct_commands(self):
        code, out, _ = run("--dry-run", "bar", "solid", "ff0000")
        self.assertIn("feature 524B  0c 00 23 00 00 ff 00 00", lines(out)[0])
        code, out, _ = run("--dry-run", "bar", "paint", "0-1=00ff00")
        self.assertIn("0c 00 02 00 00 00 ff 00 01 00 ff", lines(out)[0])

    def test_off_and_disable(self):
        self.assertEqual(len(lines(run("--dry-run", "bar", "off")[1])), 2)
        self.assertEqual(len(lines(run("--dry-run", "bar", "disable")[1])), 3)

    def test_coordinates(self):
        code, out, _ = run("--dry-run", "bar", "coordinates", "--spacing", "10")
        self.assertEqual(code, 0)
        self.assertIn("0d 00 23 00 00 00 00 00 0a 00 00 00", lines(out)[0])

    def test_info_without_reply(self):
        code, out, _ = run("--dry-run", "bar", "info")
        self.assertEqual(code, 0)
        self.assertIn("no reply", out)

    def test_bad_arguments_exit_2(self):
        for argv in (("bar", "brightness", "300"), ("bar", "static", "nothex"), ("bar", "colorshift"),
                     ("bar", "paint", "99=ff0000"), ("bar", "static", "ff0000", "--set", "oops")):
            code, _, err = run("--dry-run", *argv)
            self.assertEqual(code, 2, argv)
            self.assertTrue(err, argv)


class Keyboard(CliBase):
    def test_static_prints_four_tables_and_reset(self):
        code, out, _ = run("--dry-run", "keyboard", "static", "ff0000")
        rows = lines(out)
        self.assertEqual((code, len(rows)), (0, 5))
        self.assertTrue(rows[0].startswith("feature 524B  0e 00 2a 00 ff 00 00"))
        self.assertTrue(rows[-1].startswith("output   64B  0d 00 02"))
        self.assertTrue(rows[0].endswith("08 39"))

    def test_footer_option(self):
        _, out, _ = run("--dry-run", "keyboard", "static", "ff0000", "--footer", "0855")
        self.assertTrue(lines(out)[0].endswith("08 55"))

    def test_solid_enters_stream_mode_then_writes(self):
        code, out, _ = run("--dry-run", "keyboard", "solid", "00ff00")
        rows = lines(out)
        self.assertEqual((code, len(rows)), (0, 6))
        self.assertTrue(rows[-1].startswith("feature 524B  0c 00 54 00"))  # 84 keys

    def test_paint(self):
        code, out, _ = run("--dry-run", "keyboard", "paint", "esc=ff0000,f1-f2=0000ff")
        self.assertEqual(code, 0)
        self.assertIn("0c 00 03 00 29 ff 00 00 3a 00 00 ff 3b 00 00 ff", lines(out)[-1])

    def test_effects_and_reactive(self):
        code, out, _ = run("--dry-run", "keyboard", "colorshift", "--colors", "rainbow", "--direction", "horizontal",
                           "--keys", "letters")
        self.assertEqual((code, len(lines(out))), (0, 6))
        code, out, _ = run("--dry-run", "keyboard", "breathe", "--colors", "police")
        self.assertEqual((code, len(lines(out))), (0, 6))
        code, out, _ = run("--dry-run", "keyboard", "reactive", "100010", "--react-color", "ffffff",
                           "--react-time", "250", "--keys", "w,a,s,d")
        self.assertEqual((code, len(lines(out))), (0, 5))

    def test_off_fill_and_resets(self):
        self.assertEqual(len(lines(run("--dry-run", "keyboard", "off")[1])), 5)
        for argv, prefix in ((("fill", "ff0000"), "50 00 ff 00 00"), (("color-scale",), "51 00 8c cc 99"),
                             (("reset",), "0d 00 02"), (("restart",), "08 00"), (("restart-active",), "0d 00 00"),
                             (("lighting-reset",), "40 00")):
            code, out, _ = run("--dry-run", "keyboard", *argv)
            self.assertEqual(code, 0, argv)
            self.assertIn(prefix, lines(out)[0], argv)

    def test_save_requires_persist(self):
        self.assertEqual(run("--dry-run", "keyboard", "save")[0], 2)
        self.assertEqual(run("--dry-run", "keyboard", "save", "--persist")[0], 0)

    def test_layout_is_experimental(self):
        code, _, err = run("--dry-run", "keyboard", "layout", "0")
        self.assertEqual(code, 2)
        self.assertIn("--experimental", err)
        code, out, _ = run("--dry-run", "keyboard", "layout", "3", "--experimental")
        self.assertIn("06 00 03", lines(out)[0])

    def test_list_keys(self):
        code, out, _ = run("keyboard", "list-keys")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"esc\s+0x29\s+physical")
        self.assertRegex(out, r"jp-yen\s+0x89\s+absent")

    def test_info_without_reply(self):
        self.assertIn("no reply", run("--dry-run", "keyboard", "info")[1])

    def test_bad_arguments_exit_2(self):
        for argv in (("keyboard", "static", "zzzzzz"), ("keyboard", "paint", "nokey=ff0000"),
                     ("keyboard", "reactive", "ff0000"), ("keyboard", "breathe", "--colors", "nope"),
                     ("keyboard", "colorshift", "--colors", "rainbow", "--keys", "esc,nokey")):
            code, _, err = run("--dry-run", *argv)
            self.assertEqual(code, 2, argv)


class ApplyCommand(CliBase):
    def test_apply_example_profile_dry_run(self):
        code, out, _ = run("--dry-run", "apply", str(ROOT / "contrib" / "profile.example.json"))
        self.assertEqual(code, 0)
        rows = lines(out)
        # bar: scale, brightness, slot, coordinates, table, reset; keyboard: scale, four tables, reset
        self.assertEqual(len(rows), 6 + 6)
        self.assertTrue(any("0b 00 00 00" in row for row in rows))

    def test_apply_rejects_bad_profile(self):
        code, out, err = run("--dry-run", "apply", str(ROOT / "docs" / "does-not-exist.json"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("cannot read", err)


class EntryScript(unittest.TestCase):
    def test_script_runs_dry(self):
        result = subprocess.run([sys.executable, str(ROOT / "ge66-light"), "--dry-run", "bar", "static", "00ff00"],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(lines(result.stdout)), 2)

    def test_script_is_executable(self):
        self.assertTrue(os.access(ROOT / "ge66-light", os.X_OK))


if __name__ == "__main__":
    unittest.main()
