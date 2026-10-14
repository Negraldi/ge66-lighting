"""Shared lighting model: element info, element tables, effect struct and serialization.

Expected bytes come from the SteelSeries GG 121.0.0 specifications
(common_lighting, fancy_lighting_engine, ss-alc-base, ss-klc-base) and from the
USB captures attached to OpenRGB issues #2642 and #3961 (see tests/ge66_golden.py).
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ge66_golden import CAPTURES  # noqa: E402
from ge66_lighting import effect, model  # noqa: E402


def capture_payload(name: str, index: int) -> bytes:
    kind, size, hexdata = CAPTURES[name][index]
    return bytes.fromhex(hexdata).ljust(size, b"\0")


class Colors(unittest.TestCase):
    def test_parse_hex_forms(self):
        self.assertEqual(model.parse_color("#ff8000"), (255, 128, 0))
        self.assertEqual(model.parse_color("FF8000"), (255, 128, 0))
        self.assertEqual(model.parse_color("255,128,0"), (255, 128, 0))
        self.assertEqual(model.parse_color("red"), (255, 0, 0))

    def test_parse_rejects_garbage(self):
        for text in ("", "#12345", "256,0,0", "1,2", "nothex!"):
            with self.assertRaises(ValueError, msg=text):
                model.parse_color(text)


class ElementInfo(unittest.TestCase):
    def test_layout_is_init_react_effect_mask(self):
        info = model.ElementInfo(init=(1, 2, 3), react=(4, 5, 6), react_time=0x0102, effect_index=7, settings_mask=8)
        # common_lighting: initial(3) + reactive(3 + uint16) + effect_index + settings_mask = 10 bytes
        self.assertEqual(info.to_bytes(), bytes([1, 2, 3, 4, 5, 6, 0x02, 0x01, 7, 8]))

    def test_validation_follows_the_struct_ranges(self):
        with self.assertRaises(ValueError):
            model.ElementInfo(effect_index=0x12)
        with self.assertRaises(ValueError):
            model.ElementInfo(settings_mask=3)
        with self.assertRaises(ValueError):
            model.ElementInfo(react_time=2001)
        with self.assertRaises(ValueError):
            model.ElementInfo(init=(256, 0, 0))

    def test_all_spec_masks_are_accepted(self):
        for mask in (0, 1, 2, 4, 8, 16):
            model.ElementInfo(settings_mask=mask)

    def test_block_is_info_lockmask_id(self):
        block = model.ElementBlock(model.ElementInfo(init=(255, 0, 0), effect_index=1, settings_mask=1), ident=0x40)
        # Keyboard_Steady_RED capture, first element of the first table
        self.assertEqual(block.to_bytes(), bytes.fromhex("ff0000" "0000000000" "01" "01" "00" "40"))
        self.assertEqual(len(block.to_bytes()), 12)

    def test_block_roundtrip(self):
        raw = bytes.fromhex("ff0000" "0000000000" "01" "01" "00" "40")
        self.assertEqual(model.ElementBlock.from_bytes(raw).to_bytes(), raw)


class ElementTable(unittest.TestCase):
    def parse_blocks(self, payload: bytes):
        count = payload[2]
        return [model.ElementBlock.from_bytes(payload[4 + 12 * i:16 + 12 * i]) for i in range(count)]

    def test_matches_every_keyboard_capture_table(self):
        # 08 55 is the unexplained two-byte trailer of the vendor KLC feature reports
        for index in range(4):
            payload = capture_payload("keyboard_steady_red", index)
            blocks = self.parse_blocks(payload)
            self.assertEqual(model.element_table(blocks, footer=b"\x08\x55"), payload, f"table {index}")

    def test_matches_aurora_zone_tables(self):
        for name, index in (("aurora_steady_red", 2), ("aurora_colorshift_disco", 1), ("aurora_disable", 0)):
            payload = capture_payload(name, index)
            blocks = self.parse_blocks(payload)
            self.assertEqual(len(blocks), 30)
            self.assertEqual(model.element_table(blocks), payload, name)

    def test_header_and_padding(self):
        table = model.element_table([model.ElementBlock(model.ElementInfo(), ident=9)])
        self.assertEqual(len(table), 524)
        self.assertEqual(table[:4], bytes([0x0E, 0x00, 1, 0x00]))
        self.assertEqual(set(table[16:]), {0})

    def test_footer_goes_to_the_last_bytes(self):
        table = model.element_table([], footer=b"\x08\x39")
        self.assertEqual(table[-2:], b"\x08\x39")
        self.assertEqual(table[2], 0)

    def test_rejects_overflow(self):
        blocks = [model.ElementBlock(model.ElementInfo(), ident=i) for i in range(44)]
        with self.assertRaises(ValueError):
            model.element_table(blocks)


class Reports(unittest.TestCase):
    def test_direct_write_layout(self):
        report = model.direct_write([(3, 1, 2, 3), (9, 4, 5, 6)])
        self.assertEqual(len(report), 524)
        self.assertEqual(report[:12], bytes([0x0C, 0, 2, 0, 3, 1, 2, 3, 9, 4, 5, 6]))

    def test_direct_write_limits(self):
        with self.assertRaises(ValueError):
            model.direct_write([(0, 0, 0, 0)] * 131)
        with self.assertRaises(ValueError):
            model.direct_write([(256, 0, 0, 0)])

    def test_output_report_is_64_bytes(self):
        report = model.output_report(0x50, 0x00, 1, 2, 3)
        self.assertEqual(len(report), 64)
        self.assertEqual(report[:5], bytes([0x50, 0, 1, 2, 3]))
        self.assertEqual(set(report[5:]), {0})

    def test_output_report_rejects_oversize(self):
        with self.assertRaises(ValueError):
            model.output_report(*([1] * 65))


class EffectStruct(unittest.TestCase):
    def test_struct_is_69_bytes_with_spec_offsets(self):
        fx = effect.LightingEffect(
            kind=effect.COLORSHIFT, has_direction=True, direction_type=effect.RADIAL, direction_inverted=True,
            focal_x=0x0249, focal_y=0x0011, speed=198, scale=78,
            colors=[(255, 0, 0), (0, 255, 0)], positions=[0, 50])
        raw = fx.struct_bytes()
        self.assertEqual(len(raw), 69)
        self.assertEqual(raw[:4], bytes([1, 1, 2, 1]))
        self.assertEqual(raw[4:8], bytes([0x49, 0x02, 0x11, 0x00]))
        self.assertEqual(raw[8:12], bytes([198, 0, 78, 0]))
        self.assertEqual(raw[12], 2)
        self.assertEqual(raw[13:19], bytes([255, 0, 0, 0, 255, 0]))  # get-effect-colors offset 13
        self.assertEqual(raw[55:57], bytes([0, 50]))  # get-effect-position-byte offset 55

    def test_validation(self):
        with self.assertRaises(ValueError):
            effect.LightingEffect(kind=effect.COLORSHIFT, colors=[(0, 0, 0)] * 15)
        with self.assertRaises(ValueError):
            effect.LightingEffect(kind=effect.COLORSHIFT, colors=[(0, 0, 0)], positions=[101])
        with self.assertRaises(ValueError):
            effect.LightingEffect(kind=3)
        with self.assertRaises(ValueError):
            effect.LightingEffect(kind=effect.COLORSHIFT, colors=[(0, 0, 0)] * 2, positions=[50, 10])

    def test_default_positions_are_spread_evenly(self):
        fx = effect.LightingEffect(kind=effect.COLORSHIFT, colors=[(1, 1, 1)] * 6)
        self.assertEqual(fx.positions, [0, 17, 34, 51, 68, 85])  # same spacing as the vendor templates

    def test_disabled_effect_is_151_zero_bytes(self):
        self.assertEqual(effect.effect_bytes(effect.LightingEffect(kind=effect.DISABLED).struct_bytes()), bytes(151))

    def test_too_many_sections_for_the_fancy_engine(self):
        # the engine only computes 16 sections of 8 bytes
        fx = effect.LightingEffect(kind=effect.BREATHE, colors=[(255, 0, 0)] * 9, speed=500)
        with self.assertRaises(ValueError):
            fx.wire_bytes()


class EffectEngineGolden(unittest.TestCase):
    """The effect bytes must reproduce what the vendor software sent."""

    @staticmethod
    def slot_effect(payload: bytes) -> bytes:
        return payload[4:4 + 151]

    def test_colorshift_matches_aurora_disco_capture(self):
        fx = effect.LightingEffect(
            kind=effect.COLORSHIFT, has_direction=True, direction_type=effect.RADIAL, direction_inverted=True,
            focal_x=585, focal_y=0, speed=198, scale=78,
            colors=[(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)],
            positions=[0, 17, 34, 51, 68, 85])
        capture = capture_payload("aurora_colorshift_disco", 0)
        self.assertEqual(fx.wire_bytes(), self.slot_effect(capture))

    def test_breathe_matches_aurora_steady_capture(self):
        fx = effect.LightingEffect(
            kind=effect.BREATHE, has_direction=True, direction_type=effect.HORIZONTAL, direction_inverted=True,
            focal_x=596, focal_y=22, speed=198, scale=30,
            colors=[(255, 0, 0), (0, 255, 0), (0, 0, 255)], positions=[0, 33, 66])
        capture = capture_payload("aurora_steady_red", 4)
        self.assertEqual(fx.wire_bytes(), self.slot_effect(capture))

    def test_colorshift_with_hold_section_matches_aurora_steady_capture(self):
        # Inputs reconstructed from the output: 7 colors, last section lasts 63 ticks
        black = (0, 0, 0)
        fx = effect.LightingEffect(
            kind=effect.COLORSHIFT, has_direction=True, direction_type=effect.HORIZONTAL, direction_inverted=False,
            focal_x=594, focal_y=17, speed=252, scale=42,
            colors=[(255, 0, 0), black, (0, 255, 0), black, (0, 0, 255), black, black],
            positions=[0, 13, 26, 39, 52, 65, 75])
        capture = capture_payload("aurora_steady_red", 0)
        self.assertEqual(fx.wire_bytes(), self.slot_effect(capture))

    def test_slot_report_header(self):
        fx = effect.LightingEffect(kind=effect.DISABLED)
        report = model.effect_slot_report(5, fx.wire_bytes())
        self.assertEqual(len(report), 524)
        self.assertEqual(report[:4], bytes([0x0B, 0x00, 5, 0x00]))

    def test_slot_report_matches_capture_header(self):
        fx = effect.LightingEffect(
            kind=effect.COLORSHIFT, has_direction=True, direction_type=effect.RADIAL, direction_inverted=True,
            focal_x=585, focal_y=0, speed=198, scale=78,
            colors=[(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)],
            positions=[0, 17, 34, 51, 68, 85])
        self.assertEqual(model.effect_slot_report(0, fx.wire_bytes()), capture_payload("aurora_colorshift_disco", 0))

    def test_slot_range(self):
        with self.assertRaises(ValueError):
            model.effect_slot_report(19, bytes(151))

    def test_padding_section_when_first_position_is_not_zero(self):
        # fancy_lighting_engine: needs-padding-section when position[0] != 0 adds a hold section
        fx = effect.LightingEffect(kind=effect.COLORSHIFT, speed=300, colors=[(255, 0, 0), (0, 0, 255)], positions=[20, 60])
        data = fx.wire_bytes()
        sections = int.from_bytes(data[146:148], "little")
        self.assertEqual(sections, 3)
        self.assertEqual(data[0:3], bytes(3))  # padding section: no color change
        self.assertEqual(int.from_bytes(data[4:6], "little"), 60)  # 300 * 20 / 100

    def test_wave_scaling_bytes(self):
        base = dict(kind=effect.COLORSHIFT, speed=198, colors=[(255, 0, 0), (0, 255, 0)], positions=[0, 50], has_direction=True)
        for direction, expected in ((effect.HORIZONTAL, (1, 0)), (effect.VERTICAL, (0, 1)), (effect.RADIAL, (1, 1))):
            data = effect.LightingEffect(direction_type=direction, **base).wire_bytes()
            self.assertEqual((data[140], data[142]), expected)
        flat = effect.LightingEffect(**{**base, "has_direction": False}).wire_bytes()
        self.assertEqual((flat[140], flat[142]), (0, 0))

    def test_minimum_section_speed_is_33(self):
        fx = effect.LightingEffect(kind=effect.COLORSHIFT, speed=10, colors=[(255, 0, 0), (0, 255, 0)], positions=[0, 50])
        data = fx.wire_bytes()
        self.assertEqual(int.from_bytes(data[4:6], "little"), 33)
        self.assertEqual(int.from_bytes(data[12:14], "little"), 33)


if __name__ == "__main__":
    unittest.main()
