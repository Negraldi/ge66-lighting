"""hidraw transport and packet container shared by the bar and the keyboard.

Both devices expose a vendor HID interface (usage page 0xFFC0) with no report ids:
64-byte input/output reports and a 524-byte feature report. hidraw wants a leading
zero byte (the report id) on every write; the kernel strips it.
"""
from __future__ import annotations

import fcntl
import glob
import os
import select
import sys
import time
from dataclasses import dataclass
from typing import TextIO

VENDOR_ID = 0x1038
OUTPUT = "output"
FEATURE = "feature"
SIZES = {OUTPUT: 64, FEATURE: 524}
COMMAND_GAP = 0.010  # (time-between-commands) 10 in ss-alc-base and ss-klc-base, milliseconds there


class DeviceNotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class Packet:
    """Report bytes without the leading report id."""

    kind: str
    data: bytes

    def __post_init__(self):
        if self.kind not in SIZES:
            raise ValueError(f"unknown packet kind {self.kind!r}")
        if len(self.data) != SIZES[self.kind]:
            raise ValueError(f"{self.kind} report must be {SIZES[self.kind]} bytes, got {len(self.data)}")


def hidiocsfeature(length: int) -> int:
    """HIDIOCSFEATURE(len) = _IOC(_IOC_READ | _IOC_WRITE, 'H', 0x06, len)."""
    return (3 << 30) | (length << 16) | (ord("H") << 8) | 0x06


def find_hidraw(vendor: int, product: int, interface: int = 0, sysfs: str = "/sys/class/hidraw") -> str:
    """Resolve /dev/hidrawN from the HID id and USB interface; node numbers change across boots."""
    wanted = f"HID_ID=0003:{vendor:08X}:{product:08X}"
    suffix = f":1.{interface}"
    for node in sorted(glob.glob(os.path.join(sysfs, "hidraw*"))):
        device = os.path.realpath(os.path.join(node, "device"))
        try:
            with open(os.path.join(device, "uevent")) as uevent:
                text = uevent.read().upper()
        except OSError:
            continue
        if wanted in text and os.path.basename(os.path.dirname(device)).endswith(suffix):
            return "/dev/" + os.path.basename(node)
    raise DeviceNotFound(f"{vendor:04x}:{product:04x} interface {interface} not found")


class HidrawTransport:
    def __init__(self, path: str):
        self.path = path
        self._fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)

    def send(self, packet: Packet) -> None:
        if packet.kind == FEATURE:
            fcntl.ioctl(self._fd, hidiocsfeature(len(packet.data) + 1), bytearray(b"\0" + packet.data))
        else:
            os.write(self._fd, b"\0" + packet.data)
        time.sleep(COMMAND_GAP)

    def read(self, timeout: float = 0.5) -> bytes | None:
        ready, _, _ = select.select([self._fd], [], [], timeout)
        return os.read(self._fd, 64) if ready else None

    def drain(self) -> None:
        while self.read(0) is not None:
            pass

    def close(self) -> None:
        os.close(self._fd)


class DryRunTransport:
    """Records packets and optionally prints them; never opens a device."""

    def __init__(self, replies: list[bytes] | None = None, stream: TextIO | None = None):
        self.sent: list[Packet] = []
        self._replies = list(replies or [])
        self._stream = stream

    def send(self, packet: Packet) -> None:
        self.sent.append(packet)
        if self._stream is not None:
            trimmed = packet.data.rstrip(b"\0").ljust(8, b"\0")
            print(f"{packet.kind:7} {len(packet.data):3}B  {trimmed.hex(' ')}", file=self._stream)

    def read(self, timeout: float = 0.5) -> bytes | None:
        return self._replies.pop(0) if self._replies else None

    def drain(self) -> None:
        pass

    def close(self) -> None:
        pass


def open_transport(vendor: int, product: int, dry_run: bool = False, path: str | None = None):
    if dry_run:
        return DryRunTransport(stream=sys.stdout)
    return HidrawTransport(path or find_hidraw(vendor, product))
