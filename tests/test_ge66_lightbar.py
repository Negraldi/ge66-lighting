"""Light bar (ALC 1038:1132) packets, sequences and hidraw discovery.

Spec sources: msi-ge66-alc.device.lsp and ss-alc-base.device.lsp.
No test opens a real /dev/hidraw node.
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ge66_alc  # noqa: E402  (baseline tool must keep working)
from ge66_golden import CAPTURES  # noqa: E402
from ge66_lighting import effect, hid, lightbar, model  # noqa: E402


def kinds(packets):
    return [(p.kind, p.data[0]) for p in packets]


class OutputReports(unittest.TestCase):
    def test_match_the_baseline_tool_byte_for_byte(self):
        # ge66_alc builds 65-byte buffers with the report id; ours omit it
        pairs = [
            (lightbar.fw_version_request(), ge66_alc.fw_version_request()),
            (lightbar.write_all((1, 2, 3)), ge66_alc.write_all(1, 2, 3)),
            (lightbar.global_brightness(0x80), ge66_alc.global_brightness(0x80)),
            (lightbar.color_scale(), ge66_alc.color_scale()),
            (lightbar.reset_current_lighting_mode(), ge66_alc.reset_current_lighting_mode()),
            (lightbar.restart_lighting_active(), ge66_alc.restart_lighting_active()),
            (lightbar.reset_alc(), ge66_alc.reset_alc()),
        ]
        for ours, theirs in pairs:
            self.assertEqual(b"\0" + ours.data, theirs)
            self.assertEqual(ours.kind, hid.OUTPUT)

    def test_save_to_flash(self):
        packet = lightbar.save_to_flash()
        self.assertEqual(packet.data[:3], bytes([0x09, 0x00, 0x00]))
        self.assertEqual(len(packet.data), 64)

    def test_commit_matches_capture(self):
        # every Aurora capture ends with an OUTPUT report starting 09 00 (save_to_flash)
        for name in ("aurora_steady_red", "aurora_colorshift_disco", "aurora_disable"):
            kind, size, hexdata = CAPTURES[name][-1]
            self.assertEqual(kind, "OUTPUT")
            self.assertEqual(lightbar.save_to_flash().data, bytes.fromhex(hexdata).ljust(size, b"\0"))

    def test_brightness_and_scale_ranges(self):
        with self.assertRaises(ValueError):
            lightbar.global_brightness(256)
        with self.assertRaises(ValueError):
            lightbar.color_scale((0, 0, 256))

    def test_color_scale_default_is_vendor_value(self):
        self.assertEqual(lightbar.color_scale().data[:5], bytes([0x51, 0, 0xFF, 0xFF, 0x99]))

    def test_fw_version_parse(self):
        # incoming struct is report_id, fw_minor, fw_major; hidraw drops the id
        self.assertEqual(lightbar.parse_fw_version(bytes([26, 2, 0])), (2, 26))
        self.assertIsNone(lightbar.parse_fw_version(None))


class FeatureReports(unittest.TestCase):
    def test_zone_table_has_35_elements(self):
        packet = lightbar.zone_table([model.ElementInfo(init=(1, 2, 3), settings_mask=1)] * lightbar.ZONES)
        self.assertEqual(packet.kind, hid.FEATURE)
        self.assertEqual(packet.data[:4], bytes([0x0E, 0x00, 35, 0x00]))
        self.assertEqual(packet.data[4:16], bytes([1, 2, 3, 0, 0, 0, 0, 0, 0, 1, 0, 0]))
        self.assertEqual(packet.data[4 + 12 * 34 + 11], 34)

    def test_zone_table_requires_every_zone(self):
        with self.assertRaises(ValueError):
            lightbar.zone_table([model.ElementInfo()] * 34)

    def test_zone_coordinates_default_is_a_line(self):
        packet = lightbar.zone_coordinates()
        self.assertEqual(packet.data[:4], bytes([0x0D, 0x00, 0x23, 0x00]))
        self.assertEqual(packet.data[4:8], bytes([0, 0, 0, 0]))  # zone 0 at (0, 0)
        self.assertEqual(packet.data[4 + 4 * 34:4 + 4 * 35], bytes([34, 0, 0, 0]))  # zone 34 at (34, 0)
        self.assertEqual(len(packet.data), 524)

    def test_zone_coordinates_custom(self):
        points = [(i * 10, 5) for i in range(35)]
        packet = lightbar.zone_coordinates(points)
        self.assertEqual(packet.data[4 + 4 * 2:4 + 4 * 3], bytes([20, 0, 5, 0]))

    def test_direct_write_matches_baseline(self):
        ours = lightbar.direct_write({0: (1, 2, 3), 34: (4, 5, 6)})
        theirs = ge66_alc.direct_write([(0, 1, 2, 3), (34, 4, 5, 6)])
        self.assertEqual(b"\0" + ours.data, theirs)

    def test_direct_write_rejects_unknown_zone(self):
        with self.assertRaises(ValueError):
            lightbar.direct_write({35: (0, 0, 0)})

    def test_solid_equals_baseline_solid(self):
        self.assertEqual(b"\0" + lightbar.solid((9, 8, 7)).data, ge66_alc.solid(9, 8, 7))


class Sequences(unittest.TestCase):
    def test_static_is_table_then_reset(self):
        packets = lightbar.static_sequence((255, 0, 0))
        self.assertEqual(kinds(packets), [(hid.FEATURE, 0x0E), (hid.OUTPUT, 0x0D)])
        self.assertEqual(packets[1].data[:3], bytes([0x0D, 0x00, 0x02]))
        info = model.ElementInfo.from_bytes(packets[0].data[4:14])
        self.assertEqual((info.init, info.settings_mask), ((255, 0, 0), model.MASK_STEADY))

    def test_static_per_zone_colors(self):
        packets = lightbar.static_sequence({3: (1, 2, 3)}, base=(9, 9, 9))
        table = packets[0].data
        self.assertEqual(table[4 + 12 * 3:4 + 12 * 3 + 3], bytes([1, 2, 3]))
        self.assertEqual(table[4:7], bytes([9, 9, 9]))

    def test_persist_adds_save_before_reset(self):
        packets = lightbar.static_sequence((1, 1, 1), persist=True)
        self.assertEqual(kinds(packets), [(hid.FEATURE, 0x0E), (hid.OUTPUT, 0x09), (hid.OUTPUT, 0x0D)])

    def test_no_save_by_default_anywhere(self):
        fx = effect.LightingEffect(kind=effect.COLORSHIFT, colors=[(255, 0, 0), (0, 0, 255)])
        for packets in (lightbar.static_sequence((1, 1, 1)), lightbar.effect_sequence(fx),
                        lightbar.disable_sequence()):
            self.assertNotIn((hid.OUTPUT, 0x09), kinds(packets))

    def test_effect_sequence_order(self):
        fx = effect.LightingEffect(kind=effect.COLORSHIFT, has_direction=True, speed=198, scale=30,
                                   colors=[(255, 0, 0), (0, 255, 0)])
        packets = lightbar.effect_sequence(fx, slot=3)
        self.assertEqual(kinds(packets), [(hid.FEATURE, 0x0B), (hid.FEATURE, 0x0D), (hid.FEATURE, 0x0E),
                                          (hid.OUTPUT, 0x0D)])
        self.assertEqual(packets[0].data[:4], bytes([0x0B, 0x00, 3, 0x00]))
        self.assertEqual(packets[0].data[4:4 + 151], fx.wire_bytes())
        info = model.ElementInfo.from_bytes(packets[2].data[4:14])
        self.assertEqual((info.effect_index, info.settings_mask), (3, model.MASK_EFFECT))

    def test_effect_without_direction_skips_coordinates(self):
        fx = effect.LightingEffect(kind=effect.BREATHE, speed=198, colors=[(255, 0, 0)])
        self.assertEqual(kinds(lightbar.effect_sequence(fx))[:2], [(hid.FEATURE, 0x0B), (hid.FEATURE, 0x0E)])

    def test_effect_zone_subset(self):
        fx = effect.LightingEffect(kind=effect.BREATHE, speed=198, colors=[(255, 0, 0)])
        table = lightbar.effect_sequence(fx, zones=[0, 1], base=(0, 0, 5))[-2].data
        first = model.ElementInfo.from_bytes(table[4:14])
        third = model.ElementInfo.from_bytes(table[4 + 24:4 + 34])
        self.assertEqual(first.settings_mask, model.MASK_EFFECT)
        self.assertEqual((third.settings_mask, third.init), (model.MASK_STEADY, (0, 0, 5)))

    def test_effect_slot_limit_for_elements(self):
        fx = effect.LightingEffect(kind=effect.BREATHE, speed=198, colors=[(255, 0, 0)])
        with self.assertRaises(ValueError):
            lightbar.effect_sequence(fx, slot=18)

    def test_disable_sequence(self):
        packets = lightbar.disable_sequence()
        self.assertEqual(packets[0].data[4:4 + 151], bytes(151))
        self.assertEqual(kinds(packets)[-1], (hid.OUTPUT, 0x0D))

    def test_lid_events(self):
        # on-lid-close / on-lid-open in msi-ge66-alc: brightness 0, reset_alc
        self.assertEqual(lightbar.lid_close().data[:3], bytes([0x0C, 0, 0]))
        self.assertEqual(lightbar.lid_open().data[:2], bytes([0xF1, 0]))

    def test_init_is_scale_then_full_brightness(self):
        self.assertEqual([p.data[0] for p in lightbar.init_sequence()], [0x51, 0x0C])
        self.assertEqual(lightbar.init_sequence()[1].data[:3], bytes([0x0C, 0, 0xFF]))

    def test_zone_selection_parser(self):
        self.assertEqual(lightbar.parse_zones("0-2,5"), [0, 1, 2, 5])
        self.assertEqual(lightbar.parse_zones("left"), list(range(17, -1, -1)))
        self.assertEqual(lightbar.parse_zones("right"), list(range(18, 35)))
        self.assertEqual(lightbar.parse_zones("all"), list(range(35)))
        with self.assertRaises(ValueError):
            lightbar.parse_zones("35")
        with self.assertRaises(ValueError):
            lightbar.parse_zones("x")


class Discovery(unittest.TestCase):
    def make_tree(self, root: pathlib.Path):
        usb = root / "devices" / "usb1" / "1-10"
        nodes = {}
        for node, iface, vid, pid in (("hidraw10", 0, "1038", "1132"), ("hidraw11", 1, "1038", "1132"),
                                      ("hidraw8", 0, "1038", "1122"), ("hidraw3", 0, "046d", "c52b")):
            device = usb / f"1-10:1.{iface}" / f"0003:{vid.upper()}:{pid.upper()}.00{node[-1]}"
            device.mkdir(parents=True)
            (device / "uevent").write_text(f"DRIVER=hid-generic\nHID_ID=0003:0000{vid.upper()}:0000{pid.upper()}\n")
            class_dir = root / "class" / node
            class_dir.mkdir(parents=True)
            (class_dir / "device").symlink_to(device)
            nodes[node] = device
        return root / "class"

    def test_resolves_by_hid_id_and_interface_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            class_dir = self.make_tree(pathlib.Path(tmp))
            self.assertEqual(hid.find_hidraw(0x1038, 0x1132, sysfs=str(class_dir)), "/dev/hidraw10")
            self.assertEqual(hid.find_hidraw(0x1038, 0x1122, sysfs=str(class_dir)), "/dev/hidraw8")

    def test_missing_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            class_dir = self.make_tree(pathlib.Path(tmp))
            with self.assertRaises(hid.DeviceNotFound):
                hid.find_hidraw(0x1038, 0x9999, sysfs=str(class_dir))


class TransportAndDevice(unittest.TestCase):
    def test_dry_run_records_and_never_touches_hardware(self):
        transport = hid.DryRunTransport()
        bar = lightbar.LightBar(transport)
        bar.apply(lightbar.static_sequence((1, 2, 3)))
        self.assertEqual(len(transport.sent), 2)
        self.assertEqual(transport.sent[0].kind, hid.FEATURE)

    def test_fw_version_uses_reply(self):
        transport = hid.DryRunTransport(replies=[bytes([26, 2, 0])])
        self.assertEqual(lightbar.LightBar(transport).fw_version(), (2, 26))
        self.assertEqual(transport.sent[0].data[:2], bytes([0x10, 0x00]))

    def test_packet_size_is_checked(self):
        with self.assertRaises(ValueError):
            hid.Packet(hid.OUTPUT, bytes(65))
        with self.assertRaises(ValueError):
            hid.Packet(hid.FEATURE, bytes(525))

    def test_ioctl_number_for_feature_report(self):
        # HIDIOCSFEATURE(525) = _IOC(read|write, 'H', 0x06, 525)
        self.assertEqual(hid.hidiocsfeature(525), 0xC20D4806)


if __name__ == "__main__":
    unittest.main()
