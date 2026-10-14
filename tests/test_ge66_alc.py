"""Packet layout tests for the GE66 ALC (light bar) protocol.

Expected bytes come from the SteelSeries GG 121.0.0 device specifications
(msi-ge66-alc + ss-alc-base), not from guesses.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import ge66_alc as alc  # noqa: E402


class OutputReports(unittest.TestCase):
    def test_reports_are_65_bytes_with_zero_report_id(self):
        for packet in (alc.fw_version_request(), alc.write_all(1, 2, 3), alc.global_brightness(9)):
            self.assertEqual(len(packet), 65)
            self.assertEqual(packet[0], 0x00)

    def test_write_all(self):
        self.assertEqual(alc.write_all(0x11, 0x22, 0x33)[:6], bytes([0, 0x50, 0, 0x11, 0x22, 0x33]))

    def test_global_brightness(self):
        self.assertEqual(alc.global_brightness(0xFF)[:4], bytes([0, 0x0C, 0, 0xFF]))

    def test_color_scale_defaults_to_vendor_values(self):
        self.assertEqual(alc.color_scale()[:6], bytes([0, 0x51, 0, 0xFF, 0xFF, 0x99]))

    def test_lighting_mode_commands(self):
        self.assertEqual(alc.reset_current_lighting_mode()[:4], bytes([0, 0x0D, 0, 0x02]))
        self.assertEqual(alc.restart_lighting_active()[:4], bytes([0, 0x0D, 0, 0x00]))

    def test_fw_version_request(self):
        self.assertEqual(alc.fw_version_request()[:3], bytes([0, 0x10, 0]))

    def test_reset_alc(self):
        self.assertEqual(alc.reset_alc()[:3], bytes([0, 0xF1, 0]))


class FeatureReports(unittest.TestCase):
    def test_direct_write_covers_all_35_zones(self):
        packet = alc.direct_write([(zone, 0xAA, 0xBB, 0xCC) for zone in range(alc.ZONES)])
        self.assertEqual(len(packet), 525)
        self.assertEqual(packet[:5], bytes([0, 0x0C, 0, 35, 0]))
        self.assertEqual(packet[5:9], bytes([0, 0xAA, 0xBB, 0xCC]))
        self.assertEqual(packet[5 + 4 * 34:5 + 4 * 35], bytes([34, 0xAA, 0xBB, 0xCC]))
        self.assertEqual(set(packet[5 + 4 * 35:]), {0})

    def test_direct_write_partial(self):
        packet = alc.direct_write([(3, 1, 2, 3)])
        self.assertEqual(packet[:9], bytes([0, 0x0C, 0, 1, 0, 3, 1, 2, 3]))

    def test_direct_write_rejects_unknown_zone(self):
        with self.assertRaises(ValueError):
            alc.direct_write([(35, 0, 0, 0)])

    def test_solid_fills_every_zone(self):
        packet = alc.solid(9, 8, 7)
        self.assertEqual(packet[3], 35)
        self.assertEqual(packet[5 + 4 * 17:5 + 4 * 18], bytes([17, 9, 8, 7]))


if __name__ == "__main__":
    unittest.main()
