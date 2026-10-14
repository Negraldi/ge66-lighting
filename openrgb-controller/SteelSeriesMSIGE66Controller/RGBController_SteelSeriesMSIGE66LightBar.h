/*---------------------------------------------------------*\
| RGBController_SteelSeriesMSIGE66LightBar.h                |
|                                                           |
|   RGBController for the MSI GE66 Raider light bar         |
|   (SteelSeries ALC, 1038:1132)                            |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include "RGBController.h"
#include "SteelSeriesMSIGE66LightBarController.h"

enum
{
    MSIGE66_BAR_MODE_DIRECT         = 0,
    MSIGE66_BAR_MODE_STATIC         = 1,
    MSIGE66_BAR_MODE_COLOR_SHIFT    = 2,
    MSIGE66_BAR_MODE_COLOR_WAVE     = 3,
    MSIGE66_BAR_MODE_RAINBOW_WAVE   = 4,
    MSIGE66_BAR_MODE_BREATHING      = 5,
    MSIGE66_BAR_MODE_OFF            = 6,
};

class RGBController_SteelSeriesMSIGE66LightBar : public RGBController
{
public:
    RGBController_SteelSeriesMSIGE66LightBar(SteelSeriesMSIGE66LightBarController* controller_ptr);
    ~RGBController_SteelSeriesMSIGE66LightBar();

    void        SetupZones();
    void        ResizeZone(int zone, int new_size);

    void        DeviceUpdateLEDs();
    void        UpdateZoneLEDs(int zone);
    void        UpdateSingleLED(int led);

    void        DeviceUpdateMode();
    void        DeviceSaveMode();

private:
    SteelSeriesMSIGE66LightBarController*   controller;
    int                                     applied_mode;
    bool                                    direct_written;
    int                                     applied_brightness;
    unsigned int                            applied_speed;
    unsigned int                            applied_direction;
    std::vector<RGBColor>                   applied_colors;

    void        ApplyMode(bool persist);
};
