"""MSI GE66 Raider per-key keyboard (SteelSeries KLC, USB 1038:1122).

Which spec applies: the physical device is PID 0x1122, which the engine knows as the
generic `msi-klc` stub (0x10381122, firmware version only). The lighting spec is the
virtual device `msi-ge66-klc` (0x10382034, written through appPID 0x1122 in its
fw_update struct), which includes msi-gs65-klc -> ss-klc-base. The Colie (0x10382037)
and Disco (0x10382041) editions include it unchanged.

Wire layout: the specs prefix KLC structs with a report id plus selector bytes
(0B for output, 0C for feature). The vendor USB captures of a sibling KLC and the
working msi-perkeyrgb show reports that start at the command byte, so those selectors
are not sent here.
"""
from __future__ import annotations

from collections.abc import Iterable

from . import model
from .effect import LightingEffect
from .hid import FEATURE, OUTPUT, Packet, open_transport
from .lightbar import parse_fw_version

PRODUCT_ID = 0x1122
ENGINE_PRODUCT_ID = 0x10382034
BLACK = (0, 0, 0)
DEFAULT_COLOR_SCALE = (140, 204, 153)  # msi-gs65-klc: 255 * 0.55, 0.8, 0.6 truncated
STEADY_EFFECT_INDEX = 1  # what the vendor sends with settings_mask 1
DEFAULT_FOOTER = b"\x08\x39"  # trailer msi-perkeyrgb sends and this keyboard accepts; the capture has 08 55
LAYOUTS = 4

# Element table membership: key_illumination_block_1..4 (ss-klc-base) filled with the keys of
# the default msi_ge66_klc configuration. Lengths 42, 19, 24 and 11.
BLOCKS: list[list[int]] = [
    list(range(4, 40)) + list(range(58, 64)),
    list(range(64, 83)),
    [41, 42, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 102, 224, 225, 226, 227, 228, 229, 230, 240],
    [40, 49, 50, 100, 135, 136, 137, 138, 139, 144, 145],
]
ALL_HIDS = [code for block in BLOCKS for code in block]

# hidcode-matrix-layout-nonvariant of msi-ge66-klc (English layout), 6 rows x 22 columns
MATRIX_COLUMNS = 22
MATRIX: list[list[int | None]] = [
    [41, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, None, 73, 102] + [None] * 6,
    [53, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, None, 42, None, 74] + [None] * 5,
    [43, 20, 26, 8, 21, 23, 28, 24, 12, 18, 19, 47, 48, 49, None, 75] + [None] * 6,
    [57, 4, 22, 7, 9, 10, 11, 13, 14, 15, 51, 52, None, 40, None, 78] + [None] * 6,
    [225, None, 29, 27, 6, 25, 5, 17, 16, 54, 55, 56, None, 229, None, 82, 77] + [None] * 5,
    [224, None, 227, 226, None, None, 44, None, None, 230, 100, 240, 228, None, 80, 81, 79] + [None] * 5,
]
PHYSICAL: list[int] = sorted(code for row in MATRIX for code in row if code is not None)

NAMES: dict[str, int] = {chr(ord("a") + i): 4 + i for i in range(26)}
NAMES.update({str((i + 1) % 10): 30 + i for i in range(10)})
NAMES.update({
    "enter": 40, "esc": 41, "backspace": 42, "tab": 43, "space": 44, "minus": 45, "equal": 46,
    "lbracket": 47, "rbracket": 48, "backslash": 49, "intl-hash": 50, "semicolon": 51, "quote": 52,
    "grave": 53, "comma": 54, "period": 55, "slash": 56, "caps": 57,
    "printscreen": 70, "scrolllock": 71, "pause": 72, "insert": 73, "home": 74, "pageup": 75,
    "delete": 76, "end": 77, "pagedown": 78, "right": 79, "left": 80, "down": 81, "up": 82,
    "intl-backslash": 100, "power": 102,
    "jp-ro": 135, "jp-kana": 136, "jp-yen": 137, "jp-henkan": 138, "jp-muhenkan": 139,
    "lang1": 144, "lang2": 145,
    "lctrl": 224, "lshift": 225, "lalt": 226, "lwin": 227, "rctrl": 228, "rshift": 229, "ralt": 230,
    "fn": 240,
})
NAMES.update({f"f{i}": 57 + i for i in range(1, 13)})
KEY_GROUPS: dict[str, list[int]] = {
    "all": PHYSICAL,
    "everything": sorted(ALL_HIDS),
    "letters": list(range(4, 30)),
    "numbers": list(range(30, 40)),
    "fkeys": list(range(58, 70)),
    "arrows": [82, 81, 80, 79],
    "modifiers": [224, 225, 226, 227, 228, 229, 230],
}
_NAME_BY_HID = {code: name for name, code in NAMES.items()}


def key_name(code: int) -> str:
    return _NAME_BY_HID[code]


def key_code(text: str) -> int:
    token = text.strip().lower()
    if token in NAMES:
        return NAMES[token]
    if token.startswith("0x"):
        try:
            code = int(token, 16)
        except ValueError:
            raise ValueError(f"bad key code {text!r}") from None
        if code in ALL_HIDS:
            return code
        raise ValueError(f"key code {text!r} is not one of the {len(ALL_HIDS)} GE66 element codes")
    raise ValueError(f"unknown key {text!r}; run `ge66-light keyboard keys` for the list")


def parse_keys(text: str) -> list[int]:
    """Parse 'esc,w-d,fkeys' style selections (names, a-b ranges, groups) into HID codes."""
    codes: list[int] = []
    for token in text.split(","):
        token = token.strip().lower()
        if token in KEY_GROUPS:
            found = KEY_GROUPS[token]
        elif token in NAMES or token.startswith("0x") or "-" not in token:
            found = [key_code(token)]
        else:
            low, _, high = token.partition("-")
            start, stop = key_code(low), key_code(high)
            found = [code for code in range(start, stop + 1) if code in ALL_HIDS]
        codes += [code for code in found if code not in codes]
    return codes


def parse_key_colors(text: str) -> dict[int, model.Color]:
    """Parse 'esc=ff0000,f1-f4=0000ff' into {hid: color}."""
    result: dict[int, model.Color] = {}
    for token in text.split(","):
        keys, sep, color = token.rpartition("=")
        if not sep or not keys.strip():
            raise ValueError(f"expected keys=color, got {token!r}")
        for code in parse_keys(keys):
            result[code] = model.parse_color(color)
    return result


def _out(*payload: int) -> Packet:
    return Packet(OUTPUT, model.output_report(*payload))


def fw_version_request() -> Packet:
    return _out(0x10, 0x00)


def write_all(color: model.Color) -> Packet:
    return _out(0x50, 0x00, *model.check_color(color))


def color_scale(color: model.Color = DEFAULT_COLOR_SCALE) -> Packet:
    return _out(0x51, 0x00, *model.check_color(color))


def save_to_flash() -> Packet:
    return _out(0x09, 0x00)


def restart_lighting() -> Packet:
    return _out(0x08, 0x00)


def reset_current_lighting_mode() -> Packet:
    return _out(0x0D, 0x00, 0x02)


def restart_lighting_active() -> Packet:
    return _out(0x0D, 0x00, 0x00)


def lighting_reset() -> Packet:
    """Fallback reset kept in ss-klc-base."""
    return _out(0x40, 0x00)


def write_layout(layout: int) -> Packet:
    """write_layout_0..3; the spec marks them as not used by the vendor driver."""
    if not 0 <= layout < LAYOUTS:
        raise ValueError(f"layout {layout} outside 0..{LAYOUTS - 1}")
    return _out(0x06, 0x00, layout)


def _check_hid(code: int) -> None:
    if code not in ALL_HIDS:
        raise ValueError(f"HID code {code} is not one of the GE66 element codes")


def key_tables(overrides: dict[int, model.ElementInfo], default: model.ElementInfo,
               footer: bytes = DEFAULT_FOOTER) -> list[Packet]:
    """The four element tables (42, 19, 24, 11 keys) with per-key overrides over a default."""
    for code in overrides:
        _check_hid(code)
    return [
        Packet(FEATURE, model.element_table(
            [model.ElementBlock(overrides.get(code, default), ident=code) for code in block], footer=footer))
        for block in BLOCKS
    ]


def direct_write(colors: dict[int, model.Color]) -> Packet:
    entries = []
    for code, color in colors.items():
        _check_hid(code)
        entries.append((code, *model.check_color(color)))
    return Packet(FEATURE, model.direct_write(entries))


def _finish(persist: bool) -> list[Packet]:
    return ([save_to_flash()] if persist else []) + [reset_current_lighting_mode()]


def _steady(color: model.Color) -> model.ElementInfo:
    return model.ElementInfo(init=color, effect_index=STEADY_EFFECT_INDEX, settings_mask=model.MASK_STEADY)


def static_sequence(colors: model.Color | dict[int, model.Color], *, base: model.Color = BLACK,
                    persist: bool = False, footer: bytes = DEFAULT_FOOTER) -> list[Packet]:
    """Steady colors through the element tables (settings_mask 1), as in the vendor capture."""
    if isinstance(colors, dict):
        overrides = {code: _steady(color) for code, color in colors.items()}
        default = _steady(base)
    else:
        overrides, default = {}, _steady(colors)
    return key_tables(overrides, default, footer) + _finish(persist)


def off_sequence(persist: bool = False, footer: bytes = DEFAULT_FOOTER) -> list[Packet]:
    return static_sequence(BLACK, persist=persist, footer=footer)


def stream_init_sequence(footer: bytes = DEFAULT_FOOTER) -> list[Packet]:
    """Put every key in host-stream mode (settings_mask 2) so direct writes show up."""
    host = model.ElementInfo(effect_index=0, settings_mask=model.MASK_HOST_STREAM)
    return key_tables({}, host, footer) + [reset_current_lighting_mode()]


def effect_sequence(fx: LightingEffect, *, slot: int = 0, keys: Iterable[int] | None = None,
                    base: model.Color = BLACK, persist: bool = False,
                    footer: bytes = DEFAULT_FOOTER) -> list[Packet]:
    """Write the effect into a slot and point the selected keys at it (settings_mask 0)."""
    if not 0 <= slot <= model.MAX_EFFECT_INDEX:
        raise ValueError(f"key effect slot {slot} outside 0..{model.MAX_EFFECT_INDEX}")
    lead = fx.colors[0] if fx.colors else BLACK
    running = model.ElementInfo(init=lead, effect_index=slot, settings_mask=model.MASK_EFFECT)
    if keys is None:
        overrides, default = {}, running
    else:
        overrides, default = {code: running for code in keys}, _steady(base)
    packets = [Packet(FEATURE, model.effect_slot_report(slot, fx.wire_bytes()))]
    return packets + key_tables(overrides, default, footer) + _finish(persist)


def reactive_sequence(color: model.Color, react_color: model.Color, *, react_time: int = 300,
                      keys: Iterable[int] | None = None, base: model.Color = BLACK,
                      persist: bool = False, footer: bytes = DEFAULT_FOOTER) -> list[Packet]:
    """Keys rest at `color` and flash `react_color` for `react_time` ms when pressed (settings_mask 8)."""
    reactive = model.ElementInfo(init=color, react=react_color, react_time=react_time, effect_index=0,
                                 settings_mask=model.MASK_REACTIVE)
    if keys is None:
        overrides, default = {}, reactive
    else:
        overrides, default = {code: reactive for code in keys}, _steady(base)
    return key_tables(overrides, default, footer) + _finish(persist)


class Keyboard:
    def __init__(self, transport):
        self.transport = transport

    @classmethod
    def open(cls, dry_run: bool = False, path: str | None = None) -> "Keyboard":
        return cls(open_transport(0x1038, PRODUCT_ID, dry_run, path))

    def apply(self, packets: Iterable[Packet]) -> None:
        for packet in packets:
            self.transport.send(packet)

    def fw_version(self) -> tuple[int, int] | None:
        self.transport.drain()
        self.apply([fw_version_request()])
        return parse_fw_version(self.transport.read())

    def close(self) -> None:
        self.transport.close()
