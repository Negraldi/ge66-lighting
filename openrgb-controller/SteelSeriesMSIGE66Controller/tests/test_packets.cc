/*---------------------------------------------------------*\
| test_packets.cc                                           |
|                                                           |
|   Standalone byte-equality test of the MSI GE66 packet    |
|   builders and effect engine against golden.inc, which    |
|   generate_golden.py produces from the Python reference.  |
|   Not part of the OpenRGB build (extension is .cc).       |
|                                                           |
|   Build and run, from the parent directory:               |
|   g++ -std=c++17 -I. tests/test_packets.cc \              |
|       SteelSeriesMSIGE66Protocol.cpp -o /tmp/ge66test \   |
|       && /tmp/ge66test                                    |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include "SteelSeriesMSIGE66Protocol.h"

typedef struct
{
    const char*         name;
    const char*         packets[10];
} msige66_golden;

#include "golden.inc"

#define COLOR(r, g, b)  { r, g, b }

static int failures = 0;
static int checks   = 0;

static const msige66_color rainbow[6] =
{
    COLOR(255, 0, 0), COLOR(255, 255, 0), COLOR(0, 255, 0), COLOR(0, 255, 255), COLOR(0, 0, 255), COLOR(255, 0, 255)
};

static const msige66_color eight[8] =
{
    COLOR(255, 0, 0), COLOR(255, 128, 0), COLOR(255, 255, 0), COLOR(0, 255, 0),
    COLOR(0, 255, 255), COLOR(0, 0, 255), COLOR(128, 0, 255), COLOR(255, 0, 255)
};

static const msige66_color rgb3[3] = { COLOR(255, 0, 0), COLOR(0, 255, 0), COLOR(0, 0, 255) };
static const msige66_color red_blue[2] = { COLOR(255, 0, 0), COLOR(0, 0, 255) };

static msige66_packet OutputPacket(void (*build)(msige66_packet*))
{
    msige66_packet packet;
    build(&packet);
    return packet;
}

/*---------------------------------------------------------*\
| direction -1 means no direction (all elements in sync)    |
\*---------------------------------------------------------*/
static msige66_effect MakeEffect(unsigned char type, const msige66_color* colors, unsigned int count, const unsigned char* positions, unsigned short speed, int direction, bool invert, unsigned short focal_x, unsigned short focal_y, unsigned short scale)
{
    msige66_effect effect;
    memset(&effect, 0, sizeof(effect));

    effect.type                 = type;
    effect.has_direction        = (direction >= 0) ? 1 : 0;
    effect.direction_type       = (direction >= 0) ? direction : MSIGE66_DIRECTION_HORIZONTAL;
    effect.direction_inverted   = invert ? 1 : 0;
    effect.focal_x              = focal_x;
    effect.focal_y              = focal_y;
    effect.speed                = speed;
    effect.scale                = scale;
    effect.num_colors           = count;

    for(unsigned int i = 0; i < count; i++)
    {
        effect.colors[i] = colors[i];
    }

    if(positions != NULL)
    {
        memcpy(effect.positions, positions, count);
    }
    else
    {
        MSIGE66DefaultPositions(count, effect.positions);
    }

    return effect;
}

static std::vector<msige66_color> FourteenColors()
{
    std::vector<msige66_color> colors;

    for(unsigned int i = 0; i < 14; i++)
    {
        msige66_color color = { (unsigned char)((i * 18) % 256), (unsigned char)((i * 37) % 256), (unsigned char)((i * 91) % 256) };
        colors.push_back(color);
    }

    return colors;
}

static int HexValue(char c)
{
    if(c >= '0' && c <= '9') return c - '0';
    if(c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

static std::vector<unsigned char> DecodeHex(const char* hex)
{
    std::vector<unsigned char> bytes;

    for(unsigned int i = 0; hex[i] != 0 && hex[i + 1] != 0; i += 2)
    {
        bytes.push_back((unsigned char)((HexValue(hex[i]) << 4) | HexValue(hex[i + 1])));
    }

    return bytes;
}

/*---------------------------------------------------------*\
| Compare a built packet with a golden string (kind letter, |
| then hex without trailing zeros)                          |
\*---------------------------------------------------------*/
static bool PacketMatches(const char* name, unsigned int index, const msige66_packet& packet, const char* golden)
{
    bool            feature     = (golden[0] == 'F');
    unsigned int    size        = feature ? MSIGE66_FEATURE_SIZE : MSIGE66_OUTPUT_SIZE;
    std::vector<unsigned char> expected = DecodeHex(golden + 1);
    expected.resize(size, 0);

    if(packet.kind != (feature ? MSIGE66_PACKET_FEATURE : MSIGE66_PACKET_OUTPUT) || packet.size != size)
    {
        printf("FAIL %s packet %u: kind/size is %u/%u, expected %u/%u\n", name, index, packet.kind, packet.size, feature ? 1u : 0u, size);
        return false;
    }

    for(unsigned int i = 0; i < size; i++)
    {
        if(packet.data[i] != expected[i])
        {
            printf("FAIL %s packet %u: byte %u is %02X, expected %02X\n", name, index, i, packet.data[i], expected[i]);
            return false;
        }
    }

    return true;
}

static void Check(const char* name, const std::vector<msige66_packet>& built)
{
    const msige66_golden*   golden = NULL;
    unsigned int            golden_count = 0;

    checks++;

    for(unsigned int i = 0; i < sizeof(golden_cases) / sizeof(golden_cases[0]); i++)
    {
        if(strcmp(golden_cases[i].name, name) == 0)
        {
            golden = &golden_cases[i];
        }
    }

    if(golden == NULL)
    {
        printf("FAIL %s: no golden case\n", name);
        failures++;
        return;
    }

    while(golden->packets[golden_count] != NULL)
    {
        golden_count++;
    }

    if(golden_count != built.size())
    {
        printf("FAIL %s: %u packets built, %u expected\n", name, (unsigned int)built.size(), golden_count);
        failures++;
        return;
    }

    for(unsigned int i = 0; i < golden_count; i++)
    {
        if(!PacketMatches(name, i, built[i], golden->packets[i]))
        {
            failures++;
            return;
        }
    }
}

static void CheckOne(const char* name, const msige66_packet& packet)
{
    std::vector<msige66_packet> built;
    built.push_back(packet);
    Check(name, built);
}

static void CheckEffect(const char* name, std::vector<msige66_packet>& built, bool ok)
{
    if(!ok)
    {
        printf("FAIL %s: effect builder refused the effect\n", name);
        failures++;
        checks++;
        return;
    }

    Check(name, built);
}

static void TestOutputReports()
{
    msige66_packet packet;

    CheckOne("bar_fw_version", OutputPacket(MSIGE66FwVersionRequest));
    CheckOne("kb_fw_version", OutputPacket(MSIGE66FwVersionRequest));

    MSIGE66GlobalBrightness(&packet, 0xFF);
    CheckOne("bar_brightness_ff", packet);

    MSIGE66GlobalBrightness(&packet, 0x80);
    CheckOne("bar_brightness_80", packet);

    msige66_color bar_scale = COLOR(0xFF, 0xFF, 0x99);
    MSIGE66ColorScale(&packet, bar_scale);
    CheckOne("bar_color_scale", packet);

    msige66_color kb_scale = COLOR(140, 204, 153);
    MSIGE66ColorScale(&packet, kb_scale);
    CheckOne("kb_color_scale", packet);

    CheckOne("bar_save_to_flash", OutputPacket(MSIGE66SaveToFlash));
    CheckOne("bar_reset_current_lighting_mode", OutputPacket(MSIGE66ResetCurrentLightingMode));
}

static void TestDirectWrites()
{
    msige66_packet  packet;
    unsigned char   ids[MSIGE66_KEY_COUNT];
    msige66_color   colors[MSIGE66_KEY_COUNT];

    for(unsigned int zone = 0; zone < MSIGE66_BAR_ZONES; zone++)
    {
        ids[zone]               = zone;
        colors[zone].red        = (zone * 7) % 256;
        colors[zone].green      = 255 - zone * 5;
        colors[zone].blue       = (zone * 3) % 256;
    }

    checks++;
    if(!MSIGE66DirectWrite(&packet, MSIGE66_BAR_ZONES, ids, colors))
    {
        printf("FAIL bar_direct_write_full: refused\n");
        failures++;
    }
    else
    {
        CheckOne("bar_direct_write_full", packet);
    }

    /*-----------------------------------------------------*\
    | Physical key HID codes of the GE66, ascending         |
    \*-----------------------------------------------------*/
    static const unsigned char physical[] =
    {
        4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
        30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 57,
        58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 73, 74, 75, 77, 78, 79, 80, 81, 82,
        100, 102, 224, 225, 226, 227, 228, 229, 230, 240
    };
    unsigned int key_count = sizeof(physical) / sizeof(physical[0]);

    for(unsigned int i = 0; i < key_count; i++)
    {
        ids[i]              = physical[i];
        colors[i].red       = (physical[i] * 5) % 256;
        colors[i].green     = (physical[i] * 11) % 256;
        colors[i].blue      = 255 - physical[i];
    }

    checks++;
    if(key_count != 84 || !MSIGE66DirectWrite(&packet, key_count, ids, colors))
    {
        printf("FAIL kb_direct_write_full: %u keys\n", key_count);
        failures++;
        return;
    }

    /*-----------------------------------------------------*\
    | The keyboard direct sequence is the stream init       |
    | tables and reset, then the direct write on its own    |
    \*-----------------------------------------------------*/
    std::vector<msige66_packet> built;
    MSIGE66KeyboardStreamInitSequence(built);
    Check("kb_stream_init", built);
    CheckOne("kb_direct_write_full", packet);
}

static void TestBarSequences()
{
    std::vector<msige66_packet> out;
    msige66_color               red     = COLOR(255, 0, 0);
    msige66_color               black   = COLOR(0, 0, 0);
    msige66_color               color   = COLOR(0x12, 0x34, 0x56);
    bool                        ok;

    MSIGE66BarStaticSequence(out, red, false);
    Check("bar_static_red", out);

    out.clear();
    MSIGE66BarStaticSequence(out, color, true);
    Check("bar_static_persist", out);

    out.clear();
    MSIGE66BarStaticSequence(out, black, false);
    Check("bar_off", out);

    out.clear();
    MSIGE66BarStreamInitSequence(out);
    Check("bar_stream_init", out);

    msige66_effect effect;

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_COLORSHIFT, rainbow, 6, NULL, 200, MSIGE66_DIRECTION_HORIZONTAL, false, 0, 0, 40);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_colorshift_rainbow_horizontal", out, ok);

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_COLORSHIFT, rainbow, 6, NULL, 200, -1, false, 0, 0, 0);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_colorshift_rainbow_no_direction", out, ok);

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_COLORSHIFT, rainbow, 6, NULL, 333, MSIGE66_DIRECTION_VERTICAL, true, 4, 9, 40);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_colorshift_vertical_inverted", out, ok);

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_COLORSHIFT, rainbow, 6, NULL, 200, MSIGE66_DIRECTION_RADIAL, false, 0, 0, 77);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, true);
    CheckEffect("bar_colorshift_radial_persist", out, ok);

    out.clear();
    static const unsigned char hold_positions[3] = { 10, 50, 90 };
    effect = MakeEffect(MSIGE66_EFFECT_COLORSHIFT, rgb3, 3, hold_positions, 200, -1, false, 0, 0, 0);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_colorshift_hold_section", out, ok);

    out.clear();
    std::vector<msige66_color> fourteen = FourteenColors();
    effect = MakeEffect(MSIGE66_EFFECT_COLORSHIFT, &fourteen[0], 14, NULL, 1200, -1, false, 0, 0, 0);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_colorshift_14_colors", out, ok);

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_BREATHE, red_blue, 2, NULL, 300, -1, false, 0, 0, 0);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_breathe_two_colors", out, ok);

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_BREATHE, rgb3, 3, NULL, 400, MSIGE66_DIRECTION_HORIZONTAL, true, 3, 5, 40);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_breathe_wave_inverted", out, ok);

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_BREATHE, eight, 8, NULL, 900, -1, false, 0, 0, 0);
    ok = MSIGE66BarEffectSequence(out, &effect, 0, false);
    CheckEffect("bar_breathe_8_colors", out, ok);

    /*-----------------------------------------------------*\
    | Nine breathe colors need 18 sections, more than 16    |
    \*-----------------------------------------------------*/
    out.clear();
    msige66_color nine[9];
    for(unsigned int i = 0; i < 9; i++)
    {
        nine[i] = eight[i % 8];
    }
    effect = MakeEffect(MSIGE66_EFFECT_BREATHE, nine, 9, NULL, 900, -1, false, 0, 0, 0);
    checks++;
    if(MSIGE66BarEffectSequence(out, &effect, 0, false) || !out.empty())
    {
        printf("FAIL breathe with 9 colors was accepted\n");
        failures++;
    }
}

static void TestKeyboardSequences()
{
    std::vector<msige66_packet> out;
    msige66_color               red     = COLOR(255, 0, 0);
    msige66_color               black   = COLOR(0, 0, 0);
    msige66_color               color   = COLOR(0x00, 0xFF, 0x80);
    bool                        ok;

    MSIGE66KeyboardStaticSequence(out, red, false);
    Check("kb_static_red", out);

    out.clear();
    MSIGE66KeyboardStaticSequence(out, color, true);
    Check("kb_static_persist", out);

    out.clear();
    MSIGE66KeyboardStaticSequence(out, black, false);
    Check("kb_off", out);

    msige66_effect effect;

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_COLORSHIFT, rainbow, 6, NULL, 200, -1, false, 0, 0, 0);
    ok = MSIGE66KeyboardEffectSequence(out, &effect, 0, false);
    CheckEffect("kb_colorshift_rainbow", out, ok);

    out.clear();
    effect = MakeEffect(MSIGE66_EFFECT_BREATHE, rgb3, 3, NULL, 640, -1, false, 0, 0, 0);
    ok = MSIGE66KeyboardEffectSequence(out, &effect, 0, false);
    CheckEffect("kb_breathe_three_colors", out, ok);

    out.clear();
    msige66_color rest  = COLOR(0x00, 0x00, 0x20);
    msige66_color flash = COLOR(255, 255, 255);
    MSIGE66KeyboardReactiveSequence(out, rest, flash, MSIGE66_KEY_REACT_TIME_DEFAULT, false);
    Check("kb_reactive_default_time", out);

    out.clear();
    msige66_color rest2  = COLOR(0x10, 0x20, 0x30);
    msige66_color flash2 = COLOR(0xFF, 0x80, 0x00);
    MSIGE66KeyboardReactiveSequence(out, rest2, flash2, 500, true);
    Check("kb_reactive_500_persist", out);
}

static void TestDefaultPositions()
{
    for(unsigned int count = 1; count <= 14; count++)
    {
        unsigned char positions[MSIGE66_EFFECT_MAX_COLORS];
        MSIGE66DefaultPositions(count, positions);

        std::vector<unsigned char> expected = DecodeHex(golden_positions[count - 1]);

        checks++;
        if(expected.size() != count || memcmp(positions, &expected[0], count) != 0)
        {
            printf("FAIL default positions for %u colors\n", count);
            failures++;
        }
    }
}

static void TestEveryGoldenCaseWasChecked()
{
    printf("%d golden cases, %d checked\n", (int)(sizeof(golden_cases) / sizeof(golden_cases[0])), checks);
}

int main()
{
    TestOutputReports();
    TestDirectWrites();
    TestBarSequences();
    TestKeyboardSequences();
    TestDefaultPositions();
    TestEveryGoldenCaseWasChecked();

    if(failures > 0)
    {
        printf("%d of %d checks FAILED\n", failures, checks);
        return 1;
    }

    printf("OK: %d checks passed\n", checks);
    return 0;
}
