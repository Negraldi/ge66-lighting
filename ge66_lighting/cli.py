"""ge66-light: command line for the GE66 light bar and keyboard."""
from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from typing import Any

from . import effect, hid, keyboard, lightbar, model, profile
from .hid import Packet

USAGE_EXIT = 2
DEVICE_EXIT = 1


class UsageError(ValueError):
    pass


def parse_spec(text: str) -> dict[str, str]:
    """'left=ff0000, 3=00ff00' -> {'left': 'ff0000', '3': '00ff00'} (order kept, later entries win)."""
    result: dict[str, str] = {}
    for token in text.split(","):
        selector, sep, color = token.partition("=")
        if not sep or not selector.strip() or not color.strip():
            raise ValueError(f"expected selector=color, got {token.strip()!r}")
        result[selector.strip()] = color.strip()
    return result


def retry(operation: Callable[[], Any], timeout: float, *, interval: float = 1.0,
          sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic) -> Any:
    """Retry device discovery until `timeout` seconds have passed (devices may enumerate late at login)."""
    started = clock()
    while True:
        try:
            return operation()
        except hid.DeviceNotFound:
            if clock() - started >= timeout:
                raise
            sleep(interval)


def color_arg(text: str) -> str:
    try:
        model.parse_color(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None
    return text


def int_arg(low: int, high: int) -> Callable[[str], int]:
    def parse(text: str) -> int:
        try:
            value = int(text, 0)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
        if not low <= value <= high:
            raise argparse.ArgumentTypeError(f"{value} outside {low}..{high}")
        return value
    return parse


def _common(default: Any) -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true", default=default,
                        help="print the packets instead of opening a device")
    parent.add_argument("--path", metavar="HIDRAW", default=None if default is not argparse.SUPPRESS else default,
                        help="use this /dev/hidrawN node instead of discovering it")
    return parent


def _add_effect_options(parser: argparse.ArgumentParser, target: str) -> None:
    group = parser.add_argument_group("effect")
    group.add_argument("--colors", nargs="+", required=True, metavar="COLOR",
                       help=f"a palette ({', '.join(effect.PALETTES)}) or up to 14 colors")
    group.add_argument("--positions", nargs="+", type=int, metavar="PCT",
                       help="percentage position of each color, 0..100 (default: even)")
    group.add_argument("--speed", type=int_arg(0, 0xFFFF), default=profile.DEFAULT_SPEED,
                       help="ticks of one cycle (default %(default)s; sections last at least 33)")
    group.add_argument("--direction", choices=sorted(effect.DIRECTION_NAMES),
                       help="make it a wave; without it every element changes together")
    group.add_argument("--invert", action="store_true", help="reverse the wave")
    group.add_argument("--focal", nargs=2, type=int_arg(0, 0xFFFF), default=[0, 0], metavar=("X", "Y"),
                       help="wave origin")
    group.add_argument("--scale", type=int_arg(0, 0xFFFF), help="wave size (default 40 with --direction)")
    group.add_argument("--slot", type=int_arg(0, 17), default=0, help="effect slot 0..17 (default %(default)s)")
    group.add_argument("--base", type=color_arg, default="000000",
                       help=f"steady color of the {target} outside the selection")


def _effect_dict(args: argparse.Namespace, kind: str) -> dict:
    colors: Any = args.colors
    if len(colors) == 1 and colors[0] in effect.PALETTES:
        colors = colors[0]
    spec: dict[str, Any] = {"kind": kind, "colors": colors, "speed": args.speed, "invert": args.invert,
                            "focal": list(args.focal), "direction": args.direction}
    if args.positions is not None:
        spec["positions"] = args.positions
    if args.scale is not None:
        spec["scale"] = args.scale
    return spec


def _persist_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--persist", action="store_true",
                        help="also store the configuration in device flash (save_to_flash); default is live only")


def _persist(args: argparse.Namespace) -> bool:
    return getattr(args, "persist", False)


def _require_persist(args: argparse.Namespace, what: str) -> None:
    if not _persist(args):
        raise UsageError(f"{what} writes device flash; pass --persist to confirm")


# ---- light bar ------------------------------------------------------------------------------

def _bar_section(args: argparse.Namespace, lighting: dict) -> list[Packet]:
    return profile.build_lightbar({"lighting": lighting}, persist=_persist(args))


def _bar_set(args: argparse.Namespace) -> dict:
    return {"set": parse_spec(args.set)} if getattr(args, "set", None) else {}


def bar_build(args: argparse.Namespace) -> list[Packet]:
    command = args.command
    if command == "solid":
        return [lightbar.solid(model.parse_color(args.color))]
    if command == "paint":
        return _bar_section(args, {"type": "direct", "set": parse_spec(args.spec)})
    if command == "fill":
        return [lightbar.write_all(model.parse_color(args.color))]
    if command == "static":
        return _bar_section(args, {"type": "static", "color": args.color, **_bar_set(args)})
    if command in ("colorshift", "breathe"):
        lighting = {"type": "effect", "effect": _effect_dict(args, command), "slot": args.slot, "base": args.base}
        if args.zones:
            lighting["zones"] = args.zones
        if args.coordinates is not None:
            lighting["coordinates"] = args.coordinates
        return _bar_section(args, lighting)
    if command == "off":
        return _bar_section(args, {"type": "off"})
    if command == "disable":
        return _bar_section(args, {"type": "disable"})
    if command == "brightness":
        return [lightbar.global_brightness(args.level)]
    if command == "color-scale":
        return [lightbar.color_scale(model.parse_color(args.color))]
    if command == "init":
        return lightbar.init_sequence()
    if command == "reset":
        return [lightbar.reset_current_lighting_mode()]
    if command == "restart":
        return [lightbar.restart_lighting_active()]
    if command == "reset-device":
        return [lightbar.reset_alc()]
    if command == "save":
        _require_persist(args, "save")
        return [lightbar.save_to_flash()]
    if command == "lid":
        return [lightbar.lid_close() if args.state == "close" else lightbar.lid_open()]
    if command == "coordinates":
        return [lightbar.zone_coordinates([(zone * args.spacing, 0) for zone in range(lightbar.ZONES)])]
    raise AssertionError(command)


def _add_bar_commands(sub: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=help_text, description=help_text, parents=[common])

    add("info", "show the hidraw node and firmware version")
    add("init", "vendor init: color scale, then full brightness")
    add("solid", "live: one color on every zone (direct_write)").add_argument("color", type=color_arg)
    add("paint", "live: per-zone colors, e.g. 0-4=ff0000,left=00ff00").add_argument("spec")
    add("fill", "live: write_all_illumination").add_argument("color", type=color_arg)
    static = add("static", "steady colors through the zone table")
    static.add_argument("color", type=color_arg)
    static.add_argument("--set", metavar="SPEC", help="per-zone overrides, e.g. left=0000ff,17=ff0000")
    _persist_flag(static)
    for kind, text in (("colorshift", "fade between colors, optionally as a wave"),
                       ("breathe", "fade each color in and out, optionally as a wave")):
        parser = add(kind, text)
        _add_effect_options(parser, "bar")
        parser.add_argument("--zones", help="zones to animate, e.g. 0-17 or left (default all)")
        parser.add_argument("--coordinates", action=argparse.BooleanOptionalAction, default=None,
                            help="write zone coordinates (default: only when --direction is given)")
        _persist_flag(parser)
    for name, text in (("off", "steady black"), ("disable", "vendor disable: empty slot 0 and steady black")):
        _persist_flag(add(name, text))
    add("brightness", "global brightness").add_argument("level", type=int_arg(0, 255))
    scale = add("color-scale", "color scale (default ffff99: vendor value, white looked blue)")
    scale.add_argument("color", type=color_arg, nargs="?", default="ffff99")
    add("reset", "reset_current_lighting_mode: leave direct mode")
    add("restart", "restart_lighting_active")
    add("reset-device", "reset_alc (what the vendor sends on lid open)")
    _persist_flag(add("save", "save_to_flash: store the configuration (needs --persist)"))
    add("lid", "apply the sleep_lid_close behavior").add_argument("state", choices=("close", "open"))
    add("coordinates", "write zone coordinates used by waves").add_argument(
        "--spacing", type=int_arg(0, 0xFFFF), default=1, help="distance between zones (default %(default)s)")


# ---- keyboard -------------------------------------------------------------------------------

def _kb_section(args: argparse.Namespace, lighting: dict) -> list[Packet]:
    section: dict[str, Any] = {"lighting": lighting}
    if getattr(args, "footer", None) is not None:
        section["footer"] = args.footer
    return profile.build_keyboard(section, persist=_persist(args))


def kb_build(args: argparse.Namespace) -> list[Packet]:
    command = args.command
    if command == "solid":
        return _kb_section(args, {"type": "direct", "color": args.color})
    if command == "paint":
        return _kb_section(args, {"type": "direct", "set": parse_spec(args.spec)})
    if command == "static":
        return _kb_section(args, {"type": "static", "color": args.color, **_bar_set(args)})
    if command in ("colorshift", "breathe"):
        lighting = {"type": "effect", "effect": _effect_dict(args, command), "slot": args.slot, "base": args.base}
        if args.keys:
            lighting["keys"] = args.keys
        return _kb_section(args, lighting)
    if command == "reactive":
        lighting = {"type": "reactive", "color": args.color, "react_color": args.react_color,
                    "react_time": args.react_time, "base": args.base}
        if args.keys:
            lighting["keys"] = args.keys
        return _kb_section(args, lighting)
    if command == "off":
        return _kb_section(args, {"type": "off"})
    if command == "fill":
        return [keyboard.write_all(model.parse_color(args.color))]
    if command == "color-scale":
        return [keyboard.color_scale(model.parse_color(args.color))]
    if command == "reset":
        return [keyboard.reset_current_lighting_mode()]
    if command == "restart":
        return [keyboard.restart_lighting()]
    if command == "restart-active":
        return [keyboard.restart_lighting_active()]
    if command == "lighting-reset":
        return [keyboard.lighting_reset()]
    if command == "save":
        _require_persist(args, "save")
        return [keyboard.save_to_flash()]
    if command == "layout":
        if not args.experimental:
            raise UsageError("layout is untested (the vendor driver does not use it); pass --experimental")
        return [keyboard.write_layout(args.number)]
    raise AssertionError(command)


def _add_keyboard_commands(sub: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    def add(name: str, help_text: str, tables: bool = False) -> argparse.ArgumentParser:
        parser = sub.add_parser(name, help=help_text, description=help_text, parents=[common])
        if tables:
            parser.add_argument("--footer", metavar="HEX|none",
                                help="two-byte trailer of the table reports (default 0839; the vendor capture has 0855)")
            _persist_flag(parser)
        return parser

    add("info", "show the hidraw node and firmware version")
    add("list-keys", "list key names and HID codes")
    add("solid", "live: one color on every key (host-stream mode + direct_write)", True).add_argument(
        "color", type=color_arg)
    add("paint", "live: per-key colors, e.g. esc=ff0000,f1-f4=0000ff", True).add_argument("spec")
    static = add("static", "steady colors through the element tables", True)
    static.add_argument("color", type=color_arg)
    static.add_argument("--set", metavar="SPEC", help="per-key overrides, e.g. w,a,s,d=ffffff")
    for kind, text in (("colorshift", "fade between colors, optionally as a wave"),
                       ("breathe", "fade each color in and out, optionally as a wave")):
        parser = add(kind, text, True)
        _add_effect_options(parser, "keyboard")
        parser.add_argument("--keys", help="keys to animate, e.g. letters or w,a,s,d (default all)")
    reactive = add("reactive", "keys rest at COLOR and flash when pressed", True)
    reactive.add_argument("color", type=color_arg)
    reactive.add_argument("--react-color", type=color_arg, required=True)
    reactive.add_argument("--react-time", type=int_arg(0, model.MAX_REACT_TIME), default=300, help="ms")
    reactive.add_argument("--keys", help="keys to make reactive (default all)")
    reactive.add_argument("--base", type=color_arg, default="000000", help="steady color of the other keys")
    add("off", "steady black", True)
    add("fill", "live: write_all_illumination").add_argument("color", type=color_arg)
    scale = add("color-scale", "color scale (GE66 default 8ccc99)")
    scale.add_argument("color", type=color_arg, nargs="?", default="8ccc99")
    add("reset", "reset_current_lighting_mode: leave direct mode")
    add("restart", "restart_lighting")
    add("restart-active", "restart_lighting_active")
    add("lighting-reset", "lighting_reset fallback")
    _persist_flag(add("save", "save_to_flash: store the configuration (needs --persist)"))
    layout = add("layout", "write_layout_N (untested)")
    layout.add_argument("number", type=int_arg(0, keyboard.LAYOUTS - 1))
    layout.add_argument("--experimental", action="store_true")


def list_keys() -> None:
    physical = set(keyboard.PHYSICAL)
    print(f"{'name':<16} {'hid':<5} {'status':<9} block")
    for name, code in sorted(keyboard.NAMES.items(), key=lambda item: item[1]):
        block = next(i + 1 for i, codes in enumerate(keyboard.BLOCKS) if code in codes)
        print(f"{name:<16} 0x{code:02x}  {'physical' if code in physical else 'absent':<9} {block}")


# ---- driver ---------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ge66-light", description="Control the MSI GE66 Raider light bar and keyboard. "
        "Nothing is written to device flash unless --persist is given.",
        parents=[_common(False)])
    sub = parser.add_subparsers(dest="device", required=True)
    leaf = _common(argparse.SUPPRESS)
    bar = sub.add_parser("bar", help="light bar (ALC 1038:1132, 35 zones)", parents=[leaf])
    _add_bar_commands(bar.add_subparsers(dest="command", required=True), leaf)
    board = sub.add_parser("keyboard", help="keyboard (KLC 1038:1122)", parents=[leaf])
    _add_keyboard_commands(board.add_subparsers(dest="command", required=True), leaf)
    apply_parser = sub.add_parser("apply", help="apply a JSON profile (docs/profile-format.md)", parents=[leaf])
    apply_parser.add_argument("profile")
    apply_parser.add_argument("--wait", type=float, default=0, metavar="SECONDS",
                              help="keep looking for the devices this long (useful at login)")
    return parser


def _opener(kind: str, args: argparse.Namespace, wait: float = 0):
    product = lightbar.PRODUCT_ID if kind == "bar" else keyboard.PRODUCT_ID

    def open_once():
        return hid.open_transport(hid.VENDOR_ID, product, args.dry_run, args.path)

    return (lambda: retry(open_once, wait)) if wait else open_once


def _run_device(args: argparse.Namespace) -> None:
    kind = args.device
    if args.command == "list-keys":
        list_keys()
        return
    cls = lightbar.LightBar if kind == "bar" else keyboard.Keyboard
    if args.command == "info":
        device = cls(_opener(kind, args)())
        try:
            version = device.fw_version()
        finally:
            device.close()
        label = "lightbar" if kind == "bar" else "keyboard"
        path = getattr(device.transport, "path", "dry-run")
        text = f"{version[0]}.{version[1]}" if version else "unknown (no reply)"
        print(f"{label} {path}: firmware {text}")
        return
    packets = (bar_build if kind == "bar" else kb_build)(args)
    device = cls(_opener(kind, args)())
    try:
        device.apply(packets)
    finally:
        device.close()


def _run_apply(args: argparse.Namespace) -> None:
    data = profile.load_profile(args.profile)
    profile.apply_profile(data, bar_transport=_opener("bar", args, args.wait),
                          keyboard_transport=_opener("keyboard", args, args.wait))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.device == "apply":
            _run_apply(args)
        else:
            _run_device(args)
    except ValueError as error:  # includes UsageError and ProfileError
        print(f"error: {error}", file=sys.stderr)
        return USAGE_EXIT
    except hid.DeviceNotFound as error:
        print(f"error: {error}", file=sys.stderr)
        return DEVICE_EXIT
    except PermissionError as error:
        print(f"error: {error}; check the udev rule for the hidraw node (TAG+=\"uaccess\")", file=sys.stderr)
        return DEVICE_EXIT
    except OSError as error:
        print(f"error: device I/O failed: {error}", file=sys.stderr)
        return DEVICE_EXIT
    return 0
