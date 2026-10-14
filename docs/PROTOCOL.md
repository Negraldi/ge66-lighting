# GE66 lighting protocol: light bar (ALC 1038:1132) and keyboard (KLC 1038:1122)

Recovered from SteelSeries GG 121.0.0 (`SteelSeriesGG121.0.0Setup.exe`,
sha256 `2fffd8fe…c21907`). Static analysis only; the installer was never run.
Implemented by the `ge66_lighting/` package; every byte layout below is pinned by a
test in `tests/test_ge66_*.py`.

Spec file names refer to the vendor device descriptions, written as
`file:line` (lines of the `*.device.lsp` files; lsp is dropped for brevity).

## Provenance

The byte layouts were established by static analysis of the device descriptions
that ship with SteelSeries GG 121.0.0, cross-checked against public USB captures
of the vendor software on sibling models (OpenRGB issues #2642 and #3961) and
verified on a GE66 Raider 10SGS (light bar firmware 2.26, keyboard firmware 2.36).
The vendor software was never executed. No vendor file, text or key is included
here; "spec" references below name the vendor description and line a layout was
read from, so that others can check it against their own copy.

Three builtins of the vendor description language were settled against the
captures: integer `/` truncates toward zero, uint16 is little endian, and the
effect bytes reproduce three vendor packets exactly.

## Which spec applies

### Light bar

PID 0x1132 = `msi-ge66-alc-id` (`msi-ge66-alc:1`), standard edition. Colie (0x1138)
and Disco (0x1144) are listed on the same `(device ...)` form (`msi-ge66-alc:6`), so
they share every packet. `msi-ge66-alc-chip-refresh` (0x113c) is a different
hardware revision and is not covered. Supported firmware `2.26.x`
(`msi-ge66-alc:22`); the unit under test reports 2.26.

### Keyboard

The ids do not match one to one:

- `ss-klc-base:79` names `(actual-klc-pid) 0x10381122`: that is the *physical*
  device. In the engine it is the generic stub `msi-klc` (`msi-klc:1-27`), which only
  knows `fw_version` (`10 00`).
- The lighting spec is the virtual device `msi-ge66-klc` (`msi-ge66-klc:1`, PID
  0x10382034, bootloader 0x10382035). It writes to the hardware through
  `fw_update.appPIDid 0x1122` (`msi-ge66-klc:14`), i.e. the physical 1038:1122.
  The SQL migration `3.17.3` registers it as `physical_devices(product_id
  272113716 = 0x10382034, 'MSI GE66')`.
- `msi-ge66-klc` includes `msi-gs65-klc` (`msi-ge66-klc:7`), which includes
  `ss-klc-base` (`msi-gs65-klc:7`). Colie (0x10382037) and Disco (0x10382041) include
  `msi-ge66-klc` unchanged.

Effective constants for the GE66 keyboard: `number-of-elements` 125
(`msi-gs65-klc:11`, `ss-klc-base:11`), color scale 0.55/0.8/0.6 → 140/204/153
(`msi-gs65-klc:14-16`), key matrix of `msi-ge66-klc:64-73` (84 physical keys).
A physical keyboard is "layout 0" (English) unless the OS region is Japanese
(`ss-klc-base:39-46`); layouts are not read from the device.

## Transport

Both HID interfaces (interface 0, usage page 0xFFC0) have no report ids. Report
descriptors (`/sys/.../report_descriptor`): 64-byte input, 64-byte output, 524-byte
feature report.

| Kind | Size | Used for | Write |
|---|---|---|---|
| output | 64 | commands | `write(fd, 00 + 64 bytes)` |
| feature | 524 | tables, effects, direct writes | `HIDIOCSFEATURE(525)` with `00 + 524 bytes` |
| input | 64 | `fw_version` reply | `read`, `fw_minor` then `fw_major` |

10 ms between commands (`ss-alc-base:275`, `ss-klc-base:16`). Multi-byte fields are
little endian. The hidraw node is resolved from sysfs by `HID_ID=0003:00001038:0000PPPP`
and USB interface `:1.0`; node numbers change across boots.

The KLC structs start with `00 0B 00` (output) or `00 0C 00` (feature) before the
command byte (`ss-klc-base:112-114`, `205-208`, ...). Those bytes are not on the
wire: see *Spec versus captures*. All layouts below are the wire bytes after the
hid report id, as the tool sends and as the captures show.

## Shared structures

| Struct | Layout | Source |
|---|---|---|
| `initial_lighting` | `R G B` | common_lighting:21-25 |
| `reactive_lighting` | `R G B time(u16, 0..2000)` | common_lighting:28-33 |
| `lighting_element_info` | initial(3) reactive(5) `effect_index`(0..0x11) `settings_mask`(0,1,2,4,8,16) = 10 bytes | common_lighting:36-41 |
| `element_info_block` | info(10) `lockmask` `zone`/`hid` = 12 bytes | ss-alc-base:313-317, ss-klc-base:197-201 |
| `lighting_effect` | 69 bytes, below | common_lighting:54-66 |

`settings_mask`: 0 = run the effect slot `effect_index`, 1 = steady `init` color,
2 = host stream (direct writes), 4 = override, 8 = reactive, 16 reserved
(common_lighting:10-14). Values seen in the engine's default configs: 0, 1, 2, 8.
`effect_index` is a slot 0..17 (`effect_18` exists but the element field stops at
0x11).

### `lighting_effect` (69 bytes) → effect slot (151 bytes)

```
struct: type has_direction direction_type direction_inverted focal_x(u16) focal_y(u16)
        speed(u16) scale(u16) num_colors colors[14]*RGB positions[14]
type: 0 disabled, 1 colorshift, 2 breathe; direction_type: 0 horizontal, 1 vertical, 2 radial
```

The engine converts it with `get-effect-bytes` (fancy_lighting_engine:287-293) to 151
bytes: 16 sections × 8 bytes, then `R16 G16 B16` (first color × 16), `FF 00`, the
four focal-point bytes, `x_scale(u16) y_scale(u16)`, the scale bytes, `num_sections(u16)`,
`total_ticks(u16)`, `direction_inverted`.

Section = `dR dG dB 00 speed(u16) next 00`, where `d = trunc(16·(final − initial) / speed)`
as a signed byte, `speed = max(ticks·(Δposition%) / 100, 33)`, `next` = following
section (0 for the last).

- colorshift (fancy_lighting_engine:11-140): one section per color moving to the next
  color, last one back to color 0; if `positions[0] ≠ 0` a leading hold section is
  added.
- breathe (fancy_lighting_engine:143-283): two sections per color (color → black →
  next color), speed from half the position gap; same optional hold section.
- x/y scaling: horizontal `(1,0)`, vertical `(0,1)`, radial `(1,1)`, none `(0,0)`.
- At most 16 sections, so breathe takes at most 8 colors (7 with a hold).

Not implemented: the reverse transforms that read an effect back
(fancy_lighting_engine:295-676), used for onboard-profile readback.

## Light bar commands (ALC, 35 zones, index 0 left … 34 right)

Output reports (64 bytes):

| Wire bytes | Name | Spec | Implemented as |
|---|---|---|---|
| `10 00` | fw_version (reply `minor major`) | ss-alc-base:284-294 | `bar info` |
| `50 00 R G B` | write_all_illumination | ss-alc-base:376-385 | `bar fill` |
| `0C 00 LL` | global_brightness | ss-alc-base:304-311 | `bar brightness` |
| `51 00 R G B` | color_scale (vendor `FF FF 99`) | msi-ge66-alc:66-76 | `bar color-scale`, `bar init` |
| `0D 00 02` | reset_current_lighting_mode | ss-alc-base:452-459 | `bar reset`; closes every sequence |
| `0D 00 00` | restart_lighting_active | ss-alc-base:461-464 | `bar restart` |
| `09 00` | save_to_flash | ss-alc-base:296-302 | `bar save --persist`, `--persist` |
| `F1 00` | reset_alc | msi-ge66-alc:47-53 | `bar reset-device` |

Feature reports (524 bytes):

| Wire bytes | Name | Spec | Implemented as |
|---|---|---|---|
| `0E 00 23 00` + 35 × block(12) | zone_illumination_active (count, layer 0) | msi-ge66-alc:79-88 | zone table in `static`/`effect`/`off` |
| `0C 00 N 00` + N × `zone R G B` | direct_write | msi-ge66-alc:90-99, ss-alc-base:339-348 | `bar solid`, `bar paint` |
| `0B 00 slot 00` + 151 effect bytes | effect_0 … effect_18 | ss-alc-base:387-446 | `colorshift`, `breathe`, `disable` |
| `0D 00 23 00` + 35 × `x(u16) y(u16)` | zone_coordinates | msi-ge66-alc:101-115 | `bar coordinates`; written with wave effects |

`zone_coordinates` default: zone i at (i, 0), taken from the engine's default config
for the 35-zone bar (SQL `3.17.10`); the wave units are otherwise not documented.

Host-side behavior from the same spec, exposed as `bar lid close|open`:
`sleep_lid_close` (`msi-ge66-alc:117-127`, default 1 in
`configurationMigrations/msi_ge66_alc.migration`): on lid close the vendor sends
`global_brightness 0`; on lid open `reset_alc` (`msi-ge66-alc:36-45`). Vendor init
sends `color_scale` (`msi-ge66-alc:27-28`).

## Keyboard commands (KLC, GE66 key map)

Output reports (64 bytes):

| Wire bytes | Name | Spec | Implemented as |
|---|---|---|---|
| `10 00` | fw_version (reply `minor major`) | msi-klc:15-26 | `keyboard info` |
| `51 00 R G B` | color_scale (GE66 `8C CC 99`) | ss-klc-base:110-122, msi-gs65-klc:14-16 | `keyboard color-scale` |
| `09 00` | save_to_flash | ss-klc-base:126-134 | `keyboard save --persist`, `--persist` |
| `08 00` | restart_lighting | ss-klc-base:290-298 | `keyboard restart` |
| `50 00 R G B` | write_all_illumination | ss-klc-base:352-363 | `keyboard fill` |
| `0D 00 02` | reset_current_lighting_mode | ss-klc-base:430-439 | `keyboard reset`; closes every sequence |
| `0D 00 00` | restart_lighting_active | ss-klc-base:441-444 | `keyboard restart-active` |
| `40 00` | lighting_reset (fallback) | ss-klc-base:454-462 | `keyboard lighting-reset` |
| `06 00 n` | write_layout_0 … 3 | ss-klc-base:168-189 | `keyboard layout N --experimental` |

Feature reports (524 bytes):

| Wire bytes | Name | Spec | Implemented as |
|---|---|---|---|
| `0E 00 n 00` + n × block(12) + trailer | key_illumination_block_1 … 4 (n = 42, 19, 24, 11) | ss-klc-base:205-273 | `static`, `effect`, `reactive`, stream init |
| `0C 00 n 00` + n × `hid R G B` | direct_write | ss-klc-base:309-320 | `keyboard solid`, `paint` |
| `0B 00 slot 00` + 151 effect bytes | effect_0 … effect_18 | ss-klc-base:365-424 | `colorshift`, `breathe` |

Element tables. The four tables are the same wire command with different keys and
lengths. Membership (`ss-klc-base:203-273` comments, filled from the `msi_ge66_klc`
default settings in SQL `3.17.3`):

1. 42 keys: HID 4-39 (letters, digits), 58-63 (F1-F6)
2. 19 keys: HID 64-82 (F7-F12, printscreen … up)
3. 24 keys: 41-48, 51-57, 102 (power), 224-230 (modifiers), 240 (fn)
4. 11 keys: 40, 49, 50, 100, 135-139, 144, 145 (layout-dependent keys). The spec
   holds one 11-key variant per layout and sends the current one; the key list is
   the same for all four, only the element infos differ.

All 96 keys are written each time (as the vendor does); 84 exist on the GE66 (the
`msi-ge66-klc:64-73` matrix); the 12 absent ones are printscreen, scrolllock, pause,
delete, intl-hash and the Japanese/Korean keys (`keyboard list-keys`).

Other table behavior used by the tool:

- steady: `settings_mask 1`, `effect_index 1` (as in the vendor capture)
- effect: `settings_mask 0`, `effect_index = slot`
- reactive: `settings_mask 8`, `effect_index 0`, `init` = resting color, `react` +
  `time` (default 300 ms), the combination seen in the engine's default configs
- host stream: `settings_mask 2` for every key, then `reset_current_lighting_mode`,
  then one `direct_write` (`ss-klc-base:629-656`, `create-key-block-initialization`)
- trailer: the last two bytes of the 524-byte report; see below

## Sequences the tool sends

| Action | Packets |
|---|---|
| live apply (default) | [effect slot] [coordinates] element table(s), `0D 00 02` |
| `--persist` | the same with `09 00` before the final `0D 00 02` |
| vendor deploy (captures) | slots and tables in any order, then `09 00` |
| host stream (bar) | `direct_write` only (this is what lit the bar on hardware) |
| host stream (keyboard) | stream init tables, `0D 00 02`, `direct_write` |

`reset_current_lighting_mode` as the live-apply closer comes from `post-live-deploy`
(`ss-alc-base:448-450`, `ss-klc-base:426-428`); the vendor's committing deploy ends in
`save_to_flash`. Whether the tables take effect with only the reset has not been
confirmed on hardware.

## Spec versus captures

1. **KLC selector bytes.** The spec prefixes KLC structs with `00 0B 00` (output) and
   `00 0C 00` (feature); the report id `00` is consumed by the OS, which would leave
   `0B 00 …` / `0C 00 …`. The vendor capture of a sibling KLC
   (`Keyboard_Steady_RED_Config.pcapng`, a GE76 using the same `ss-klc-base`) shows
   `0E 00 24 00 …` and `09 00 …`, and `msi-perkeyrgb` (working on this unit) builds
   `0E 00 <n> 00 …` too. Decision: the selector bytes are not sent. Hardware check of
   the new tables is still pending.
2. **Table trailer.** Not in the spec. Captured KLC feature reports end in `08 55`;
   `msi-perkeyrgb` sends `08 39`; the capture's output report `09` also has a stray
   last byte (`2D`). Looks like uninitialized buffer content. The tool sends `08 39`
   (known good here); `--footer`/`footer` overrides it. The Aurora bar captures have
   no trailer.
3. **Table lengths.** The capture's tables are 36/42/11/24 (GE76: `msi-ge63-klc:28-37`
   overrides block 2 with 36 keys including the numpad). The GE66 spec keeps block 2
   at 19 (`ss-klc-base:226`), which the tool follows. Blocks 1, 3 and 4 equal the
   capture byte for byte (tests).
4. **Steady `effect_index`.** The keyboard capture uses 1; the bar capture alternates
   2 and 0 by zone parity; `msi-perkeyrgb` uses 0. The value is ignored for
   `settings_mask 1` as far as is known; the tool uses 1 for keys and 0 for zones.
5. **`save_to_flash` as refresh.** `msi-perkeyrgb` ends every update with `09 00 …`;
   the vendor commit is the same packet. The tool only sends it with `--persist`.
6. **Bar size.** The captures are 30-zone bars (`0E 00 1E 00`, GE76); the GE66 has 35
   (`0E 00 23 00`). The effect bytes and element layout are otherwise identical.
7. **Unused keys.** In the capture the vendor marks keys absent on that keyboard with
   `G = 0xAA` (and `settings_mask 0` for two of them). The tool has no such marker.
8. **Not seen in captures:** reactive `time` byte order (all captured values are 0),
   any `zone_coordinates` or output-report variants. Little endian is assumed like
   every other uint16 in the captures.

## Verified on hardware

- 2026-10-13, light bar: `fw_version` returned 2.26; `color_scale` +
  `global_brightness FF` + `direct_write` (35 zones, red) lit the bar red with the
  lid closed.
- Everything else, including all effects, the element tables and the whole
  keyboard path of the new package, is verified offline only.

## Not implemented

| Item | Spec | Why |
|---|---|---|
| `fw_update` (bar, keyboard, bootloaders 0x1133, 0x1123, 0x10382035) | msi-ge66-alc:55-64, 237-263; msi-ge66-klc:12-21, 212-236 | firmware update is out of scope and unsafe |
| Reverse effect transforms (readback) | fancy_lighting_engine:295-676 | only used to read onboard profiles |
| `direct_write_raw` | ss-klc-base:322-333 | same wire command as `direct_write` with a prebuilt body |
| `keys_direct_write` | ss-alc-base:351-374, ss-klc-base:466-474 | host-side emulation of `direct_write` for cooldown timers |
| `idle_time` | ss-klc-base:193-194 | empty struct: no idle illumination, no wire format |
| `button_mappings` | msi-gs65-klc:19-20 | driver-side, stubbed |
| `layout` read | ss-klc-base:157-164 | the spec answers a constant, not a device read |
| `set_key_blink`, `reset_all_illumination` | standard-boilerplate:192-199 | empty stubs |
| `bar` `sleep_lid_close` as a daemon | msi-ge66-alc:117-127 | the setting is host logic; `bar lid close|open` sends its packets |
| Prism Sync (zone data, 33 ms streaming) | msi-ge66-alc:129-177, ss-klc-base:476-612 | host-side engine, not a device setting |
| GameSense interfaces (`MSI-ALC-Interface`, `MSI-KLC-Interface`, key zone names) | ss-alc-base:474-509, ss-klc-base:620-697, msi-ge66-klc:93-210 | host-side game integration |
| Japanese layout replacements | msi-ge66-klc:75-91 | only affect which matrix cell a key shows in the UI; key membership of the tables is layout independent |
| `msi-ge66-alc-chip-refresh` (0x113c) | msi-ge66-alc-chip-refresh:1-53 | different PID/firmware (1.0.x); not this unit |
| `radial` unit conversion for focal/scale | n/a | raw values only; the vendor UI units are unknown |

## Open

- Does the live sequence (tables + `0D 00 02`, no `09 00`) change the lighting on
  both devices? The hardware-visible order is: bar effect, keyboard static,
  keyboard effect.
- Which of `08 39` / `08 55` / none the keyboard needs for tables.
- Whether wave effects on the bar need `zone_coordinates` written first.
