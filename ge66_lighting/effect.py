"""Port of the "fancy lighting engine" forward transform (fancy_lighting_engine.device.lsp).

The vendor UI describes an effect with the 69-byte `lighting_effect` struct
(common_lighting.device.lsp); the engine converts it to the 151 bytes the firmware
stores per effect slot: 16 sections of 8 bytes, then the initial color, focal point,
wave scaling, scale, section count and total tick count.

Arithmetic follows the Go engine: integer division truncates toward zero. This was
confirmed against the vendor captures (see tests/test_ge66_model.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import Color, check_color, u16

DISABLED, COLORSHIFT, BREATHE = 0, 1, 2
HORIZONTAL, VERTICAL, RADIAL = 0, 1, 2
MAX_COLORS = 14
MAX_SECTIONS = 16
MIN_SECTION_SPEED = 33  # deltas would exceed the -127..127 range below this
EFFECT_BYTES = 151
STRUCT_BYTES = 69

KIND_NAMES = {"disabled": DISABLED, "colorshift": COLORSHIFT, "breathe": BREATHE}
DIRECTION_NAMES = {"horizontal": HORIZONTAL, "vertical": VERTICAL, "radial": RADIAL}
PALETTES: dict[str, list[Color]] = {
    "rainbow": [(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)],
    "police": [(255, 0, 0), (0, 0, 255)],
    "fire": [(255, 0, 0), (255, 128, 0), (255, 255, 0)],
    "ocean": [(0, 0, 255), (0, 128, 255), (0, 255, 255)],
}


def _div(numerator: int, denominator: int) -> int:
    quotient = abs(numerator) // abs(denominator)
    return quotient if (numerator >= 0) == (denominator > 0) else -quotient


def default_positions(count: int) -> list[int]:
    """Evenly spread positions, using the vendor template spacing (0, 17, 34 ... for six colors)."""
    if count == 0:
        return []
    step = round(100 / count)
    return [min(i * step, 100) for i in range(count)]


@dataclass
class LightingEffect:
    kind: int
    has_direction: bool = False
    direction_type: int = HORIZONTAL
    direction_inverted: bool = False
    focal_x: int = 0
    focal_y: int = 0
    speed: int = 100
    scale: int = 0
    colors: list[Color] = field(default_factory=list)
    positions: list[int] | None = None

    def __post_init__(self):
        if self.kind not in (DISABLED, COLORSHIFT, BREATHE):
            raise ValueError(f"effect type {self.kind} is not disabled/colorshift/breathe")
        if self.direction_type not in (HORIZONTAL, VERTICAL, RADIAL):
            raise ValueError(f"direction type {self.direction_type} outside 0..2")
        if len(self.colors) > MAX_COLORS:
            raise ValueError(f"at most {MAX_COLORS} colors")
        self.colors = [check_color(tuple(color)) for color in self.colors]
        if self.positions is None:
            self.positions = default_positions(len(self.colors))
        if len(self.positions) != len(self.colors):
            raise ValueError("positions and colors must have the same length")
        if any(not 0 <= pos <= 100 for pos in self.positions):
            raise ValueError("positions are percentages 0..100")
        if self.positions != sorted(self.positions):
            raise ValueError("positions must not decrease")
        for name in ("focal_x", "focal_y", "speed", "scale"):
            u16(getattr(self, name))

    def struct_bytes(self) -> bytes:
        """The 69-byte lighting_effect struct."""
        colors = b"".join(bytes(color) for color in self.colors).ljust(3 * MAX_COLORS, b"\0")
        positions = bytes(self.positions).ljust(MAX_COLORS, b"\0")
        raw = (bytes([self.kind, int(self.has_direction), self.direction_type, int(self.direction_inverted)])
               + u16(self.focal_x) + u16(self.focal_y) + u16(self.speed) + u16(self.scale)
               + bytes([len(self.colors)]) + colors + positions)
        assert len(raw) == STRUCT_BYTES
        return raw

    def wire_bytes(self) -> bytes:
        """The 151 bytes stored in an effect slot."""
        return effect_bytes(self.struct_bytes())


def _color_byte(payload: bytes, color_index: int, channel: int) -> int:
    return payload[13 + color_index * 3 + channel]


def _position(payload: bytes, index: int) -> int:
    return payload[55 + index]


def _scaled(initial: int, final: int, speed: int) -> int:
    diff = _div(16 * (final - initial), speed)
    return 256 + diff if diff < 0 else diff


def _section(deltas: tuple[int, int, int], speed: int, next_index: int) -> bytes:
    return bytes([*deltas, 0]) + u16(speed) + bytes([next_index, 0])


_EMPTY_SECTION = (0, bytes(8))


def _colorshift_section(payload: bytes, index: int, sections: int, ticks: int, padded: bool) -> tuple[int, bytes]:
    if sections == 0 or index >= sections:
        return _EMPTY_SECTION
    last = index == sections - 1
    first_color = (0 if index == 0 else index - 1) if padded else index
    last_color = 0 if last else (index if padded else index + 1)
    start = 0 if index == 0 else _position(payload, index - 1 if padded else index)
    end = 100 if last else _position(payload, index if padded else index + 1)
    speed = max(_div(ticks * (end - start), 100), MIN_SECTION_SPEED)
    deltas = tuple(_scaled(_color_byte(payload, first_color, c), _color_byte(payload, last_color, c), speed)
                   for c in range(3))
    return speed, _section(deltas, speed, 0 if last else index + 1)


def _breathe_section(payload: bytes, index: int, colors: int, ticks: int, padded: bool) -> tuple[int, bytes]:
    sections = 2 * colors + (1 if padded else 0)
    if sections == 0 or index >= sections:
        return _EMPTY_SECTION
    if index == 0:
        start = 0
    else:
        start = _position(payload, _div(index - 1, 2) if padded else _div(index, 2))
    if index >= sections - 2:
        end = 100
    elif padded:
        end = _position(payload, 0) if index == 0 else _position(payload, 1 + _div(index - 1, 2))
    else:
        end = _position(payload, 1 + _div(index, 2))
    speed = max(_div(ticks * _div(end - start, 2), 100), MIN_SECTION_SPEED)
    if index == 0:
        first_color = 0
    else:
        first_color = _div(index - 1, 2) if padded else _div(index, 2)
    if index == sections - 1:
        last_color = 0
    elif padded:
        last_color = 0 if index == 0 else _div(index - 1, 2) + 1
    else:
        last_color = _div(index, 2) + 1
    odd = (index % 2 == 1) if padded else (index % 2 == 0)
    padding = padded and index == 0
    deltas = []
    for c in range(3):
        initial = _color_byte(payload, first_color, c) if (odd or padding) else 0
        final = 0 if (odd and not padding) else _color_byte(payload, last_color, c)
        deltas.append(_scaled(initial, final, speed))
    return speed, _section(tuple(deltas), speed, 0 if index == sections - 1 else index + 1)


def effect_bytes(payload: bytes) -> bytes:
    """get-effect-bytes: 69-byte lighting_effect struct -> 151 effect bytes."""
    if len(payload) != STRUCT_BYTES:
        raise ValueError(f"lighting_effect struct is {STRUCT_BYTES} bytes")
    kind = payload[0]
    if kind == DISABLED:
        return bytes(EFFECT_BYTES)
    if kind not in (COLORSHIFT, BREATHE):
        return bytes(EFFECT_BYTES)  # types the engine does not support become disabled
    has_direction, direction_type, inverted = payload[1], payload[2], payload[3]
    ticks = int.from_bytes(payload[8:10], "little")
    colors = payload[12]
    padded = _position(payload, 0) != 0
    if kind == COLORSHIFT:
        sections = colors + (1 if padded else 0)
    else:
        sections = 2 * colors + (1 if padded else 0)
    if sections > MAX_SECTIONS:
        raise ValueError(f"{sections} sections exceed the {MAX_SECTIONS} the engine can send; use fewer colors")
    if kind == COLORSHIFT:
        parts = [_colorshift_section(payload, i, sections, ticks, padded) for i in range(MAX_SECTIONS)]
    else:
        parts = [_breathe_section(payload, i, colors, ticks, padded) for i in range(MAX_SECTIONS)]
    section_bytes = b"".join(part[1] for part in parts)
    total = sum(part[0] for part in parts)
    if has_direction == 1 and direction_type in (HORIZONTAL, RADIAL):
        x_scaling = b"\x01\x00"
    else:
        x_scaling = b"\x00\x00"
    if has_direction == 1 and direction_type in (VERTICAL, RADIAL):
        y_scaling = b"\x01\x00"
    else:
        y_scaling = b"\x00\x00"
    initial = b"".join(u16(16 * _color_byte(payload, 0, c)) for c in range(3))
    data = (section_bytes + initial + b"\xff\x00" + payload[4:8] + x_scaling + y_scaling
            + payload[10:12] + u16(sections) + u16(total) + bytes([inverted]))
    assert len(data) == EFFECT_BYTES
    return data
