/*---------------------------------------------------------*\
| SteelSeriesMSIGE66LightBarController.cpp                  |
|                                                           |
|   Driver for the MSI GE66 Raider light bar                |
|   (SteelSeries ALC, 1038:1132, 35 zones)                  |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include "SteelSeriesMSIGE66LightBarController.h"

/*---------------------------------------------------------*\
| The vendor software scales blue down to 0x99, as white    |
| looks blue otherwise                                      |
\*---------------------------------------------------------*/
#define MSIGE66_BAR_COLOR_SCALE_RED         0xFF
#define MSIGE66_BAR_COLOR_SCALE_GREEN       0xFF
#define MSIGE66_BAR_COLOR_SCALE_BLUE        0x99

SteelSeriesMSIGE66LightBarController::SteelSeriesMSIGE66LightBarController(hid_device* dev_handle, const char* path, std::string dev_name) : SteelSeriesMSIGE66Controller(dev_handle, path, dev_name)
{
    /*-----------------------------------------------------*\
    | Vendor init: color scale, then full brightness        |
    \*-----------------------------------------------------*/
    msige66_packet  packet;
    msige66_color   color_scale = { MSIGE66_BAR_COLOR_SCALE_RED, MSIGE66_BAR_COLOR_SCALE_GREEN, MSIGE66_BAR_COLOR_SCALE_BLUE };

    MSIGE66ColorScale(&packet, color_scale);
    SendPacket(packet);

    SetBrightness(0xFF);
}

SteelSeriesMSIGE66LightBarController::~SteelSeriesMSIGE66LightBarController()
{

}

void SteelSeriesMSIGE66LightBarController::SetBrightness(unsigned char level)
{
    msige66_packet packet;

    MSIGE66GlobalBrightness(&packet, level);
    SendPacket(packet);
}

/*---------------------------------------------------------*\
| One direct_write feature report with every zone           |
\*---------------------------------------------------------*/
void SteelSeriesMSIGE66LightBarController::SetDirect(std::vector<RGBColor>& colors)
{
    unsigned char   ids[MSIGE66_BAR_ZONES];
    msige66_color   zone_colors[MSIGE66_BAR_ZONES];
    msige66_packet  packet;

    for(unsigned int zone_idx = 0; zone_idx < MSIGE66_BAR_ZONES && zone_idx < colors.size(); zone_idx++)
    {
        ids[zone_idx]               = zone_idx;
        zone_colors[zone_idx].red   = RGBGetRValue(colors[zone_idx]);
        zone_colors[zone_idx].green = RGBGetGValue(colors[zone_idx]);
        zone_colors[zone_idx].blue  = RGBGetBValue(colors[zone_idx]);
    }

    if(MSIGE66DirectWrite(&packet, MSIGE66_BAR_ZONES, ids, zone_colors))
    {
        SendPacket(packet);
    }
}

/*---------------------------------------------------------*\
| Put every zone back in host stream mode so that direct    |
| writes show up after a firmware effect or static color    |
\*---------------------------------------------------------*/
void SteelSeriesMSIGE66LightBarController::SetHostStream()
{
    std::vector<msige66_packet> sequence;

    MSIGE66BarStreamInitSequence(sequence);
    SendSequence(sequence);
}

void SteelSeriesMSIGE66LightBarController::SetStatic(RGBColor color, bool persist)
{
    std::vector<msige66_packet> sequence;
    msige66_color               bar_color = { (unsigned char)RGBGetRValue(color), (unsigned char)RGBGetGValue(color), (unsigned char)RGBGetBValue(color) };

    MSIGE66BarStaticSequence(sequence, bar_color, persist);
    SendSequence(sequence);
}

bool SteelSeriesMSIGE66LightBarController::SetEffect(const msige66_effect* effect, bool persist)
{
    std::vector<msige66_packet> sequence;

    if(!MSIGE66BarEffectSequence(sequence, effect, 0, persist))
    {
        return(false);
    }

    SendSequence(sequence);
    return(true);
}
