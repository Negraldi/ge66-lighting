"""MSI GE66 Raider light bar (SteelSeries ALC, USB 1038:1132, 35 zones).

Sources: msi-ge66-alc.device.lsp (35 zones, lid events, zone_coordinates) and
ss-alc-base.device.lsp (commands). PID 0x1132 is the standard edition; the Colie
and Disco editions (0x1138, 0x1144) reuse the same spec.
"""
from __future__ import annotations

from collections.abc import Iterable

from . import model
from .effect import LightingEffect
from .hid import FEATURE, OUTPUT, Packet, open_transport

PRODUCT_ID = 0x1132
ZONES = 35
MAX_ELEMENT_SLOT = model.MAX_EFFECT_INDEX
BLACK = (0, 0, 0)
ZONE_GROUPS = {
    "left": list(range(17, -1, -1)),
    "right": list(range(18, 35)),
    "all": list(range(ZONES)),
}


def _out(*payload: int) -> Packet:
    return Packet(OUTPUT, model.output_report(*payload))


def _check_zone(zone: int) -> None:
    if not 0 <= zone < ZONES:
        raise ValueError(f"zone {zone} outside 0..{ZONES - 1}")


def fw_version_request() -> Packet:
    return _out(0x10, 0x00)


def parse_fw_version(reply: bytes | None) -> tuple[int, int] | None:
    """Incoming struct is report_id, fw_minor, fw_major; hidraw drops the id. Returns (major, minor)."""
    return None if reply is None else (reply[1], reply[0])


def write_all(color: model.Color) -> Packet:
    return _out(0x50, 0x00, *model.check_color(color))


def global_brightness(level: int) -> Packet:
    if not 0 <= level <= 255:
        raise ValueError("brightness is 0..255")
    return _out(0x0C, 0x00, level)


def color_scale(color: model.Color = (0xFF, 0xFF, 0x99)) -> Packet:
    """White looked blue, so the vendor scales blue down to 0x99."""
    return _out(0x51, 0x00, *model.check_color(color))


def reset_current_lighting_mode() -> Packet:
    return _out(0x0D, 0x00, 0x02)


def restart_lighting_active() -> Packet:
    return _out(0x0D, 0x00, 0x00)


def reset_alc() -> Packet:
    return _out(0xF1, 0x00)


def save_to_flash() -> Packet:
    return _out(0x09, 0x00)


def lid_close() -> Packet:
    """on-lid-close with sleep_lid_close enabled."""
    return global_brightness(0)


def lid_open() -> Packet:
    """on-lid-open with sleep_lid_close enabled."""
    return reset_alc()


def init_sequence() -> list[Packet]:
    """Vendor init: color scale, then full brightness (the latter was needed on this unit)."""
    return [color_scale(), global_brightness(0xFF)]


def direct_write(colors: dict[int, model.Color]) -> Packet:
    entries = []
    for zone, color in colors.items():
        _check_zone(zone)
        entries.append((zone, *model.check_color(color)))
    return Packet(FEATURE, model.direct_write(entries))


def solid(color: model.Color) -> Packet:
    return direct_write({zone: color for zone in range(ZONES)})


def zone_table(elements: list[model.ElementInfo]) -> Packet:
    if len(elements) != ZONES:
        raise ValueError(f"the zone table needs {ZONES} elements")
    blocks = [model.ElementBlock(info, ident=zone) for zone, info in enumerate(elements)]
    return Packet(FEATURE, model.element_table(blocks))


def zone_coordinates(points: list[tuple[int, int]] | None = None) -> Packet:
    """Zone positions used by wave effects. Default: the vendor config, zone i at (i, 0)."""
    points = points if points is not None else [(zone, 0) for zone in range(ZONES)]
    if len(points) != ZONES:
        raise ValueError(f"need {ZONES} coordinates")
    body = bytes([0x0D, 0x00, ZONES, 0x00]) + b"".join(model.u16(x) + model.u16(y) for x, y in points)
    return Packet(FEATURE, body.ljust(model.FEATURE_SIZE, b"\0"))


def parse_zones(text: str) -> list[int]:
    """Parse '0-5,10', 'left', 'right' or 'all' into zone indexes."""
    zones: list[int] = []
    for token in text.split(","):
        token = token.strip().lower()
        if token in ZONE_GROUPS:
            found = ZONE_GROUPS[token]
        else:
            try:
                low, _, high = token.partition("-")
                found = list(range(int(low), int(high) + 1)) if high else [int(low)]
            except ValueError:
                raise ValueError(f"bad zone selection {token!r}") from None
        for zone in found:
            _check_zone(zone)
        zones += [zone for zone in found if zone not in zones]
    return zones


def _finish(persist: bool) -> list[Packet]:
    """Leave direct mode; with persist, store the configuration first (save_to_flash)."""
    return ([save_to_flash()] if persist else []) + [reset_current_lighting_mode()]


def static_sequence(colors: model.Color | dict[int, model.Color], *, base: model.Color = BLACK,
                    persist: bool = False) -> list[Packet]:
    """Steady colors through the zone table (settings_mask 1), like the vendor 'steady' config."""
    per_zone = colors if isinstance(colors, dict) else {zone: colors for zone in range(ZONES)}
    for zone in per_zone:
        _check_zone(zone)
    elements = [model.ElementInfo(init=per_zone.get(zone, base), settings_mask=model.MASK_STEADY)
                for zone in range(ZONES)]
    return [zone_table(elements)] + _finish(persist)


def effect_sequence(fx: LightingEffect, *, slot: int = 0, zones: Iterable[int] | None = None,
                    base: model.Color = BLACK, coordinates: bool | list[tuple[int, int]] | None = None,
                    persist: bool = False) -> list[Packet]:
    """Write the effect into a slot and point the selected zones at it (settings_mask 0)."""
    if not 0 <= slot <= MAX_ELEMENT_SLOT:
        raise ValueError(f"zone effect slot {slot} outside 0..{MAX_ELEMENT_SLOT}")
    selected = set(range(ZONES) if zones is None else zones)
    for zone in selected:
        _check_zone(zone)
    lead = fx.colors[0] if fx.colors else BLACK
    elements = [
        model.ElementInfo(init=lead, effect_index=slot, settings_mask=model.MASK_EFFECT) if zone in selected
        else model.ElementInfo(init=base, settings_mask=model.MASK_STEADY)
        for zone in range(ZONES)
    ]
    packets = [Packet(FEATURE, model.effect_slot_report(slot, fx.wire_bytes()))]
    if coordinates is None:
        coordinates = fx.has_direction
    if coordinates:
        packets.append(zone_coordinates(None if coordinates is True else coordinates))
    packets.append(zone_table(elements))
    return packets + _finish(persist)


def disable_sequence(persist: bool = False) -> list[Packet]:
    """Vendor 'disable': empty effect slot 0 and every zone steady black."""
    packets = [Packet(FEATURE, model.effect_slot_report(0, bytes(151)))]
    packets.append(zone_table([model.ElementInfo(settings_mask=model.MASK_STEADY)] * ZONES))
    return packets + _finish(persist)


class LightBar:
    def __init__(self, transport):
        self.transport = transport

    @classmethod
    def open(cls, dry_run: bool = False, path: str | None = None) -> "LightBar":
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
