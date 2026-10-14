"""Keyboard (KLC 1038:1122) packets, GE66 key map and sequences.

Spec sources: msi-ge66-klc, msi-gs65-klc, ss-klc-base. The 0B/0C report selector bytes
of the specs are not on the wire; the vendor captures (a GE76 keyboard that shares
ss-klc-base) and the working msi-perkeyrgb tool show feature reports starting at the
command byte. No test opens a real /dev/hidraw node.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ge66_golden import CAPTURES  # noqa: E402
from ge66_lighting import effect, hid, keyboard, model  # noqa: E402

RED = (255, 0, 0)


def capture_payload(name: str, index: int) -> bytes:
    kind, size, hexdata = CAPTURES[name][index]
    return bytes.fromhex(hexdata).ljust(size, b"\0")


def with_footer(packet: hid.Packet, footer: bytes) -> bytes:
    return packet.data[:-2] + footer


class KeyMap(unittest.TestCase):
    def test_canonical_blocks_follow_ss_klc_base(self):
        # lengths 42 / 19 / 24 / 11 and the hid membership of the msi_ge66_klc default settings
        self.assertEqual([len(block) for block in keyboard.BLOCKS], [42, 19, 24, 11])
        self.assertEqual(keyboard.BLOCKS[0], list(range(4, 40)) + list(range(58, 64)))
        self.assertEqual(keyboard.BLOCKS[1], list(range(64, 83)))
        self.assertEqual(keyboard.BLOCKS[2][:3], [41, 42, 43])
        self.assertEqual(keyboard.BLOCKS[2][-9:], [102, 224, 225, 226, 227, 228, 229, 230, 240])
        self.assertEqual(keyboard.BLOCKS[3], [40, 49, 50, 100, 135, 136, 137, 138, 139, 144, 145])

    def test_every_block_key_has_a_unique_name(self):
        hids = [hid_code for block in keyboard.BLOCKS for hid_code in block]
        self.assertEqual(len(hids), 96)
        self.assertEqual(len(set(hids)), 96)
        self.assertEqual(sorted(keyboard.NAMES.values()), sorted(hids))

    def test_names_resolve(self):
        for name, code in (("a", 4), ("z", 29), ("1", 30), ("0", 39), ("enter", 40), ("esc", 41),
                           ("space", 44), ("f1", 58), ("f12", 69), ("up", 82), ("fn", 240),
                           ("lctrl", 224), ("ralt", 230), ("power", 102), ("intl-backslash", 100)):
            self.assertEqual(keyboard.key_code(name), code, name)
        self.assertEqual(keyboard.key_code("0x29"), 0x29)
        self.assertEqual(keyboard.key_code("ESC"), 41)

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError):
            keyboard.key_code("nope")
        with self.assertRaises(ValueError):
            keyboard.key_code("0x1")  # not one of the 96 element hids

    def test_physical_keys_match_the_ge66_matrix(self):
        self.assertEqual(len(keyboard.PHYSICAL), 84)
        absent = set(keyboard.NAMES.values()) - set(keyboard.PHYSICAL)
        # printscreen, scrolllock, pause, delete, intl-hash and the Japanese/Korean keys
        self.assertEqual(absent, {50, 70, 71, 72, 76, 135, 136, 137, 138, 139, 144, 145})
        self.assertEqual(keyboard.MATRIX_COLUMNS * len(keyboard.MATRIX), 132)  # 22 x 6

    def test_groups(self):
        self.assertEqual(keyboard.parse_keys("f1-f3"), [58, 59, 60])
        self.assertEqual(keyboard.parse_keys("w,a,s,d"), [26, 4, 22, 7])
        self.assertEqual(keyboard.parse_keys("arrows"), [82, 81, 80, 79])
        self.assertEqual(len(keyboard.parse_keys("all")), 84)
        self.assertEqual(len(keyboard.parse_keys("everything")), 96)

    def test_key_color_spec(self):
        self.assertEqual(keyboard.parse_key_colors("esc=ff0000, w=00ff00"), {41: (255, 0, 0), 26: (0, 255, 0)})
        self.assertEqual(keyboard.parse_key_colors("f1-f2=0000ff"), {58: (0, 0, 255), 59: (0, 0, 255)})
        with self.assertRaises(ValueError):
            keyboard.parse_key_colors("esc")


class OutputReports(unittest.TestCase):
    def test_wire_layout_drops_report_selectors(self):
        # spec: 00 0B 00 <command> ...; wire: <command> ... (Keyboard_Steady_RED ends with 09 00 ...)
        kind, size, hexdata = CAPTURES["keyboard_steady_red"][-1]
        self.assertTrue(hexdata.startswith("09"))
        self.assertEqual(keyboard.save_to_flash().data[:3], bytes([0x09, 0, 0]))

    def test_commands(self):
        self.assertEqual(keyboard.fw_version_request().data[:2], bytes([0x10, 0x00]))
        self.assertEqual(keyboard.write_all(RED).data[:5], bytes([0x50, 0, 255, 0, 0]))
        self.assertEqual(keyboard.restart_lighting().data[:2], bytes([0x08, 0x00]))
        self.assertEqual(keyboard.reset_current_lighting_mode().data[:3], bytes([0x0D, 0, 2]))
        self.assertEqual(keyboard.restart_lighting_active().data[:3], bytes([0x0D, 0, 0]))
        self.assertEqual(keyboard.lighting_reset().data[:2], bytes([0x40, 0x00]))

    def test_color_scale_default_is_gs65_value(self):
        # msi-gs65-klc: (integer (* 255 0.55)) (integer (* 255 0.8)) (integer (* 255 0.6))
        self.assertEqual(keyboard.DEFAULT_COLOR_SCALE, (140, 204, 153))
        self.assertEqual(keyboard.color_scale().data[:5], bytes([0x51, 0, 140, 204, 153]))
        self.assertEqual(keyboard.color_scale((1, 2, 3)).data[:5], bytes([0x51, 0, 1, 2, 3]))

    def test_write_layout(self):
        self.assertEqual(keyboard.write_layout(3).data[:3], bytes([0x06, 0x00, 3]))
        with self.assertRaises(ValueError):
            keyboard.write_layout(4)

    def test_all_output_reports_are_64_bytes(self):
        for packet in (keyboard.fw_version_request(), keyboard.write_all(RED), keyboard.color_scale(),
                       keyboard.save_to_flash(), keyboard.restart_lighting(), keyboard.lighting_reset()):
            self.assertEqual((packet.kind, len(packet.data)), (hid.OUTPUT, 64))


class Tables(unittest.TestCase):
    def steady_red(self):
        return keyboard.key_tables({}, default=model.ElementInfo(init=RED, effect_index=1, settings_mask=1))

    def test_four_tables_cover_all_keys(self):
        tables = self.steady_red()
        self.assertEqual([t.data[2] for t in tables], [42, 19, 24, 11])
        for table in tables:
            self.assertEqual(table.kind, hid.FEATURE)
            self.assertEqual(table.data[:2], bytes([0x0E, 0x00]))
            self.assertEqual(table.data[3], 0)

    def test_first_and_third_table_equal_the_vendor_capture(self):
        tables = self.steady_red()
        self.assertEqual(with_footer(tables[0], b"\x08\x55"), capture_payload("keyboard_steady_red", 1))
        self.assertEqual(with_footer(tables[2], b"\x08\x55"), capture_payload("keyboard_steady_red", 3))

    def test_variant_table_equals_the_vendor_capture(self):
        # the vendor tinted keys that do not exist on that keyboard (G=0xAA); the layout is otherwise identical
        tint = model.ElementInfo(init=(255, 170, 0), effect_index=1, settings_mask=1)
        overrides = {code: tint for code in (50, 135, 136, 137, 138, 139, 144, 145)}
        tables = keyboard.key_tables(overrides, default=model.ElementInfo(init=RED, effect_index=1, settings_mask=1))
        self.assertEqual(with_footer(tables[3], b"\x08\x55"), capture_payload("keyboard_steady_red", 2))

    def test_default_footer_is_the_perkeyrgb_trailer(self):
        for table in self.steady_red():
            self.assertEqual(table.data[-2:], b"\x08\x39")

    def test_footer_can_be_disabled(self):
        for table in keyboard.key_tables({}, default=model.ElementInfo(), footer=b""):
            self.assertEqual(table.data[-2:], b"\0\0")

    def test_override_applies_to_one_key(self):
        tables = keyboard.key_tables({41: model.ElementInfo(init=(1, 2, 3), settings_mask=1)},
                                     default=model.ElementInfo())
        index = keyboard.BLOCKS[2].index(41)
        block = model.ElementBlock.from_bytes(tables[2].data[4 + 12 * index:16 + 12 * index])
        self.assertEqual((block.ident, block.info.init), (41, (1, 2, 3)))

    def test_rejects_unknown_hid(self):
        with self.assertRaises(ValueError):
            keyboard.key_tables({1: model.ElementInfo()}, default=model.ElementInfo())


class Sequences(unittest.TestCase):
    def test_static_is_four_tables_then_reset(self):
        packets = keyboard.static_sequence(RED)
        self.assertEqual([(p.kind, p.data[0]) for p in packets],
                         [(hid.FEATURE, 0x0E)] * 4 + [(hid.OUTPUT, 0x0D)])
        info = model.ElementInfo.from_bytes(packets[0].data[4:14])
        self.assertEqual((info.init, info.effect_index, info.settings_mask), (RED, 1, model.MASK_STEADY))

    def test_static_persist_matches_vendor_order(self):
        # vendor capture: four tables, then 09 00
        packets = keyboard.static_sequence(RED, persist=True)
        self.assertEqual([p.data[0] for p in packets], [0x0E] * 4 + [0x09, 0x0D])

    def test_static_without_persist_never_saves(self):
        for packets in (keyboard.static_sequence(RED), keyboard.off_sequence(),
                        keyboard.stream_init_sequence(), keyboard.reactive_sequence(RED, (0, 0, 255))):
            self.assertNotIn(0x09, [p.data[0] for p in packets if p.kind == hid.OUTPUT])

    def test_per_key_static(self):
        packets = keyboard.static_sequence({41: RED}, base=(0, 0, 9))
        index = keyboard.BLOCKS[2].index(41)
        self.assertEqual(packets[2].data[4 + 12 * index:4 + 12 * index + 3], bytes(RED))
        self.assertEqual(packets[0].data[4:7], bytes([0, 0, 9]))  # key 4 keeps the base color

    def test_stream_mode_then_direct_write(self):
        init = keyboard.stream_init_sequence()
        self.assertEqual([p.data[0] for p in init], [0x0E] * 4 + [0x0D])
        info = model.ElementInfo.from_bytes(init[0].data[4:14])
        self.assertEqual(info.settings_mask, model.MASK_HOST_STREAM)
        direct = keyboard.direct_write({41: RED, 26: (0, 255, 0)})
        self.assertEqual(direct.data[:12], bytes([0x0C, 0, 2, 0, 41, 255, 0, 0, 26, 0, 255, 0]))
        self.assertEqual(len(direct.data), 524)

    def test_direct_write_covers_every_key_in_one_report(self):
        direct = keyboard.direct_write({code: RED for code in keyboard.NAMES.values()})
        self.assertEqual(direct.data[2], 96)

    def test_direct_write_rejects_unknown_hid(self):
        with self.assertRaises(ValueError):
            keyboard.direct_write({1: RED})

    def test_effect_sequence(self):
        fx = effect.LightingEffect(kind=effect.COLORSHIFT, has_direction=True, speed=198, scale=40,
                                   colors=[RED, (0, 0, 255)])
        packets = keyboard.effect_sequence(fx, slot=2)
        self.assertEqual([p.data[0] for p in packets], [0x0B] + [0x0E] * 4 + [0x0D])
        self.assertEqual(packets[0].data[:4], bytes([0x0B, 0, 2, 0]))
        self.assertEqual(packets[0].data[4:155], fx.wire_bytes())
        info = model.ElementInfo.from_bytes(packets[1].data[4:14])
        self.assertEqual((info.effect_index, info.settings_mask), (2, model.MASK_EFFECT))

    def test_effect_key_subset(self):
        fx = effect.LightingEffect(kind=effect.BREATHE, speed=198, colors=[RED])
        packets = keyboard.effect_sequence(fx, keys=[41], base=(0, 0, 3))
        index = keyboard.BLOCKS[2].index(41)
        chosen = model.ElementInfo.from_bytes(packets[3].data[4 + 12 * index:14 + 12 * index])
        other = model.ElementInfo.from_bytes(packets[3].data[16:26])  # key 42, same block
        self.assertEqual(chosen.settings_mask, model.MASK_EFFECT)
        self.assertEqual((other.settings_mask, other.init), (model.MASK_STEADY, (0, 0, 3)))

    def test_reactive_sequence(self):
        packets = keyboard.reactive_sequence(RED, (0, 0, 255), react_time=300)
        info = model.ElementInfo.from_bytes(packets[0].data[4:14])
        # settings seen in the vendor default configs: mask 8, effect 0, time 300
        self.assertEqual((info.init, info.react, info.react_time, info.effect_index, info.settings_mask),
                         (RED, (0, 0, 255), 300, 0, model.MASK_REACTIVE))

    def test_off_is_steady_black(self):
        info = model.ElementInfo.from_bytes(keyboard.off_sequence()[0].data[4:14])
        self.assertEqual((info.init, info.settings_mask), ((0, 0, 0), model.MASK_STEADY))


class Device(unittest.TestCase):
    def test_physical_pid_is_1122(self):
        self.assertEqual(keyboard.PRODUCT_ID, 0x1122)
        self.assertEqual(keyboard.ENGINE_PRODUCT_ID, 0x10382034)

    def test_fw_version_over_dry_run(self):
        transport = hid.DryRunTransport(replies=[bytes([1, 0, 0])])
        board = keyboard.Keyboard(transport)
        self.assertEqual(board.fw_version(), (0, 1))
        self.assertEqual(transport.sent[0].data[:2], bytes([0x10, 0x00]))


if __name__ == "__main__":
    unittest.main()
