/*---------------------------------------------------------*\
| SteelSeriesMSIGE66Controller.h                            |
|                                                           |
|   Shared HID transport for the SteelSeries ALC light bar  |
|   and KLC keyboard of the MSI GE66 Raider                 |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include <string>
#include <vector>
#include <hidapi.h>
#include "RGBController.h"
#include "SteelSeriesMSIGE66Protocol.h"

/*---------------------------------------------------------*\
| Speed steps shown by OpenRGB and the effect cycle length  |
| they select, in firmware ticks (high speed, short cycle)  |
\*---------------------------------------------------------*/
#define MSIGE66_SPEED_MIN                   0
#define MSIGE66_SPEED_MAX                   9
#define MSIGE66_SPEED_DEFAULT               4
#define MSIGE66_SPEED_TO_TICKS(speed)       (1000 - ((speed) * 85))

class SteelSeriesMSIGE66Controller
{
public:
    SteelSeriesMSIGE66Controller(hid_device* dev_handle, const char* path, std::string dev_name);
    virtual ~SteelSeriesMSIGE66Controller();

    std::string     GetLocation();
    std::string     GetName();
    std::string     GetSerial();
    std::string     GetVersion();

    void            SendPacket(const msige66_packet& packet);
    void            SendSequence(const std::vector<msige66_packet>& sequence);

    static void     FillEffect(msige66_effect* effect, unsigned char type, const std::vector<RGBColor>& colors, unsigned int speed);

protected:
    hid_device*     dev;
    std::string     location;
    std::string     name;
    std::string     version;

private:
    std::string     ReadVersion();
};
