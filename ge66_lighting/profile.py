"""JSON profiles: validation and translation into packets. Format: docs/profile-format.md."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from . import effect, keyboard, lightbar, model
from .hid import Packet

VERSION = 1
DEFAULT_SPEED = 200
DEFAULT_WAVE_SCALE = 40
TOP_KEYS = {"version", "name", "description", "persist", "lightbar", "keyboard"}
EFFECT_KEYS = {"kind", "colors", "positions", "speed", "direction", "invert", "focal", "scale"}


class ProfileError(ValueError):
    pass


def _check_keys(obj: Any, allowed: set[str], where: str) -> dict:
    if not isinstance(obj, dict):
        raise ProfileError(f"{where}: expected an object")
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ProfileError(f"{where}: unknown field(s) {', '.join(unknown)}")
    return obj


def _color(value: Any, where: str) -> model.Color:
    try:
        if isinstance(value, list):
            return model.check_color(tuple(value))
        return model.parse_color(str(value))
    except ValueError as error:
        raise ProfileError(f"{where}: {error}") from None


def _int(value: Any, where: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ProfileError(f"{where}: expected an integer {low}..{high}")
    return value


def effect_from_dict(spec: dict) -> effect.LightingEffect:
    _check_keys(spec, EFFECT_KEYS, "effect")
    kind = spec.get("kind")
    if kind not in ("colorshift", "breathe"):
        raise ProfileError("effect.kind must be 'colorshift' or 'breathe'")
    colors = spec.get("colors")
    if isinstance(colors, str):
        if colors not in effect.PALETTES:
            raise ProfileError(f"effect.colors: unknown palette {colors!r} (known: {', '.join(effect.PALETTES)})")
        colors = list(effect.PALETTES[colors])
    elif isinstance(colors, list) and colors:
        colors = [_color(c, "effect.colors") for c in colors]
    else:
        raise ProfileError("effect.colors: give a palette name or a non-empty color list")
    direction = spec.get("direction")
    if direction is not None and direction not in effect.DIRECTION_NAMES:
        raise ProfileError(f"effect.direction must be one of {', '.join(effect.DIRECTION_NAMES)} or null")
    focal = spec.get("focal", [0, 0])
    if not (isinstance(focal, list) and len(focal) == 2):
        raise ProfileError("effect.focal: expected [x, y]")
    try:
        return effect.LightingEffect(
            kind=effect.KIND_NAMES[kind], has_direction=direction is not None,
            direction_type=effect.DIRECTION_NAMES.get(direction, effect.HORIZONTAL),
            direction_inverted=bool(spec.get("invert", False)),
            focal_x=_int(focal[0], "effect.focal", 0, 0xFFFF), focal_y=_int(focal[1], "effect.focal", 0, 0xFFFF),
            speed=_int(spec.get("speed", DEFAULT_SPEED), "effect.speed", 0, 0xFFFF),
            scale=_int(spec.get("scale", DEFAULT_WAVE_SCALE if direction else 0), "effect.scale", 0, 0xFFFF),
            colors=colors, positions=spec.get("positions"))
    except ValueError as error:
        if isinstance(error, ProfileError):
            raise
        raise ProfileError(f"effect: {error}") from None


def _selection(parser: Callable[[str], Any], text: Any, where: str):
    try:
        return parser(str(text))
    except ValueError as error:
        raise ProfileError(f"{where}: {error}") from None


def _overrides(section: dict, expand: Callable[[str], list[int]], where: str) -> dict[int, model.Color]:
    result: dict[int, model.Color] = {}
    for selector, value in _check_keys(section.get("set", {}), set(section.get("set", {})), f"{where}.set").items():
        color = _color(value, f"{where}.set.{selector}")
        for ident in _selection(expand, selector, f"{where}.set"):
            result[ident] = color
    return result


def _persist(section: dict, default: bool) -> bool:
    value = section.get("persist", default)
    if not isinstance(value, bool):
        raise ProfileError("persist must be true or false")
    return value


def build_lightbar(section: dict, persist: bool = False) -> list[Packet]:
    allowed = {"persist", "color_scale", "brightness", "lighting"}
    _check_keys(section, allowed, "lightbar")
    persist = _persist(section, persist)
    packets: list[Packet] = []
    try:
        if "color_scale" in section:
            packets.append(lightbar.color_scale(_color(section["color_scale"], "lightbar.color_scale")))
        if "brightness" in section:
            packets.append(lightbar.global_brightness(_int(section["brightness"], "lightbar.brightness", 0, 255)))
        if "lighting" in section:
            packets += _lightbar_lighting(section["lighting"], persist)
    except ValueError as error:
        if isinstance(error, ProfileError):
            raise
        raise ProfileError(f"lightbar: {error}") from None
    return packets


def _lightbar_lighting(spec: dict, persist: bool) -> list[Packet]:
    kind = spec.get("type") if isinstance(spec, dict) else None
    fields = {
        "static": {"type", "color", "set"}, "off": {"type"}, "disable": {"type"}, "fill": {"type", "color"},
        "direct": {"type", "color", "set"},
        "effect": {"type", "effect", "slot", "zones", "base", "coordinates"},
    }
    if kind not in fields:
        raise ProfileError(f"lightbar.lighting.type must be one of {', '.join(fields)}")
    _check_keys(spec, fields[kind], "lightbar.lighting")
    if kind in ("static", "fill", "direct") and "color" not in spec and "set" not in spec:
        raise ProfileError(f"lightbar.lighting: '{kind}' needs a color")
    color = _color(spec["color"], "lightbar.lighting.color") if "color" in spec else lightbar.BLACK
    overrides = _overrides(spec, lightbar.parse_zones, "lightbar.lighting")
    if kind == "off":
        return lightbar.static_sequence(lightbar.BLACK, persist=persist)
    if kind == "disable":
        return lightbar.disable_sequence(persist=persist)
    if kind == "fill":
        return [lightbar.write_all(color)]
    if kind == "direct":
        zones = {zone: color for zone in range(lightbar.ZONES)} if "color" in spec else {}
        return [lightbar.direct_write({**zones, **overrides})]
    if kind == "static":
        if overrides:
            return lightbar.static_sequence(overrides, base=color, persist=persist)
        return lightbar.static_sequence(color, persist=persist)
    zones = _selection(lightbar.parse_zones, spec["zones"], "lightbar.lighting.zones") if "zones" in spec else None
    return lightbar.effect_sequence(
        effect_from_dict(spec.get("effect")), slot=_int(spec.get("slot", 0), "lightbar.lighting.slot", 0, 17),
        zones=zones, base=_color(spec.get("base", "000000"), "lightbar.lighting.base"),
        coordinates=spec.get("coordinates"), persist=persist)


def _footer(value: Any) -> bytes:
    if value is None:
        return keyboard.DEFAULT_FOOTER
    if value == "none":
        return b""
    try:
        footer = bytes.fromhex(str(value))
    except ValueError:
        raise ProfileError("keyboard.footer: expected 'none' or hex bytes such as '0839'") from None
    if len(footer) > 2:
        raise ProfileError("keyboard.footer: at most two bytes")
    return footer


def build_keyboard(section: dict, persist: bool = False) -> list[Packet]:
    allowed = {"persist", "color_scale", "footer", "lighting"}
    _check_keys(section, allowed, "keyboard")
    persist = _persist(section, persist)
    footer = _footer(section.get("footer"))
    packets: list[Packet] = []
    try:
        if "color_scale" in section:
            packets.append(keyboard.color_scale(_color(section["color_scale"], "keyboard.color_scale")))
        if "lighting" in section:
            packets += _keyboard_lighting(section["lighting"], persist, footer)
    except ValueError as error:
        if isinstance(error, ProfileError):
            raise
        raise ProfileError(f"keyboard: {error}") from None
    return packets


def _keyboard_lighting(spec: dict, persist: bool, footer: bytes) -> list[Packet]:
    kind = spec.get("type") if isinstance(spec, dict) else None
    fields = {
        "static": {"type", "color", "set"}, "off": {"type"}, "fill": {"type", "color"},
        "direct": {"type", "color", "set"},
        "effect": {"type", "effect", "slot", "keys", "base"},
        "reactive": {"type", "color", "react_color", "react_time", "keys", "base"},
    }
    if kind not in fields:
        raise ProfileError(f"keyboard.lighting.type must be one of {', '.join(fields)}")
    _check_keys(spec, fields[kind], "keyboard.lighting")
    if kind in ("static", "fill", "direct") and "color" not in spec and "set" not in spec:
        raise ProfileError(f"keyboard.lighting: '{kind}' needs a color")
    color = _color(spec["color"], "keyboard.lighting.color") if "color" in spec else keyboard.BLACK
    overrides = _overrides(spec, keyboard.parse_keys, "keyboard.lighting")
    keys = _selection(keyboard.parse_keys, spec["keys"], "keyboard.lighting.keys") if "keys" in spec else None
    base = _color(spec.get("base", "000000"), "keyboard.lighting.base")
    if kind == "off":
        return keyboard.off_sequence(persist=persist, footer=footer)
    if kind == "fill":
        return [keyboard.write_all(color)]
    if kind == "direct":
        colors = {code: color for code in keyboard.PHYSICAL} if "color" in spec else {}
        return keyboard.stream_init_sequence(footer) + [keyboard.direct_write({**colors, **overrides})]
    if kind == "static":
        if overrides:
            return keyboard.static_sequence(overrides, base=color, persist=persist, footer=footer)
        return keyboard.static_sequence(color, persist=persist, footer=footer)
    if kind == "reactive":
        react = _color(spec.get("react_color", "ffffff"), "keyboard.lighting.react_color")
        time = _int(spec.get("react_time", 300), "keyboard.lighting.react_time", 0, model.MAX_REACT_TIME)
        return keyboard.reactive_sequence(color, react, react_time=time, keys=keys, base=base,
                                          persist=persist, footer=footer)
    return keyboard.effect_sequence(
        effect_from_dict(spec.get("effect")), slot=_int(spec.get("slot", 0), "keyboard.lighting.slot", 0, 17),
        keys=keys, base=base, persist=persist, footer=footer)


def validate(data: Any) -> dict:
    _check_keys(data, TOP_KEYS, "profile")
    if data.get("version") != VERSION:
        raise ProfileError(f"profile.version must be {VERSION}")
    return data


def load_profile(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as error:
        raise ProfileError(f"cannot read {path}: {error.strerror}") from None
    except json.JSONDecodeError as error:
        raise ProfileError(f"{path}: invalid JSON ({error})") from None
    return validate(data)


def build_all(data: dict) -> dict[str, list[Packet]]:
    """Packets per device present in the profile; also validates every section."""
    validate(data)
    persist = _persist(data, False)
    built = {}
    if "lightbar" in data:
        built["lightbar"] = build_lightbar(data["lightbar"], persist)
    if "keyboard" in data:
        built["keyboard"] = build_keyboard(data["keyboard"], persist)
    return built


def apply_profile(data: dict, *, bar_transport: Callable[[], Any], keyboard_transport: Callable[[], Any]) -> None:
    built = build_all(data)  # validate everything before touching a device
    for name, opener in (("lightbar", bar_transport), ("keyboard", keyboard_transport)):
        if name not in built:
            continue
        transport = opener()
        try:
            for packet in built[name]:
                transport.send(packet)
        finally:
            transport.close()
