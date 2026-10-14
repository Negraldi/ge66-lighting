"""JSON profiles: schema checks and packet generation (no hardware)."""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ge66_lighting import effect, hid, keyboard, lightbar, model, profile  # noqa: E402

RED = (255, 0, 0)


def first_bytes(packets):
    return [p.data[0] for p in packets]


class EffectObject(unittest.TestCase):
    def test_rainbow_palette_wave(self):
        fx = profile.effect_from_dict({"kind": "colorshift", "colors": "rainbow", "speed": 198,
                                       "direction": "radial", "invert": True, "focal": [585, 0], "scale": 78})
        self.assertEqual(fx.colors, [(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)])
        self.assertEqual((fx.has_direction, fx.direction_type, fx.direction_inverted), (True, effect.RADIAL, True))
        self.assertEqual((fx.focal_x, fx.focal_y, fx.speed, fx.scale), (585, 0, 198, 78))
        self.assertEqual(fx.positions, [0, 17, 34, 51, 68, 85])

    def test_color_list_and_positions(self):
        fx = profile.effect_from_dict({"kind": "breathe", "colors": ["#ff0000", "00ff00"], "positions": [0, 40]})
        self.assertEqual((fx.kind, fx.colors, fx.positions), (effect.BREATHE, [RED, (0, 255, 0)], [0, 40]))
        self.assertFalse(fx.has_direction)

    def test_rejects_unknown_fields_and_values(self):
        for bad in ({"kind": "spin", "colors": "rainbow"}, {"kind": "breathe"},
                    {"kind": "breathe", "colors": "rainbow", "colour": 1},
                    {"kind": "breathe", "colors": "rainbow", "direction": "diagonal"},
                    {"kind": "breathe", "colors": ["nope"]}, {"kind": "breathe", "colors": "rainbow", "focal": [1]}):
            with self.assertRaises(profile.ProfileError, msg=bad):
                profile.effect_from_dict(bad)


class LightbarSection(unittest.TestCase):
    def test_static_equals_sequence(self):
        packets = profile.build_lightbar({"lighting": {"type": "static", "color": "#ff0000"}})
        self.assertEqual(packets, lightbar.static_sequence(RED))

    def test_static_with_zone_overrides(self):
        packets = profile.build_lightbar({"lighting": {"type": "static", "color": "000000",
                                                       "set": {"left": "0000ff", "0": "ff0000"}}})
        table = packets[0].data
        self.assertEqual(table[4 + 12 * 5:4 + 12 * 5 + 3], bytes([0, 0, 255]))  # zone 5 is on the left
        self.assertEqual(table[4:7], bytes(RED))  # explicit zone 0 wins over the group
        self.assertEqual(table[4 + 12 * 20:4 + 12 * 20 + 3], bytes(3))

    def test_settings_come_first(self):
        packets = profile.build_lightbar({"color_scale": "ffff99", "brightness": 128,
                                          "lighting": {"type": "off"}})
        self.assertEqual(first_bytes(packets)[:2], [0x51, 0x0C])
        self.assertEqual(packets[1].data[2], 128)

    def test_effect_equals_sequence(self):
        spec = {"kind": "colorshift", "colors": "rainbow", "speed": 198, "direction": "horizontal", "scale": 30}
        packets = profile.build_lightbar({"lighting": {"type": "effect", "effect": spec, "slot": 2,
                                                       "zones": "0-9", "base": "000010"}})
        expected = lightbar.effect_sequence(profile.effect_from_dict(spec), slot=2, zones=list(range(10)),
                                            base=(0, 0, 16))
        self.assertEqual(packets, expected)

    def test_direct_and_fill_and_disable(self):
        self.assertEqual(profile.build_lightbar({"lighting": {"type": "direct", "color": "ff0000"}}),
                         [lightbar.solid(RED)])
        self.assertEqual(profile.build_lightbar({"lighting": {"type": "fill", "color": "ff0000"}}),
                         [lightbar.write_all(RED)])
        self.assertEqual(profile.build_lightbar({"lighting": {"type": "disable"}}), lightbar.disable_sequence())

    def test_persist_flag(self):
        section = {"lighting": {"type": "static", "color": "ff0000"}}
        self.assertNotIn(0x09, first_bytes(profile.build_lightbar(section)))
        self.assertIn(0x09, first_bytes(profile.build_lightbar(section, persist=True)))

    def test_rejects_typos(self):
        for bad in ({"lighting": {"type": "stati", "color": "ff0000"}}, {"lightning": {}},
                    {"lighting": {"type": "static"}}, {"brightness": 300},
                    {"lighting": {"type": "static", "color": "ff0000", "colour": 1}},
                    {"lighting": {"type": "static", "color": "ff0000", "set": {"35": "ff0000"}}}):
            with self.assertRaises(profile.ProfileError, msg=bad):
                profile.build_lightbar(bad)


class KeyboardSection(unittest.TestCase):
    def test_static_with_key_overrides(self):
        packets = profile.build_keyboard({"lighting": {"type": "static", "color": "000000", "set": {"esc": "ff0000"}}})
        self.assertEqual(packets, keyboard.static_sequence({41: RED}, base=(0, 0, 0)))

    def test_static_default_footer_and_override(self):
        self.assertEqual(profile.build_keyboard({"lighting": {"type": "off"}})[0].data[-2:], b"\x08\x39")
        packets = profile.build_keyboard({"footer": "none", "lighting": {"type": "off"}})
        self.assertEqual(packets[0].data[-2:], b"\0\0")
        packets = profile.build_keyboard({"footer": "0855", "lighting": {"type": "off"}})
        self.assertEqual(packets[0].data[-2:], b"\x08\x55")

    def test_effect_with_keys(self):
        spec = {"kind": "breathe", "colors": ["ff0000", "0000ff"], "speed": 300}
        packets = profile.build_keyboard({"lighting": {"type": "effect", "effect": spec, "keys": "w,a,s,d"}})
        expected = keyboard.effect_sequence(profile.effect_from_dict(spec), keys=[26, 4, 22, 7])
        self.assertEqual(packets, expected)

    def test_reactive(self):
        packets = profile.build_keyboard({"lighting": {"type": "reactive", "color": "000000",
                                                       "react_color": "ffffff", "react_time": 200}})
        self.assertEqual(packets, keyboard.reactive_sequence((0, 0, 0), (255, 255, 255), react_time=200))

    def test_direct_enters_stream_mode_first(self):
        packets = profile.build_keyboard({"lighting": {"type": "direct", "color": "ff0000"}})
        self.assertEqual(first_bytes(packets), [0x0E] * 4 + [0x0D, 0x0C])
        self.assertEqual(packets[-1].data[2], 84)  # every physical key

    def test_direct_with_key_colors(self):
        packets = profile.build_keyboard({"lighting": {"type": "direct", "set": {"esc": "ff0000"}}})
        self.assertEqual(packets[-1].data[:8], bytes([0x0C, 0, 1, 0, 41, 255, 0, 0]))

    def test_color_scale(self):
        packets = profile.build_keyboard({"color_scale": [140, 204, 153]})
        self.assertEqual(packets, [keyboard.color_scale()])

    def test_keyboard_has_no_brightness_command(self):
        with self.assertRaises(profile.ProfileError):
            profile.build_keyboard({"brightness": 10})


class WholeProfile(unittest.TestCase):
    def test_apply_profile_routes_sections_to_devices(self):
        data = {"version": 1, "lightbar": {"lighting": {"type": "off"}}, "keyboard": {"lighting": {"type": "off"}}}
        bar, board = hid.DryRunTransport(), hid.DryRunTransport()
        profile.apply_profile(data, bar_transport=lambda: bar, keyboard_transport=lambda: board)
        self.assertEqual(first_bytes(bar.sent), [0x0E, 0x0D])
        self.assertEqual(first_bytes(board.sent), [0x0E] * 4 + [0x0D])

    def test_missing_section_does_not_open_the_device(self):
        def forbidden():
            raise AssertionError("device opened")

        bar = hid.DryRunTransport()
        profile.apply_profile({"version": 1, "lightbar": {"lighting": {"type": "off"}}},
                              bar_transport=lambda: bar, keyboard_transport=forbidden)
        self.assertTrue(bar.sent)

    def test_persist_at_top_level_and_per_device(self):
        data = {"version": 1, "persist": True,
                "lightbar": {"lighting": {"type": "off"}},
                "keyboard": {"persist": False, "lighting": {"type": "off"}}}
        bar, board = hid.DryRunTransport(), hid.DryRunTransport()
        profile.apply_profile(data, bar_transport=lambda: bar, keyboard_transport=lambda: board)
        self.assertIn(0x09, first_bytes(bar.sent))
        self.assertNotIn(0x09, first_bytes(board.sent))

    def test_version_and_unknown_top_level_keys(self):
        with self.assertRaises(profile.ProfileError):
            profile.validate({"version": 2})
        with self.assertRaises(profile.ProfileError):
            profile.validate({"version": 1, "keybord": {}})
        with self.assertRaises(profile.ProfileError):
            profile.validate({"lightbar": {}})  # version is required

    def test_load_profile_reports_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "p.json"
            path.write_text("{nope")
            with self.assertRaises(profile.ProfileError):
                profile.load_profile(str(path))
            with self.assertRaises(profile.ProfileError):
                profile.load_profile(str(path) + ".missing")

    def test_example_profile_is_valid_and_builds(self):
        data = profile.load_profile(str(ROOT / "contrib" / "profile.example.json"))
        self.assertEqual(data["version"], 1)
        self.assertTrue(profile.build_lightbar(data["lightbar"]))
        self.assertTrue(profile.build_keyboard(data["keyboard"]))
        self.assertFalse(data.get("persist", False))

    def test_every_documented_example_in_the_docs_loads(self):
        # docs/profile-format.md embeds its examples in ```json fences
        text = (ROOT / "docs" / "profile-format.md").read_text()
        blocks = [part.split("```", 1)[0] for part in text.split("```json\n")[1:]]
        self.assertGreaterEqual(len(blocks), 3)
        for block in blocks:
            data = json.loads(block)
            profile.validate(data)
            if "lightbar" in data:
                profile.build_lightbar(data["lightbar"])
            if "keyboard" in data:
                profile.build_keyboard(data["keyboard"])

    def test_systemd_unit_applies_the_profile_without_persisting(self):
        unit = (ROOT / "contrib" / "ge66-light.service").read_text()
        self.assertIn("Type=oneshot", unit)
        self.assertIn("ge66-light apply", unit)
        self.assertIn("WantedBy=default.target", unit)
        exec_line = next(line for line in unit.splitlines() if line.startswith("ExecStart="))
        self.assertNotIn("--persist", exec_line)


if __name__ == "__main__":
    unittest.main()
