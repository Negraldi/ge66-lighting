#!/usr/bin/env python3
"""MSI GE66 Raider light bar (SteelSeries ALC, 1038:1132) control over hidraw.

Protocol source: SteelSeries GG 121.0.0 device specifications
(msi-ge66-alc + ss-alc-base). See docs/PROTOCOL.md.

Output reports are 64 bytes on the wire, feature reports 524; both are sent
with a leading 0x00 report id, which the kernel strips.
"""
from __future__ import annotations

import argparse
import fcntl
import glob
import os
import select
import sys
import time

VENDOR_ID = 0x1038
PRODUCT_ID = 0x1132
ZONES = 35
REPORT_SIZE = 65
FEATURE_SIZE = 525
COMMAND_GAP = 0.010  # (time-between-commands) in ss-alc-base, milliseconds there


def _output(*payload: int) -> bytes:
    return bytes([0x00, *payload]).ljust(REPORT_SIZE, b"\0")


def _feature(payload: bytes) -> bytes:
    return (b"\0" + payload).ljust(FEATURE_SIZE, b"\0")


def fw_version_request() -> bytes:
    return _output(0x10, 0x00)


def write_all(red: int, green: int, blue: int) -> bytes:
    return _output(0x50, 0x00, red, green, blue)


def global_brightness(level: int) -> bytes:
    return _output(0x0C, 0x00, level)


def color_scale(red: int = 0xFF, green: int = 0xFF, blue: int = 0x99) -> bytes:
    return _output(0x51, 0x00, red, green, blue)


def reset_current_lighting_mode() -> bytes:
    return _output(0x0D, 0x00, 0x02)


def restart_lighting_active() -> bytes:
    return _output(0x0D, 0x00, 0x00)


def reset_alc() -> bytes:
    return _output(0xF1, 0x00)


def direct_write(zones: list[tuple[int, int, int, int]]) -> bytes:
    """Build a direct write for (zone, red, green, blue) entries."""
    body = bytearray([0x0C, 0x00, len(zones), 0x00])
    for zone, red, green, blue in zones:
        if not 0 <= zone < ZONES:
            raise ValueError(f"zone {zone} outside 0..{ZONES - 1}")
        body += bytes([zone, red, green, blue])
    return _feature(bytes(body))


def solid(red: int, green: int, blue: int) -> bytes:
    return direct_write([(zone, red, green, blue) for zone in range(ZONES)])


def find_hidraw(vendor: int = VENDOR_ID, product: int = PRODUCT_ID) -> str:
    """Return the hidraw node of USB interface 0; node numbers change across boots."""
    wanted = f"HID_ID=0003:{vendor:08X}:{product:08X}"
    for node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        device = os.path.realpath(os.path.join(node, "device"))
        with open(os.path.join(device, "uevent")) as uevent:
            if wanted not in uevent.read().upper():
                continue
        if ":1.0/" in device + "/":
            return "/dev/" + os.path.basename(node)
    raise SystemExit(f"{vendor:04x}:{product:04x} interface 0 not found")


def _hidiocsfeature(length: int) -> int:
    return (3 << 30) | (length << 16) | (ord("H") << 8) | 0x06


class LightBar:
    def __init__(self, path: str | None = None):
        self.path = path or find_hidraw()
        self._fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)

    def close(self) -> None:
        os.close(self._fd)

    def send(self, packet: bytes) -> None:
        if len(packet) == FEATURE_SIZE:
            fcntl.ioctl(self._fd, _hidiocsfeature(len(packet)), bytearray(packet))
        else:
            os.write(self._fd, packet)
        time.sleep(COMMAND_GAP)

    def read(self, timeout: float = 0.5) -> bytes | None:
        ready, _, _ = select.select([self._fd], [], [], timeout)
        return os.read(self._fd, 64) if ready else None

    def fw_version(self) -> str | None:
        while self.read(0) is not None:
            pass
        self.send(fw_version_request())
        reply = self.read()
        # Incoming struct is report_id, fw_minor, fw_major; hidraw drops the id.
        return None if reply is None else f"{reply[1]}.{reply[0]} (raw {reply[:8].hex(' ')})"


def _color(text: str) -> tuple[int, int, int]:
    value = int(text.lstrip("#"), 16)
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("info", help="show device node and firmware version")
    for name, text in (("color", "set every zone through direct write"),
                       ("fill", "set every zone through write_all_illumination")):
        commands.add_parser(name, help=text).add_argument("rgb", type=_color)
    commands.add_parser("brightness", help="global brightness 0-255").add_argument("level", type=int)
    commands.add_parser("off", help="turn the bar off")
    commands.add_parser("init", help="vendor init: color scale + full brightness")
    args = parser.parse_args(argv)

    bar = LightBar()
    try:
        if args.command == "info":
            print(bar.path, "firmware:", bar.fw_version())
        elif args.command == "color":
            bar.send(solid(*args.rgb))
        elif args.command == "fill":
            bar.send(write_all(*args.rgb))
        elif args.command == "brightness":
            bar.send(global_brightness(args.level))
        elif args.command == "off":
            bar.send(solid(0, 0, 0))
        elif args.command == "init":
            bar.send(color_scale())
            bar.send(global_brightness(0xFF))
    finally:
        bar.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
