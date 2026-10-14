# ge66-light profile format

A profile is one JSON file applied with `ge66-light apply profile.json`. Unknown
fields are rejected so typos do not silently do nothing. Validate without touching
hardware: `ge66-light apply --dry-run profile.json` prints the packets instead.

Nothing is written to device flash unless `persist` is `true` (top level or per
device). Without it the lighting is live: it survives until power cycle or until
another tool changes it.

## Top level

| Field | Type | Meaning |
|---|---|---|
| `version` | `1` | required |
| `name`, `description` | string | free text, ignored |
| `persist` | bool | default `false`; also send `save_to_flash` after the configuration |
| `lightbar` | object | settings for the light bar; omit to leave the bar alone |
| `keyboard` | object | settings for the keyboard; omit to leave the keyboard alone |

Colors are `"#rrggbb"`, `"rrggbb"`, `"r,g,b"`, a name (`red green blue yellow cyan
magenta orange purple pink white black`) or `[r, g, b]`.

## `lightbar`

| Field | Meaning |
|---|---|
| `persist` | overrides the top-level value |
| `color_scale` | color, vendor value `ffff99` (white looked blue) |
| `brightness` | 0..255 (`global_brightness`) |
| `lighting` | one lighting object, below |

Zone selectors: `"0-4,10"`, `"left"` (17..0), `"right"` (18..34), `"all"`; the
bar has 35 zones, 0 on the left.

| `lighting.type` | Fields | Behavior |
|---|---|---|
| `static` | `color`, `set` | steady colors through the zone table (settings_mask 1). `set` maps selectors to colors over the base `color`; later entries win |
| `effect` | `effect`, `slot` (0..17, default 0), `zones` (default all), `base` (default black), `coordinates` | writes the effect into a slot and points the zones at it |
| `direct` | `color`, `set` | host-stream write (`direct_write`), volatile |
| `fill` | `color` | `write_all_illumination`, volatile |
| `off` | | steady black through the zone table |
| `disable` | | vendor "disable": empty effect slot 0 and steady black |

`coordinates` is `true`, `false`, a list of 35 `[x, y]` points, or omitted
(written for effects that have a direction, default zone i at `[i, 0]`).

## `keyboard`

| Field | Meaning |
|---|---|
| `persist` | overrides the top-level value |
| `color_scale` | color, GE66 default `[140, 204, 153]` |
| `footer` | trailer of the table reports: `"none"` or hex bytes; default `"0839"` (see PROTOCOL.md) |
| `lighting` | one lighting object, below |

Key selectors: names (`esc`, `w`, `f1`, `lshift`, `fn`, ...; list them with
`ge66-light keyboard list-keys`), ranges (`f1-f4`), groups (`all` = the 84 physical
GE66 keys, `everything`, `letters`, `numbers`, `fkeys`, `arrows`, `modifiers`)
and `0xNN` HID usage codes, comma separated.

| `lighting.type` | Fields | Behavior |
|---|---|---|
| `static` | `color`, `set` | steady colors through the four element tables |
| `effect` | `effect`, `slot`, `keys` (default all), `base` | effect slot plus tables |
| `reactive` | `color`, `react_color` (white), `react_time` (ms, 0..2000, default 300), `keys`, `base` | keys rest at `color` and flash on key press |
| `direct` | `color`, `set` | puts keys in host-stream mode, then one `direct_write` |
| `fill` | `color` | `write_all_illumination` |
| `off` | | steady black |

## `effect`

| Field | Meaning |
|---|---|
| `kind` | `colorshift` (fade between colors) or `breathe` (fade each color in and out of black) |
| `colors` | palette name (`rainbow police fire ocean`) or a list of up to 14 colors |
| `positions` | optional percentages 0..100, one per color, not decreasing; default evenly spread. A first position above 0 adds a hold section |
| `speed` | total ticks of one cycle, 0..65535, default 200. Every section lasts at least 33 ticks |
| `direction` | `null` (all elements change together), `horizontal`, `vertical` or `radial` (a wave) |
| `invert` | reverse the wave |
| `focal` | `[x, y]` wave origin, default `[0, 0]` |
| `scale` | wave size, default 40 when `direction` is set |

The engine can send 16 sections: `colorshift` allows up to 15 colors (14 with a
hold), `breathe` up to 8 colors (7 with a hold).

## Examples

Light bar only, steady purple on the left half and orange on the right:

```json
{
  "version": 1,
  "lightbar": {
    "brightness": 255,
    "lighting": { "type": "static", "color": "000000", "set": { "left": "8000ff", "right": "ff8000" } }
  }
}
```

Keyboard only, breathing red/blue on the arrow keys over a dim steady base:

```json
{
  "version": 1,
  "keyboard": {
    "lighting": {
      "type": "effect",
      "effect": { "kind": "breathe", "colors": ["ff0000", "0000ff"], "speed": 300 },
      "keys": "arrows",
      "base": "000020"
    }
  }
}
```

Both devices, with an explicit opt-in to store the configuration in flash:

```json
{
  "version": 1,
  "persist": true,
  "lightbar": { "lighting": { "type": "effect", "effect": { "kind": "breathe", "colors": "fire", "speed": 600 } } },
  "keyboard": { "lighting": { "type": "reactive", "color": "100010", "react_color": "ffffff", "react_time": 250 } }
}
```
