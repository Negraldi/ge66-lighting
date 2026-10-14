/*---------------------------------------------------------*\
| SteelSeriesMSIGE66Protocol.h                              |
|                                                           |
|   Packet builders and effect engine for the MSI GE66      |
|   Raider light bar (SteelSeries ALC, 1038:1132) and       |
|   keyboard (SteelSeries KLC, 1038:1122)                   |
|                                                           |
|   Pure functions, no hidapi or RGBController dependency.  |
|   Builders fill the bytes that follow the HID report ID.  |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include <vector>

/*---------------------------------------------------------*\
| Report sizes without the leading report ID                |
\*---------------------------------------------------------*/
#define MSIGE66_OUTPUT_SIZE                 64
#define MSIGE66_FEATURE_SIZE                524

/*---------------------------------------------------------*\
| Effect engine limits                                      |
\*---------------------------------------------------------*/
#define MSIGE66_EFFECT_SIZE                 151
#define MSIGE66_EFFECT_STRUCT_SIZE          69
#define MSIGE66_EFFECT_SLOTS                18
#define MSIGE66_EFFECT_MAX_COLORS           14
#define MSIGE66_EFFECT_MAX_SECTIONS         16
#define MSIGE66_EFFECT_MIN_SECTION_SPEED    33

/*---------------------------------------------------------*\
| Devices                                                   |
\*---------------------------------------------------------*/
#define MSIGE66_BAR_ZONES                   35
#define MSIGE66_KEY_BLOCK_COUNT             4
#define MSIGE66_KEY_COUNT                   96
#define MSIGE66_KEY_REACT_TIME_DEFAULT      300
#define MSIGE66_KEY_REACT_TIME_MAX          2000

enum
{
    MSIGE66_PACKET_OUTPUT                   = 0,
    MSIGE66_PACKET_FEATURE                  = 1,
};

/*---------------------------------------------------------*\
| lighting_element_info.settings_mask values                |
\*---------------------------------------------------------*/
enum
{
    MSIGE66_MASK_EFFECT                     = 0,
    MSIGE66_MASK_STEADY                     = 1,
    MSIGE66_MASK_HOST_STREAM                = 2,
    MSIGE66_MASK_REACTIVE                   = 8,
};

/*---------------------------------------------------------*\
| lighting_effect.type and direction_type values            |
\*---------------------------------------------------------*/
enum
{
    MSIGE66_EFFECT_DISABLED                 = 0,
    MSIGE66_EFFECT_COLORSHIFT               = 1,
    MSIGE66_EFFECT_BREATHE                  = 2,
};

enum
{
    MSIGE66_DIRECTION_HORIZONTAL            = 0,
    MSIGE66_DIRECTION_VERTICAL              = 1,
    MSIGE66_DIRECTION_RADIAL                = 2,
};

typedef struct
{
    unsigned char       red;
    unsigned char       green;
    unsigned char       blue;
} msige66_color;

/*---------------------------------------------------------*\
| One HID report, size is 64 (output) or 524 (feature)      |
\*---------------------------------------------------------*/
typedef struct
{
    unsigned char       kind;
    unsigned int        size;
    unsigned char       data[MSIGE66_FEATURE_SIZE];
} msige66_packet;

/*---------------------------------------------------------*\
| lighting_element_info, 10 bytes on the wire               |
\*---------------------------------------------------------*/
typedef struct
{
    msige66_color       init;
    msige66_color       react;
    unsigned short      react_time;
    unsigned char       effect_index;
    unsigned char       settings_mask;
} msige66_element_info;

/*---------------------------------------------------------*\
| lighting_effect, 69 bytes on the wire                     |
\*---------------------------------------------------------*/
typedef struct
{
    unsigned char       type;
    unsigned char       has_direction;
    unsigned char       direction_type;
    unsigned char       direction_inverted;
    unsigned short      focal_x;
    unsigned short      focal_y;
    unsigned short      speed;
    unsigned short      scale;
    unsigned char       num_colors;
    msige66_color       colors[MSIGE66_EFFECT_MAX_COLORS];
    unsigned char       positions[MSIGE66_EFFECT_MAX_COLORS];
} msige66_effect;

/*---------------------------------------------------------*\
| Keyboard element table membership (HID usage codes)       |
\*---------------------------------------------------------*/
extern const unsigned char  msige66_key_block_sizes[MSIGE66_KEY_BLOCK_COUNT];
extern const unsigned char* msige66_key_blocks[MSIGE66_KEY_BLOCK_COUNT];

/*---------------------------------------------------------*\
| Output reports                                            |
\*---------------------------------------------------------*/
void MSIGE66FwVersionRequest(msige66_packet* packet);
void MSIGE66GlobalBrightness(msige66_packet* packet, unsigned char level);
void MSIGE66ColorScale(msige66_packet* packet, msige66_color color);
void MSIGE66SaveToFlash(msige66_packet* packet);
void MSIGE66ResetCurrentLightingMode(msige66_packet* packet);

/*---------------------------------------------------------*\
| Feature reports                                           |
\*---------------------------------------------------------*/
bool MSIGE66DirectWrite(msige66_packet* packet, unsigned int count, const unsigned char* ids, const msige66_color* colors);
void MSIGE66EffectSlot(msige66_packet* packet, unsigned char slot, const unsigned char* effect_data);
void MSIGE66ZoneCoordinates(msige66_packet* packet);
void MSIGE66ElementTable(msige66_packet* packet, unsigned int count, const unsigned char* ids, const msige66_element_info* info, const unsigned char* footer, unsigned int footer_size);

/*---------------------------------------------------------*\
| Effect engine                                             |
\*---------------------------------------------------------*/
void MSIGE66DefaultPositions(unsigned int count, unsigned char* positions);
void MSIGE66EffectStruct(const msige66_effect* effect, unsigned char* out);
bool MSIGE66EffectBytes(const unsigned char* effect_struct, unsigned char* out);

/*---------------------------------------------------------*\
| Sequences. Each one ends with reset_current_lighting_mode |
| and, if persist is set, save_to_flash goes before it.     |
| Effect sequences return false if the effect needs more    |
| sections than the firmware has.                           |
\*---------------------------------------------------------*/
void MSIGE66BarStreamInitSequence(std::vector<msige66_packet>& out);
void MSIGE66BarStaticSequence(std::vector<msige66_packet>& out, msige66_color color, bool persist);
bool MSIGE66BarEffectSequence(std::vector<msige66_packet>& out, const msige66_effect* effect, unsigned char slot, bool persist);

void MSIGE66KeyboardStreamInitSequence(std::vector<msige66_packet>& out);
void MSIGE66KeyboardStaticSequence(std::vector<msige66_packet>& out, msige66_color color, bool persist);
bool MSIGE66KeyboardEffectSequence(std::vector<msige66_packet>& out, const msige66_effect* effect, unsigned char slot, bool persist);
void MSIGE66KeyboardReactiveSequence(std::vector<msige66_packet>& out, msige66_color color, msige66_color react_color, unsigned short react_time, bool persist);
