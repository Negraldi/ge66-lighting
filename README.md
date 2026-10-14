# ge66-lighting

Linux control for the RGB lighting of the MSI GE66 Raider: the front light bar
(SteelSeries ALC, USB `1038:1132`, 35 zones) and the per-key keyboard
(SteelSeries KLC, USB `1038:1122`).

It contains:

- `docs/PROTOCOL.md`: the HID protocol of both devices.
- `ge66-light`: a Python command line tool with no dependencies beyond Python 3.
- `openrgb-controller/`: an OpenRGB controller in C++ for both devices.

## Status

Tested on one GE66 Raider 10SGS (light bar firmware 2.26, keyboard firmware 2.36).

| | Python tool | OpenRGB controller |
|---|---|---|
| Light bar: per-zone colors, static, color shift, brightness | tested | tested |
| Light bar: breathing, wave direction, effect speed scale | not tested | not tested |
| Keyboard: static, per-key colors | tested | tested |
| Keyboard: color shift | tested | not tested |
| Keyboard: breathing, reactive | not tested | not tested |

Other GE66 editions (`1038:1138`, `1038:1144`) share the light bar description
but were not tested. The chip-refresh light bar (`1038:113c`) is not covered.

## AI disclosure

The code in this repository was written with an AI coding assistant (Claude),
directed and tested on real hardware by the repository owner. It has not been
independently reviewed line by line. The protocol document is the part meant to
be reused: anyone can implement it from scratch.

Because OpenRGB does not accept AI generated submissions, the controller is
published here and not as a merge request.

## Why the light bar never lit with earlier tools

- The GE66 bar has 35 zones. In command `0E`, the third byte is the element
  count; captures from the 30-zone GE76 bar show `1E` there, which reads like a
  region id but is not.
- The vendor sends a color scale (`51 00 FF FF 99`) on init, and the bar needs a
  global brightness (`0C 00 FF`).
- The simplest way to light it is a direct write: feature report
  `0C 00 23 00` followed by 35 entries of `zone R G B`.
- The device is not write-only: output report `10 00` returns the firmware
  version, which makes a safe check that writes reach the firmware.

## Python tool

```
sudo cp contrib/60-ge66-light.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger

./ge66-light bar info
./ge66-light bar init
./ge66-light bar static ffff00 --set 0-7=ff0000,8=ff00ff,9-16=0000ff
./ge66-light bar colorshift --colors rainbow --speed 198 --direction horizontal --scale 40
./ge66-light keyboard static 0000ff
./ge66-light keyboard paint w=ff0000,a=ff0000,s=ff0000,d=ff0000
./ge66-light apply contrib/profile.example.json
```

`--dry-run` prints the packets without opening a device. Nothing is written to
device flash unless `--persist` is given. Firmware update is not implemented.

Profiles are described in `docs/profile-format.md`; `contrib/ge66-light.service`
is a systemd user unit that applies one at login.

Tests: `python3 -m unittest discover -s tests -p 'test_ge66*.py'`

## OpenRGB controller

Written against OpenRGB `release_candidate_1.0rc3.1`.

```
cp -r openrgb-controller/SteelSeriesMSIGE66Controller <OpenRGB>/Controllers/SteelSeriesController/
cd <OpenRGB> && git apply <this repo>/openrgb-controller/SteelSeriesControllerDetect.patch
mkdir build && cd build && qmake ../OpenRGB.pro && make -j$(nproc)
```

The packet builders have a standalone test that compares them byte for byte
with the Python tool:

```
cd openrgb-controller/SteelSeriesMSIGE66Controller
g++ -std=c++17 -I. tests/test_packets.cc SteelSeriesMSIGE66Protocol.cpp -o /tmp/ge66test && /tmp/ge66test
```

## Where the protocol comes from

Static analysis of the device descriptions shipped with SteelSeries GG 121.0.0,
cross-checked with the USB captures users attached to OpenRGB issues #2642 and
#3961, then verified on hardware. This repository contains no SteelSeries or MSI
file, text or key. The work was done for interoperability with hardware the
author owns.

SteelSeries and MSI are trademarks of their owners. This project is not
affiliated with or endorsed by them.

## License

GPL-2.0-or-later, the same as OpenRGB. See `LICENSE`.
