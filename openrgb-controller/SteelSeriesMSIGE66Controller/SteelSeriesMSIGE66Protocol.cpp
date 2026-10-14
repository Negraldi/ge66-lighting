/*---------------------------------------------------------*\
| SteelSeriesMSIGE66Protocol.cpp                            |
|                                                           |
|   Packet builders and effect engine for the MSI GE66      |
|   Raider light bar (SteelSeries ALC, 1038:1132) and       |
|   keyboard (SteelSeries KLC, 1038:1122)                   |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include <cstring>
#include "SteelSeriesMSIGE66Protocol.h"

/*---------------------------------------------------------*\
| Offsets inside the 69 byte lighting_effect struct         |
\*---------------------------------------------------------*/
#define EFFECT_STRUCT_COLORS                13
#define EFFECT_STRUCT_POSITIONS             55

#define ELEMENT_INFO_SIZE                   10
#define ELEMENT_BLOCK_SIZE                  12

/*---------------------------------------------------------*\
| Unused bytes at the end of every captured KLC element     |
| table. msi-perkeyrgb sends 08 39 and works on this unit.  |
\*---------------------------------------------------------*/
static const unsigned char key_table_footer[2] = { 0x08, 0x39 };

/*---------------------------------------------------------*\
| Keyboard element tables (key_illumination_block_1 to 4)   |
| filled with the keys of the default msi_ge66_klc config.  |
| Sizes are 42, 19, 24 and 11.                              |
\*---------------------------------------------------------*/
static const unsigned char key_block_1[] =
{
    4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 58, 59, 60, 61, 62, 63
};

static const unsigned char key_block_2[] =
{
    64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82
};

static const unsigned char key_block_3[] =
{
    41, 42, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 102, 224, 225, 226, 227, 228, 229, 230, 240
};

static const unsigned char key_block_4[] =
{
    40, 49, 50, 100, 135, 136, 137, 138, 139, 144, 145
};

const unsigned char msige66_key_block_sizes[MSIGE66_KEY_BLOCK_COUNT] =
{
    sizeof(key_block_1), sizeof(key_block_2), sizeof(key_block_3), sizeof(key_block_4)
};

const unsigned char* msige66_key_blocks[MSIGE66_KEY_BLOCK_COUNT] =
{
    key_block_1, key_block_2, key_block_3, key_block_4
};

/*---------------------------------------------------------*\
| Position step of evenly spread colors, indexed by count   |
| (the vendor template: 0, 17, 34 and so on for six colors) |
\*---------------------------------------------------------*/
static const unsigned char position_step[MSIGE66_EFFECT_MAX_COLORS + 1] =
{
    0, 100, 50, 33, 25, 20, 17, 14, 12, 11, 10, 9, 8, 8, 7
};

static void InitPacket(msige66_packet* packet, unsigned char kind)
{
    memset(packet->data, 0x00, sizeof(packet->data));
    packet->kind = kind;
    packet->size = (kind == MSIGE66_PACKET_FEATURE) ? MSIGE66_FEATURE_SIZE : MSIGE66_OUTPUT_SIZE;
}

static void PutU16(unsigned char* buf, unsigned short value)
{
    buf[0] = value & 0xFF;
    buf[1] = value >> 8;
}

/*---------------------------------------------------------*\
| Output reports                                            |
\*---------------------------------------------------------*/
void MSIGE66FwVersionRequest(msige66_packet* packet)
{
    InitPacket(packet, MSIGE66_PACKET_OUTPUT);
    packet->data[0] = 0x10;
}

void MSIGE66GlobalBrightness(msige66_packet* packet, unsigned char level)
{
    InitPacket(packet, MSIGE66_PACKET_OUTPUT);
    packet->data[0] = 0x0C;
    packet->data[2] = level;
}

void MSIGE66ColorScale(msige66_packet* packet, msige66_color color)
{
    InitPacket(packet, MSIGE66_PACKET_OUTPUT);
    packet->data[0] = 0x51;
    packet->data[2] = color.red;
    packet->data[3] = color.green;
    packet->data[4] = color.blue;
}

void MSIGE66SaveToFlash(msige66_packet* packet)
{
    InitPacket(packet, MSIGE66_PACKET_OUTPUT);
    packet->data[0] = 0x09;
}

void MSIGE66ResetCurrentLightingMode(msige66_packet* packet)
{
    InitPacket(packet, MSIGE66_PACKET_OUTPUT);
    packet->data[0] = 0x0D;
    packet->data[2] = 0x02;
}

/*---------------------------------------------------------*\
| Feature reports                                           |
\*---------------------------------------------------------*/
bool MSIGE66DirectWrite(msige66_packet* packet, unsigned int count, const unsigned char* ids, const msige66_color* colors)
{
    if(count > 255 || (4 + 4 * count) > MSIGE66_FEATURE_SIZE)
    {
        return(false);
    }

    InitPacket(packet, MSIGE66_PACKET_FEATURE);
    packet->data[0] = 0x0C;
    packet->data[2] = count;

    for(unsigned int i = 0; i < count; i++)
    {
        packet->data[4 + 4 * i + 0] = ids[i];
        packet->data[4 + 4 * i + 1] = colors[i].red;
        packet->data[4 + 4 * i + 2] = colors[i].green;
        packet->data[4 + 4 * i + 3] = colors[i].blue;
    }

    return(true);
}

void MSIGE66EffectSlot(msige66_packet* packet, unsigned char slot, const unsigned char* effect_data)
{
    InitPacket(packet, MSIGE66_PACKET_FEATURE);
    packet->data[0] = 0x0B;
    packet->data[2] = slot;
    memcpy(&packet->data[4], effect_data, MSIGE66_EFFECT_SIZE);
}

/*---------------------------------------------------------*\
| Zone positions used by wave effects, zone i is at (i, 0)  |
\*---------------------------------------------------------*/
void MSIGE66ZoneCoordinates(msige66_packet* packet)
{
    InitPacket(packet, MSIGE66_PACKET_FEATURE);
    packet->data[0] = 0x0D;
    packet->data[2] = MSIGE66_BAR_ZONES;

    for(unsigned int zone = 0; zone < MSIGE66_BAR_ZONES; zone++)
    {
        PutU16(&packet->data[4 + 4 * zone], zone);
    }
}

/*---------------------------------------------------------*\
| zone_illumination_active and key_illumination_block_N:    |
| 0E 00 count 00, then one 12 byte block per element.       |
| Every element gets the same info, ids differ.             |
\*---------------------------------------------------------*/
void MSIGE66ElementTable(msige66_packet* packet, unsigned int count, const unsigned char* ids, const msige66_element_info* info, const unsigned char* footer, unsigned int footer_size)
{
    InitPacket(packet, MSIGE66_PACKET_FEATURE);
    packet->data[0] = 0x0E;
    packet->data[2] = count;

    for(unsigned int i = 0; i < count; i++)
    {
        unsigned char* block = &packet->data[4 + ELEMENT_BLOCK_SIZE * i];

        block[0] = info->init.red;
        block[1] = info->init.green;
        block[2] = info->init.blue;
        block[3] = info->react.red;
        block[4] = info->react.green;
        block[5] = info->react.blue;
        PutU16(&block[6], info->react_time);
        block[8] = info->effect_index;
        block[9] = info->settings_mask;
        block[10] = 0x00;
        block[11] = ids[i];
    }

    if(footer != NULL)
    {
        memcpy(&packet->data[MSIGE66_FEATURE_SIZE - footer_size], footer, footer_size);
    }
}

/*---------------------------------------------------------*\
| Effect engine                                             |
\*---------------------------------------------------------*/
void MSIGE66DefaultPositions(unsigned int count, unsigned char* positions)
{
    for(unsigned int i = 0; i < count && i < MSIGE66_EFFECT_MAX_COLORS; i++)
    {
        unsigned int position = i * position_step[count];

        positions[i] = (position > 100) ? 100 : position;
    }
}

void MSIGE66EffectStruct(const msige66_effect* effect, unsigned char* out)
{
    memset(out, 0x00, MSIGE66_EFFECT_STRUCT_SIZE);

    out[0] = effect->type;
    out[1] = effect->has_direction;
    out[2] = effect->direction_type;
    out[3] = effect->direction_inverted;
    PutU16(&out[4], effect->focal_x);
    PutU16(&out[6], effect->focal_y);
    PutU16(&out[8], effect->speed);
    PutU16(&out[10], effect->scale);
    out[12] = effect->num_colors;

    for(unsigned int i = 0; i < MSIGE66_EFFECT_MAX_COLORS; i++)
    {
        out[EFFECT_STRUCT_COLORS + 3 * i + 0] = effect->colors[i].red;
        out[EFFECT_STRUCT_COLORS + 3 * i + 1] = effect->colors[i].green;
        out[EFFECT_STRUCT_COLORS + 3 * i + 2] = effect->colors[i].blue;
        out[EFFECT_STRUCT_POSITIONS + i]      = effect->positions[i];
    }
}

static int ColorByte(const unsigned char* effect_struct, int color_index, int channel)
{
    return(effect_struct[EFFECT_STRUCT_COLORS + color_index * 3 + channel]);
}

static int Position(const unsigned char* effect_struct, int index)
{
    return(effect_struct[EFFECT_STRUCT_POSITIONS + index]);
}

/*---------------------------------------------------------*\
| Section color delta: 16 * (final - initial) / speed,      |
| truncated toward zero, stored as a signed byte            |
\*---------------------------------------------------------*/
static unsigned char ScaledDelta(int initial, int final, int speed)
{
    int diff = (16 * (final - initial)) / speed;

    return((unsigned char)(diff < 0 ? 256 + diff : diff));
}

/*---------------------------------------------------------*\
| Section: dR dG dB 00 speed(u16) next 00                   |
\*---------------------------------------------------------*/
static void PutSection(unsigned char* out, const unsigned char* deltas, int speed, int next_index)
{
    out[0] = deltas[0];
    out[1] = deltas[1];
    out[2] = deltas[2];
    out[3] = 0x00;
    PutU16(&out[4], speed);
    out[6] = next_index;
    out[7] = 0x00;
}

static int ColorshiftSection(const unsigned char* effect_struct, int index, int sections, int ticks, bool padded, unsigned char* out)
{
    memset(out, 0x00, 8);

    if(sections == 0 || index >= sections)
    {
        return(0);
    }

    bool last           = (index == sections - 1);
    int first_color     = padded ? ((index == 0) ? 0 : index - 1) : index;
    int last_color      = last ? 0 : (padded ? index : index + 1);
    int start           = (index == 0) ? 0 : Position(effect_struct, padded ? index - 1 : index);
    int end             = last ? 100 : Position(effect_struct, padded ? index : index + 1);
    int speed           = (ticks * (end - start)) / 100;
    unsigned char deltas[3];

    if(speed < MSIGE66_EFFECT_MIN_SECTION_SPEED)
    {
        speed = MSIGE66_EFFECT_MIN_SECTION_SPEED;
    }

    for(int channel = 0; channel < 3; channel++)
    {
        deltas[channel] = ScaledDelta(ColorByte(effect_struct, first_color, channel), ColorByte(effect_struct, last_color, channel), speed);
    }

    PutSection(out, deltas, speed, last ? 0 : index + 1);
    return(speed);
}

static int BreatheSection(const unsigned char* effect_struct, int index, int colors, int ticks, bool padded, unsigned char* out)
{
    int sections = 2 * colors + (padded ? 1 : 0);

    memset(out, 0x00, 8);

    if(sections == 0 || index >= sections)
    {
        return(0);
    }

    int start;
    int end;
    int first_color;
    int last_color;

    if(index == 0)
    {
        start = 0;
    }
    else
    {
        start = Position(effect_struct, padded ? (index - 1) / 2 : index / 2);
    }

    if(index >= sections - 2)
    {
        end = 100;
    }
    else if(padded)
    {
        end = (index == 0) ? Position(effect_struct, 0) : Position(effect_struct, 1 + (index - 1) / 2);
    }
    else
    {
        end = Position(effect_struct, 1 + index / 2);
    }

    int speed = (ticks * ((end - start) / 2)) / 100;

    if(speed < MSIGE66_EFFECT_MIN_SECTION_SPEED)
    {
        speed = MSIGE66_EFFECT_MIN_SECTION_SPEED;
    }

    if(index == 0)
    {
        first_color = 0;
    }
    else
    {
        first_color = padded ? (index - 1) / 2 : index / 2;
    }

    if(index == sections - 1)
    {
        last_color = 0;
    }
    else if(padded)
    {
        last_color = (index == 0) ? 0 : (index - 1) / 2 + 1;
    }
    else
    {
        last_color = index / 2 + 1;
    }

    bool odd        = padded ? (index % 2 == 1) : (index % 2 == 0);
    bool padding    = padded && (index == 0);
    unsigned char deltas[3];

    for(int channel = 0; channel < 3; channel++)
    {
        int initial = (odd || padding) ? ColorByte(effect_struct, first_color, channel) : 0;
        int final   = (odd && !padding) ? 0 : ColorByte(effect_struct, last_color, channel);

        deltas[channel] = ScaledDelta(initial, final, speed);
    }

    PutSection(out, deltas, speed, (index == sections - 1) ? 0 : index + 1);
    return(speed);
}

/*---------------------------------------------------------*\
| get-effect-bytes: the 69 byte lighting_effect struct to   |
| the 151 bytes stored in an effect slot. 16 sections of 8  |
| bytes, first color * 16, focal point, wave scaling, scale,|
| section count, total ticks and the direction inverted flag|
\*---------------------------------------------------------*/
bool MSIGE66EffectBytes(const unsigned char* effect_struct, unsigned char* out)
{
    unsigned char type = effect_struct[0];

    memset(out, 0x00, MSIGE66_EFFECT_SIZE);

    /*-----------------------------------------------------*\
    | Disabled, and types the engine does not know, are     |
    | an all zero effect                                    |
    \*-----------------------------------------------------*/
    if(type != MSIGE66_EFFECT_COLORSHIFT && type != MSIGE66_EFFECT_BREATHE)
    {
        return(true);
    }

    int has_direction   = effect_struct[1];
    int direction_type  = effect_struct[2];
    int ticks           = effect_struct[8] | (effect_struct[9] << 8);
    int colors          = effect_struct[12];
    bool padded         = (Position(effect_struct, 0) != 0);
    int sections        = (type == MSIGE66_EFFECT_COLORSHIFT) ? colors : 2 * colors;

    if(padded)
    {
        sections++;
    }

    if(sections > MSIGE66_EFFECT_MAX_SECTIONS)
    {
        return(false);
    }

    int total = 0;

    for(int i = 0; i < MSIGE66_EFFECT_MAX_SECTIONS; i++)
    {
        if(type == MSIGE66_EFFECT_COLORSHIFT)
        {
            total += ColorshiftSection(effect_struct, i, sections, ticks, padded, &out[8 * i]);
        }
        else
        {
            total += BreatheSection(effect_struct, i, colors, ticks, padded, &out[8 * i]);
        }
    }

    if(total > 0xFFFF)
    {
        memset(out, 0x00, MSIGE66_EFFECT_SIZE);
        return(false);
    }

    unsigned char* tail = &out[8 * MSIGE66_EFFECT_MAX_SECTIONS];

    PutU16(&tail[0], 16 * ColorByte(effect_struct, 0, 0));
    PutU16(&tail[2], 16 * ColorByte(effect_struct, 0, 1));
    PutU16(&tail[4], 16 * ColorByte(effect_struct, 0, 2));
    tail[6] = 0xFF;
    tail[7] = 0x00;
    memcpy(&tail[8], &effect_struct[4], 4);

    if(has_direction == 1 && (direction_type == MSIGE66_DIRECTION_HORIZONTAL || direction_type == MSIGE66_DIRECTION_RADIAL))
    {
        PutU16(&tail[12], 1);
    }

    if(has_direction == 1 && (direction_type == MSIGE66_DIRECTION_VERTICAL || direction_type == MSIGE66_DIRECTION_RADIAL))
    {
        PutU16(&tail[14], 1);
    }

    memcpy(&tail[16], &effect_struct[10], 2);
    PutU16(&tail[18], sections);
    PutU16(&tail[20], total);
    tail[22] = effect_struct[3];

    return(true);
}

/*---------------------------------------------------------*\
| Sequences                                                 |
\*---------------------------------------------------------*/
static void AppendFinish(std::vector<msige66_packet>& out, bool persist)
{
    msige66_packet packet;

    if(persist)
    {
        MSIGE66SaveToFlash(&packet);
        out.push_back(packet);
    }

    MSIGE66ResetCurrentLightingMode(&packet);
    out.push_back(packet);
}

static void AppendBarTable(std::vector<msige66_packet>& out, const msige66_element_info* info)
{
    unsigned char   ids[MSIGE66_BAR_ZONES];
    msige66_packet  packet;

    for(unsigned int zone = 0; zone < MSIGE66_BAR_ZONES; zone++)
    {
        ids[zone] = zone;
    }

    MSIGE66ElementTable(&packet, MSIGE66_BAR_ZONES, ids, info, NULL, 0);
    out.push_back(packet);
}

static void AppendKeyTables(std::vector<msige66_packet>& out, const msige66_element_info* info)
{
    msige66_packet packet;

    for(unsigned int block = 0; block < MSIGE66_KEY_BLOCK_COUNT; block++)
    {
        MSIGE66ElementTable(&packet, msige66_key_block_sizes[block], msige66_key_blocks[block], info, key_table_footer, sizeof(key_table_footer));
        out.push_back(packet);
    }
}

static msige66_element_info SteadyInfo(msige66_color color, unsigned char effect_index)
{
    msige66_element_info info;
    memset(&info, 0x00, sizeof(info));

    info.init           = color;
    info.effect_index   = effect_index;
    info.settings_mask  = MSIGE66_MASK_STEADY;
    return(info);
}

static msige66_element_info EffectInfo(const msige66_effect* effect, unsigned char slot)
{
    msige66_element_info info;
    memset(&info, 0x00, sizeof(info));

    if(effect->num_colors > 0)
    {
        info.init = effect->colors[0];
    }

    info.effect_index   = slot;
    info.settings_mask  = MSIGE66_MASK_EFFECT;
    return(info);
}

static msige66_element_info HostStreamInfo()
{
    msige66_element_info info;
    memset(&info, 0x00, sizeof(info));

    info.settings_mask  = MSIGE66_MASK_HOST_STREAM;
    return(info);
}

static bool AppendEffectSlot(std::vector<msige66_packet>& out, const msige66_effect* effect, unsigned char slot)
{
    unsigned char   effect_struct[MSIGE66_EFFECT_STRUCT_SIZE];
    unsigned char   effect_data[MSIGE66_EFFECT_SIZE];
    msige66_packet  packet;

    if(slot >= MSIGE66_EFFECT_SLOTS)
    {
        return(false);
    }

    MSIGE66EffectStruct(effect, effect_struct);

    if(!MSIGE66EffectBytes(effect_struct, effect_data))
    {
        return(false);
    }

    MSIGE66EffectSlot(&packet, slot, effect_data);
    out.push_back(packet);
    return(true);
}

void MSIGE66BarStreamInitSequence(std::vector<msige66_packet>& out)
{
    msige66_element_info info = HostStreamInfo();

    AppendBarTable(out, &info);
    AppendFinish(out, false);
}

void MSIGE66BarStaticSequence(std::vector<msige66_packet>& out, msige66_color color, bool persist)
{
    msige66_element_info info = SteadyInfo(color, 0);

    AppendBarTable(out, &info);
    AppendFinish(out, persist);
}

bool MSIGE66BarEffectSequence(std::vector<msige66_packet>& out, const msige66_effect* effect, unsigned char slot, bool persist)
{
    std::vector<msige66_packet> sequence;
    msige66_element_info        info = EffectInfo(effect, slot);

    if(!AppendEffectSlot(sequence, effect, slot))
    {
        return(false);
    }

    /*-----------------------------------------------------*\
    | Waves need to know where each zone is                 |
    \*-----------------------------------------------------*/
    if(effect->has_direction)
    {
        msige66_packet packet;

        MSIGE66ZoneCoordinates(&packet);
        sequence.push_back(packet);
    }

    AppendBarTable(sequence, &info);
    AppendFinish(sequence, persist);

    out.insert(out.end(), sequence.begin(), sequence.end());
    return(true);
}

void MSIGE66KeyboardStreamInitSequence(std::vector<msige66_packet>& out)
{
    msige66_element_info info = HostStreamInfo();

    AppendKeyTables(out, &info);
    AppendFinish(out, false);
}

void MSIGE66KeyboardStaticSequence(std::vector<msige66_packet>& out, msige66_color color, bool persist)
{
    msige66_element_info info = SteadyInfo(color, 1);

    AppendKeyTables(out, &info);
    AppendFinish(out, persist);
}

bool MSIGE66KeyboardEffectSequence(std::vector<msige66_packet>& out, const msige66_effect* effect, unsigned char slot, bool persist)
{
    std::vector<msige66_packet> sequence;
    msige66_element_info        info = EffectInfo(effect, slot);

    if(!AppendEffectSlot(sequence, effect, slot))
    {
        return(false);
    }

    AppendKeyTables(sequence, &info);
    AppendFinish(sequence, persist);

    out.insert(out.end(), sequence.begin(), sequence.end());
    return(true);
}

void MSIGE66KeyboardReactiveSequence(std::vector<msige66_packet>& out, msige66_color color, msige66_color react_color, unsigned short react_time, bool persist)
{
    msige66_element_info info;
    memset(&info, 0x00, sizeof(info));

    info.init           = color;
    info.react          = react_color;
    info.react_time     = (react_time > MSIGE66_KEY_REACT_TIME_MAX) ? MSIGE66_KEY_REACT_TIME_MAX : react_time;
    info.effect_index   = 0;
    info.settings_mask  = MSIGE66_MASK_REACTIVE;

    AppendKeyTables(out, &info);
    AppendFinish(out, persist);
}
