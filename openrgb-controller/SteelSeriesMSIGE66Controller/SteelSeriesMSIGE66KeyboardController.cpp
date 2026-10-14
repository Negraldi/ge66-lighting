/*---------------------------------------------------------*\
| SteelSeriesMSIGE66KeyboardController.cpp                  |
|                                                           |
|   Driver for the MSI GE66 Raider per-key keyboard         |
|   (SteelSeries KLC, 1038:1122)                            |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include "SteelSeriesMSIGE66KeyboardController.h"

static msige66_color ToMSIGE66Color(RGBColor color)
{
    msige66_color new_color = { (unsigned char)RGBGetRValue(color), (unsigned char)RGBGetGValue(color), (unsigned char)RGBGetBValue(color) };

    return(new_color);
}

SteelSeriesMSIGE66KeyboardController::SteelSeriesMSIGE66KeyboardController(hid_device* dev_handle, const char* path, std::string dev_name) : SteelSeriesMSIGE66Controller(dev_handle, path, dev_name)
{

}

SteelSeriesMSIGE66KeyboardController::~SteelSeriesMSIGE66KeyboardController()
{

}

/*---------------------------------------------------------*\
| Put every key in host stream mode so that direct writes   |
| show up                                                   |
\*---------------------------------------------------------*/
void SteelSeriesMSIGE66KeyboardController::SetHostStream()
{
    std::vector<msige66_packet> sequence;

    MSIGE66KeyboardStreamInitSequence(sequence);
    SendSequence(sequence);
}

/*---------------------------------------------------------*\
| One direct_write feature report, ids are HID usage codes  |
\*---------------------------------------------------------*/
void SteelSeriesMSIGE66KeyboardController::SetDirect(unsigned int count, const unsigned char* ids, const msige66_color* colors)
{
    msige66_packet packet;

    if(MSIGE66DirectWrite(&packet, count, ids, colors))
    {
        SendPacket(packet);
    }
}

void SteelSeriesMSIGE66KeyboardController::SetStatic(RGBColor color, bool persist)
{
    std::vector<msige66_packet> sequence;

    MSIGE66KeyboardStaticSequence(sequence, ToMSIGE66Color(color), persist);
    SendSequence(sequence);
}

bool SteelSeriesMSIGE66KeyboardController::SetEffect(const msige66_effect* effect, bool persist)
{
    std::vector<msige66_packet> sequence;

    if(!MSIGE66KeyboardEffectSequence(sequence, effect, 0, persist))
    {
        return(false);
    }

    SendSequence(sequence);
    return(true);
}

void SteelSeriesMSIGE66KeyboardController::SetReactive(RGBColor color, RGBColor react_color, unsigned short react_time, bool persist)
{
    std::vector<msige66_packet> sequence;

    MSIGE66KeyboardReactiveSequence(sequence, ToMSIGE66Color(color), ToMSIGE66Color(react_color), react_time, persist);
    SendSequence(sequence);
}
