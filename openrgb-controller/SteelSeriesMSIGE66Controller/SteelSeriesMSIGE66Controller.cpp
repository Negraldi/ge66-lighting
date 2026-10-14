/*---------------------------------------------------------*\
| SteelSeriesMSIGE66Controller.cpp                          |
|                                                           |
|   Shared HID transport for the SteelSeries ALC light bar  |
|   and KLC keyboard of the MSI GE66 Raider                 |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include <cstring>
#include <chrono>
#include <thread>
#include "SteelSeriesMSIGE66Controller.h"
#include "LogManager.h"
#include "StringUtils.h"

using namespace std::chrono_literals;

#define MSIGE66_CONTROLLER_NAME             "SteelSeriesMSIGE66Controller"
#define MSIGE66_COMMAND_GAP                 10ms
#define MSIGE66_VERSION_TIMEOUT_MS          500

SteelSeriesMSIGE66Controller::SteelSeriesMSIGE66Controller(hid_device* dev_handle, const char* path, std::string dev_name)
{
    dev         = dev_handle;
    location    = path;
    name        = dev_name;
    version     = ReadVersion();
}

SteelSeriesMSIGE66Controller::~SteelSeriesMSIGE66Controller()
{
    hid_close(dev);
}

std::string SteelSeriesMSIGE66Controller::GetLocation()
{
    return("HID: " + location);
}

std::string SteelSeriesMSIGE66Controller::GetName()
{
    return(name);
}

std::string SteelSeriesMSIGE66Controller::GetSerial()
{
    wchar_t serial_string[128];
    int     ret = hid_get_serial_number_string(dev, serial_string, 128);

    if(ret != 0)
    {
        return("");
    }

    return(StringUtils::wstring_to_string(serial_string));
}

std::string SteelSeriesMSIGE66Controller::GetVersion()
{
    return(version);
}

/*---------------------------------------------------------*\
| Output reports are 64 bytes and feature reports 524, both |
| sent with a leading report ID of 0. The firmware needs    |
| 10 ms between commands.                                   |
\*---------------------------------------------------------*/
void SteelSeriesMSIGE66Controller::SendPacket(const msige66_packet& packet)
{
    unsigned char   usb_buf[MSIGE66_FEATURE_SIZE + 1];
    int             result;

    usb_buf[0] = 0x00;
    memcpy(&usb_buf[1], packet.data, packet.size);

    if(packet.kind == MSIGE66_PACKET_FEATURE)
    {
        result = hid_send_feature_report(dev, usb_buf, packet.size + 1);
    }
    else
    {
        result = hid_write(dev, usb_buf, packet.size + 1);
    }

    if(result < 0)
    {
        LOG_WARNING("[%s] Failed to write a report to %s", MSIGE66_CONTROLLER_NAME, name.c_str());
    }

    std::this_thread::sleep_for(MSIGE66_COMMAND_GAP);
}

void SteelSeriesMSIGE66Controller::SendSequence(const std::vector<msige66_packet>& sequence)
{
    for(unsigned int packet_idx = 0; packet_idx < sequence.size(); packet_idx++)
    {
        SendPacket(sequence[packet_idx]);
    }
}

/*---------------------------------------------------------*\
| Fill an effect from OpenRGB mode colors. The caller sets  |
| the direction fields afterwards if the effect is a wave.  |
\*---------------------------------------------------------*/
void SteelSeriesMSIGE66Controller::FillEffect(msige66_effect* effect, unsigned char type, const std::vector<RGBColor>& colors, unsigned int speed)
{
    memset(effect, 0x00, sizeof(msige66_effect));

    effect->type        = type;
    effect->speed       = MSIGE66_SPEED_TO_TICKS(speed);
    effect->num_colors  = (colors.size() > MSIGE66_EFFECT_MAX_COLORS) ? MSIGE66_EFFECT_MAX_COLORS : colors.size();

    for(unsigned int color_idx = 0; color_idx < effect->num_colors; color_idx++)
    {
        effect->colors[color_idx].red   = RGBGetRValue(colors[color_idx]);
        effect->colors[color_idx].green = RGBGetGValue(colors[color_idx]);
        effect->colors[color_idx].blue  = RGBGetBValue(colors[color_idx]);
    }

    MSIGE66DefaultPositions(effect->num_colors, effect->positions);
}

/*---------------------------------------------------------*\
| fw_version request, the reply is fw_minor then fw_major.  |
| Stale input reports are dropped first.                    |
\*---------------------------------------------------------*/
std::string SteelSeriesMSIGE66Controller::ReadVersion()
{
    unsigned char   in_buf[MSIGE66_OUTPUT_SIZE];
    msige66_packet  packet;
    std::string     return_string = "";

    while(hid_read_timeout(dev, in_buf, sizeof(in_buf), 0) > 0)
    {
    }

    MSIGE66FwVersionRequest(&packet);
    SendPacket(packet);

    if(hid_read_timeout(dev, in_buf, sizeof(in_buf), MSIGE66_VERSION_TIMEOUT_MS) >= 2)
    {
        return_string = std::to_string(in_buf[1]) + "." + std::to_string(in_buf[0]);
    }

    return(return_string);
}
