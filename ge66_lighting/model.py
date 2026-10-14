"""Shared lighting model for the SteelSeries ALC (light bar) and KLC (keyboard).

Sources: common_lighting.device.lsp (element and effect structs), ss-alc-base and
ss-klc-base (report layouts). Builders return the bytes that follow the HID report
id: 64 for output reports, 524 for feature reports. The transport adds the id.
"""
from __future__ import annotations

from dataclasses import dataclass, field

OUTPUT_SIZE = 64
FEATURE_SIZE = 524
EFFECT_SLOTS = 19  # effect_0 .. effect_18
MAX_EFFECT_INDEX = 0x11  # lighting_element_info.effect_index range
MAX_REACT_TIME = 2000  # reactive_lighting.time range

# lighting_element_info.settings_mask values
MASK_EFFECT = 0
MASK_STEADY = 1
MASK_HOST_STREAM = 2
MASK_OVERRIDE = 4
MASK_REACTIVE = 8
MASK_RESERVED = 16
VALID_MASKS = (0, 1, 2, 4, 8, 16)

Color = tuple[int, int, int]

NAMED_COLORS: dict[str, Color] = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0), "green": (0, 255, 0),
    "blue": (0, 0, 255), "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "orange": (255, 128, 0), "purple": (128, 0, 255), "pink": (255, 105, 180),
}


def parse_color(text: str) -> Color:
    """Parse '#rrggbb', 'rrggbb', 'r,g,b' or a color name."""
    value = text.strip().lower()
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    if "," in value:
        parts = value.split(",")
        if len(parts) != 3:
            raise ValueError(f"expected r,g,b: {text!r}")
        try:
            channels = tuple(int(part) for part in parts)
        except ValueError:
            raise ValueError(f"expected r,g,b numbers: {text!r}") from None
        return check_color(channels)
    digits = value.lstrip("#")
    if len(digits) != 6:
        raise ValueError(f"expected 6 hex digits: {text!r}")
    try:
        number = int(digits, 16)
    except ValueError:
        raise ValueError(f"not a hex color: {text!r}") from None
    return (number >> 16) & 0xFF, (number >> 8) & 0xFF, number & 0xFF


def check_color(color: tuple[int, ...]) -> Color:
    if len(color) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in color):
        raise ValueError(f"color must be three 0..255 channels: {color!r}")
    return color[0], color[1], color[2]


def u16(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"{value} does not fit in uint16")
    return value.to_bytes(2, "little")


@dataclass(frozen=True)
class ElementInfo:
    """lighting_element_info: 10 bytes (initial 3, reactive 5, effect_index, settings_mask)."""

    init: Color = (0, 0, 0)
    react: Color = (0, 0, 0)
    react_time: int = 0
    effect_index: int = 0
    settings_mask: int = MASK_EFFECT

    def __post_init__(self):
        check_color(self.init)
        check_color(self.react)
        if not 0 <= self.react_time <= MAX_REACT_TIME:
            raise ValueError(f"reactive time {self.react_time} outside 0..{MAX_REACT_TIME}")
        if not 0 <= self.effect_index <= MAX_EFFECT_INDEX:
            raise ValueError(f"effect index {self.effect_index} outside 0..{MAX_EFFECT_INDEX}")
        if self.settings_mask not in VALID_MASKS:
            raise ValueError(f"settings mask {self.settings_mask} not one of {VALID_MASKS}")

    def to_bytes(self) -> bytes:
        return bytes([*self.init, *self.react]) + u16(self.react_time) + bytes([self.effect_index, self.settings_mask])

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ElementInfo":
        if len(raw) != 10:
            raise ValueError("element info is 10 bytes")
        return cls(tuple(raw[0:3]), tuple(raw[3:6]), int.from_bytes(raw[6:8], "little"), raw[8], raw[9])


@dataclass(frozen=True)
class ElementBlock:
    """element_info_block: info (10), lockmask (1), zone index (bar) or HID usage code (keyboard)."""

    info: ElementInfo = field(default_factory=ElementInfo)
    lockmask: int = 0
    ident: int = 0

    def to_bytes(self) -> bytes:
        for name, value in (("lockmask", self.lockmask), ("ident", self.ident)):
            if not 0 <= value <= 255:
                raise ValueError(f"{name} {value} outside 0..255")
        return self.info.to_bytes() + bytes([self.lockmask, self.ident])

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ElementBlock":
        if len(raw) != 12:
            raise ValueError("element block is 12 bytes")
        return cls(ElementInfo.from_bytes(raw[:10]), raw[10], raw[11])


def _feature(payload: bytes, footer: bytes = b"") -> bytes:
    if len(payload) + len(footer) > FEATURE_SIZE:
        raise ValueError("feature report overflow")
    return payload.ljust(FEATURE_SIZE - len(footer), b"\0") + footer


def output_report(*payload: int) -> bytes:
    if len(payload) > OUTPUT_SIZE:
        raise ValueError("output report overflow")
    return bytes(payload).ljust(OUTPUT_SIZE, b"\0")


def element_table(blocks: list[ElementBlock], *, layer: int = 0, footer: bytes = b"") -> bytes:
    """zone_illumination_active / key_illumination_block_N_active: 0E 00 count layer + 12-byte blocks."""
    body = b"".join(block.to_bytes() for block in blocks)
    if 4 + len(body) + len(footer) > FEATURE_SIZE:
        raise ValueError(f"{len(blocks)} elements do not fit in one feature report")
    return _feature(bytes([0x0E, 0x00, len(blocks), layer]) + body, footer)


def direct_write(entries: list[tuple[int, int, int, int]]) -> bytes:
    """direct_write: 0C 00 count 00 + (id, r, g, b) entries."""
    if 4 + 4 * len(entries) > FEATURE_SIZE:
        raise ValueError(f"{len(entries)} entries do not fit in one feature report")
    body = bytearray([0x0C, 0x00, len(entries), 0x00])
    for ident, red, green, blue in entries:
        if not all(0 <= value <= 255 for value in (ident, red, green, blue)):
            raise ValueError(f"direct write entry out of range: {(ident, red, green, blue)}")
        body += bytes([ident, red, green, blue])
    return _feature(bytes(body))


def effect_slot_report(slot: int, effect_data: bytes) -> bytes:
    """effect_N: 0B 00 slot 00 + 151 effect bytes."""
    if not 0 <= slot < EFFECT_SLOTS:
        raise ValueError(f"effect slot {slot} outside 0..{EFFECT_SLOTS - 1}")
    if len(effect_data) != 151:
        raise ValueError("effect data is 151 bytes")
    return _feature(bytes([0x0B, 0x00, slot, 0x00]) + effect_data)
