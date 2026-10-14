/*---------------------------------------------------------*\
| SteelSeriesMSIGE66LightBarController.h                    |
|                                                           |
|   Driver for the MSI GE66 Raider light bar                |
|   (SteelSeries ALC, 1038:1132, 35 zones)                  |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include "SteelSeriesMSIGE66Controller.h"

class SteelSeriesMSIGE66LightBarController : public SteelSeriesMSIGE66Controller
{
public:
    SteelSeriesMSIGE66LightBarController(hid_device* dev_handle, const char* path, std::string dev_name);
    ~SteelSeriesMSIGE66LightBarController();

    void            SetBrightness(unsigned char level);
    void            SetDirect(std::vector<RGBColor>& colors);
    void            SetHostStream();
    void            SetStatic(RGBColor color, bool persist);
    bool            SetEffect(const msige66_effect* effect, bool persist);
};
