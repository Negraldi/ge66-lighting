/*---------------------------------------------------------*\
| RGBController_SteelSeriesMSIGE66Keyboard.h                |
|                                                           |
|   RGBController for the MSI GE66 Raider keyboard          |
|   (SteelSeries KLC, 1038:1122)                            |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include "RGBController.h"
#include "SteelSeriesMSIGE66KeyboardController.h"

enum
{
    MSIGE66_KEYBOARD_MODE_DIRECT        = 0,
    MSIGE66_KEYBOARD_MODE_STATIC        = 1,
    MSIGE66_KEYBOARD_MODE_COLOR_SHIFT   = 2,
    MSIGE66_KEYBOARD_MODE_BREATHING     = 3,
    MSIGE66_KEYBOARD_MODE_REACTIVE      = 4,
    MSIGE66_KEYBOARD_MODE_OFF           = 5,
};

class RGBController_SteelSeriesMSIGE66Keyboard : public RGBController
{
public:
    RGBController_SteelSeriesMSIGE66Keyboard(SteelSeriesMSIGE66KeyboardController* controller_ptr);
    ~RGBController_SteelSeriesMSIGE66Keyboard();

    void        SetupZones();
    void        ResizeZone(int zone, int new_size);

    void        DeviceUpdateLEDs();
    void        UpdateZoneLEDs(int zone);
    void        UpdateSingleLED(int led);

    void        DeviceUpdateMode();
    void        DeviceSaveMode();

private:
    SteelSeriesMSIGE66KeyboardController*   controller;
    bool                                    stream_ready;

    void        ApplyMode(bool persist);
};
