/*---------------------------------------------------------*\
| SteelSeriesMSIGE66KeyboardController.h                    |
|                                                           |
|   Driver for the MSI GE66 Raider per-key keyboard         |
|   (SteelSeries KLC, 1038:1122)                            |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include "SteelSeriesMSIGE66Controller.h"

class SteelSeriesMSIGE66KeyboardController : public SteelSeriesMSIGE66Controller
{
public:
    SteelSeriesMSIGE66KeyboardController(hid_device* dev_handle, const char* path, std::string dev_name);
    ~SteelSeriesMSIGE66KeyboardController();

    void            SetHostStream();
    void            SetDirect(unsigned int count, const unsigned char* ids, const msige66_color* colors);
    void            SetStatic(RGBColor color, bool persist);
    bool            SetEffect(const msige66_effect* effect, bool persist);
    void            SetReactive(RGBColor color, RGBColor react_color, unsigned short react_time, bool persist);
};
