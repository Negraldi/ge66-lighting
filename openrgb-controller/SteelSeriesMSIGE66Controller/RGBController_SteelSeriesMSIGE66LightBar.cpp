/*---------------------------------------------------------*\
| RGBController_SteelSeriesMSIGE66LightBar.cpp              |
|                                                           |
|   RGBController for the MSI GE66 Raider light bar         |
|   (SteelSeries ALC, 1038:1132)                            |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include <cstdio>
#include "RGBController_SteelSeriesMSIGE66LightBar.h"

#define MSIGE66_BAR_BRIGHTNESS_MIN          0
#define MSIGE66_BAR_BRIGHTNESS_MAX          255
#define MSIGE66_BAR_WAVE_SCALE              40
#define MSIGE66_BAR_COLOR_SHIFT_MAX_COLORS  14
#define MSIGE66_BAR_BREATHING_MAX_COLORS    8
#define MSIGE66_BAR_MODE_NONE               -1

/**------------------------------------------------------------------*\
    @name MSI GE66 Raider Light Bar
    @category LEDStrip
    @type USB
    @save :white_check_mark:
    @direct :white_check_mark:
    @effects :white_check_mark:
    @detectors DetectSteelSeriesMSIGE66LightBar
    @comment The light bar is a SteelSeries ALC device (1038:1132).
        Static, effects and Off use the firmware and can be saved
        to flash. Wave direction and effect speed are not verified
        on hardware.
\*-------------------------------------------------------------------*/

RGBController_SteelSeriesMSIGE66LightBar::RGBController_SteelSeriesMSIGE66LightBar(SteelSeriesMSIGE66LightBarController* controller_ptr)
{
    controller                  = controller_ptr;

    name                        = controller->GetName();
    vendor                      = "MSI";
    type                        = DEVICE_TYPE_LEDSTRIP;
    description                 = "MSI GE66 Raider Light Bar (SteelSeries ALC)";
    location                    = controller->GetLocation();
    serial                      = controller->GetSerial();
    version                     = controller->GetVersion();

    applied_mode                = MSIGE66_BAR_MODE_NONE;
    direct_written              = false;
    applied_brightness          = MSIGE66_BAR_BRIGHTNESS_MAX;
    applied_speed               = 0;
    applied_direction           = 0;

    mode Direct;
    Direct.name                 = "Direct";
    Direct.value                = MSIGE66_BAR_MODE_DIRECT;
    Direct.flags                = MODE_FLAG_HAS_PER_LED_COLOR | MODE_FLAG_HAS_BRIGHTNESS;
    Direct.color_mode           = MODE_COLORS_PER_LED;
    Direct.brightness_min       = MSIGE66_BAR_BRIGHTNESS_MIN;
    Direct.brightness_max       = MSIGE66_BAR_BRIGHTNESS_MAX;
    Direct.brightness           = MSIGE66_BAR_BRIGHTNESS_MAX;
    modes.push_back(Direct);

    mode Static;
    Static.name                 = "Static";
    Static.value                = MSIGE66_BAR_MODE_STATIC;
    Static.flags                = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_HAS_BRIGHTNESS | MODE_FLAG_MANUAL_SAVE;
    Static.color_mode           = MODE_COLORS_MODE_SPECIFIC;
    Static.brightness_min       = MSIGE66_BAR_BRIGHTNESS_MIN;
    Static.brightness_max       = MSIGE66_BAR_BRIGHTNESS_MAX;
    Static.brightness           = MSIGE66_BAR_BRIGHTNESS_MAX;
    Static.colors_min           = 1;
    Static.colors_max           = 1;
    Static.colors.resize(1);
    Static.colors[0]            = ToRGBColor(255, 255, 255);
    modes.push_back(Static);

    mode ColorShift;
    ColorShift.name             = "Color Shift";
    ColorShift.value            = MSIGE66_BAR_MODE_COLOR_SHIFT;
    ColorShift.flags            = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_HAS_SPEED | MODE_FLAG_HAS_BRIGHTNESS | MODE_FLAG_MANUAL_SAVE;
    ColorShift.color_mode       = MODE_COLORS_MODE_SPECIFIC;
    ColorShift.speed_min        = MSIGE66_SPEED_MIN;
    ColorShift.speed_max        = MSIGE66_SPEED_MAX;
    ColorShift.speed            = MSIGE66_SPEED_DEFAULT;
    ColorShift.brightness_min   = MSIGE66_BAR_BRIGHTNESS_MIN;
    ColorShift.brightness_max   = MSIGE66_BAR_BRIGHTNESS_MAX;
    ColorShift.brightness       = MSIGE66_BAR_BRIGHTNESS_MAX;
    ColorShift.colors_min       = 2;
    ColorShift.colors_max       = MSIGE66_BAR_COLOR_SHIFT_MAX_COLORS;
    ColorShift.colors.resize(2);
    ColorShift.colors[0]        = ToRGBColor(255, 0, 0);
    ColorShift.colors[1]        = ToRGBColor(0, 0, 255);
    modes.push_back(ColorShift);

    mode ColorWave;
    ColorWave.name              = "Color Wave";
    ColorWave.value             = MSIGE66_BAR_MODE_COLOR_WAVE;
    ColorWave.flags             = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_HAS_SPEED | MODE_FLAG_HAS_DIRECTION_LR | MODE_FLAG_HAS_BRIGHTNESS | MODE_FLAG_MANUAL_SAVE;
    ColorWave.color_mode        = MODE_COLORS_MODE_SPECIFIC;
    ColorWave.speed_min         = MSIGE66_SPEED_MIN;
    ColorWave.speed_max         = MSIGE66_SPEED_MAX;
    ColorWave.speed             = MSIGE66_SPEED_DEFAULT;
    ColorWave.direction         = MODE_DIRECTION_RIGHT;
    ColorWave.brightness_min    = MSIGE66_BAR_BRIGHTNESS_MIN;
    ColorWave.brightness_max    = MSIGE66_BAR_BRIGHTNESS_MAX;
    ColorWave.brightness        = MSIGE66_BAR_BRIGHTNESS_MAX;
    ColorWave.colors_min        = 2;
    ColorWave.colors_max        = MSIGE66_BAR_COLOR_SHIFT_MAX_COLORS;
    ColorWave.colors.resize(2);
    ColorWave.colors[0]         = ToRGBColor(255, 0, 0);
    ColorWave.colors[1]         = ToRGBColor(0, 0, 255);
    modes.push_back(ColorWave);

    mode RainbowWave;
    RainbowWave.name            = "Rainbow Wave";
    RainbowWave.value           = MSIGE66_BAR_MODE_RAINBOW_WAVE;
    RainbowWave.flags           = MODE_FLAG_HAS_SPEED | MODE_FLAG_HAS_DIRECTION_LR | MODE_FLAG_HAS_BRIGHTNESS | MODE_FLAG_MANUAL_SAVE;
    RainbowWave.color_mode      = MODE_COLORS_NONE;
    RainbowWave.speed_min       = MSIGE66_SPEED_MIN;
    RainbowWave.speed_max       = MSIGE66_SPEED_MAX;
    RainbowWave.speed           = MSIGE66_SPEED_DEFAULT;
    RainbowWave.direction       = MODE_DIRECTION_RIGHT;
    RainbowWave.brightness_min  = MSIGE66_BAR_BRIGHTNESS_MIN;
    RainbowWave.brightness_max  = MSIGE66_BAR_BRIGHTNESS_MAX;
    RainbowWave.brightness      = MSIGE66_BAR_BRIGHTNESS_MAX;
    modes.push_back(RainbowWave);

    mode Breathing;
    Breathing.name              = "Breathing";
    Breathing.value             = MSIGE66_BAR_MODE_BREATHING;
    Breathing.flags             = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_HAS_SPEED | MODE_FLAG_HAS_BRIGHTNESS | MODE_FLAG_MANUAL_SAVE;
    Breathing.color_mode        = MODE_COLORS_MODE_SPECIFIC;
    Breathing.speed_min         = MSIGE66_SPEED_MIN;
    Breathing.speed_max         = MSIGE66_SPEED_MAX;
    Breathing.speed             = MSIGE66_SPEED_DEFAULT;
    Breathing.brightness_min    = MSIGE66_BAR_BRIGHTNESS_MIN;
    Breathing.brightness_max    = MSIGE66_BAR_BRIGHTNESS_MAX;
    Breathing.brightness        = MSIGE66_BAR_BRIGHTNESS_MAX;
    Breathing.colors_min        = 1;
    Breathing.colors_max        = MSIGE66_BAR_BREATHING_MAX_COLORS;
    Breathing.colors.resize(1);
    Breathing.colors[0]         = ToRGBColor(255, 255, 255);
    modes.push_back(Breathing);

    mode Off;
    Off.name                    = "Off";
    Off.value                   = MSIGE66_BAR_MODE_OFF;
    Off.flags                   = MODE_FLAG_MANUAL_SAVE;
    Off.color_mode              = MODE_COLORS_NONE;
    modes.push_back(Off);

    SetupZones();
}

RGBController_SteelSeriesMSIGE66LightBar::~RGBController_SteelSeriesMSIGE66LightBar()
{
    delete controller;
}

void RGBController_SteelSeriesMSIGE66LightBar::SetupZones()
{
    /*---------------------------------------------------------*\
    | One linear zone, LED 0 is the left end of the bar         |
    \*---------------------------------------------------------*/
    zone bar_zone;
    bar_zone.name           = "Light Bar";
    bar_zone.type           = ZONE_TYPE_LINEAR;
    bar_zone.leds_min       = MSIGE66_BAR_ZONES;
    bar_zone.leds_max       = MSIGE66_BAR_ZONES;
    bar_zone.leds_count     = MSIGE66_BAR_ZONES;
    bar_zone.matrix_map     = NULL;
    zones.push_back(bar_zone);

    for(unsigned int led_idx = 0; led_idx < MSIGE66_BAR_ZONES; led_idx++)
    {
        char led_name[32];
        snprintf(led_name, sizeof(led_name), "Light Bar LED %d", led_idx + 1);

        led new_led;
        new_led.name        = led_name;
        new_led.value       = led_idx;
        leds.push_back(new_led);
    }

    SetupColors();
}

void RGBController_SteelSeriesMSIGE66LightBar::ResizeZone(int /*zone*/, int /*new_size*/)
{
    /*---------------------------------------------------------*\
    | This device does not support resizing zones               |
    \*---------------------------------------------------------*/
}

void RGBController_SteelSeriesMSIGE66LightBar::DeviceUpdateLEDs()
{
    if(modes[active_mode].value != MSIGE66_BAR_MODE_DIRECT)
    {
        return;
    }

    /*-----------------------------------------------------*\
    | The color buffer starts all black and the frontend     |
    | pushes it on any mode update, brightness included.     |
    | Hold that back until a color was actually chosen, so   |
    | opening the application does not turn the bar off.     |
    \*-----------------------------------------------------*/
    if(!direct_written)
    {
        bool all_black = true;

        for(std::size_t led_idx = 0; led_idx < colors.size(); led_idx++)
        {
            if(colors[led_idx] != 0)
            {
                all_black = false;
                break;
            }
        }

        if(all_black)
        {
            return;
        }
    }

    direct_written = true;
    controller->SetDirect(colors);
}

void RGBController_SteelSeriesMSIGE66LightBar::UpdateZoneLEDs(int /*zone*/)
{
    DeviceUpdateLEDs();
}

void RGBController_SteelSeriesMSIGE66LightBar::UpdateSingleLED(int /*led*/)
{
    DeviceUpdateLEDs();
}

void RGBController_SteelSeriesMSIGE66LightBar::DeviceUpdateMode()
{
    ApplyMode(false);
}

/*---------------------------------------------------------*\
| save_to_flash is only sent from here, when the user asks  |
| to save the active mode. Direct mode has nothing to save. |
\*---------------------------------------------------------*/
void RGBController_SteelSeriesMSIGE66LightBar::DeviceSaveMode()
{
    if(modes[active_mode].flags & MODE_FLAG_MANUAL_SAVE)
    {
        ApplyMode(true);
    }
}

void RGBController_SteelSeriesMSIGE66LightBar::ApplyMode(bool persist)
{
    mode&           active      = modes[active_mode];
    msige66_effect  effect;

    if((active.flags & MODE_FLAG_HAS_BRIGHTNESS) && ((int)active.brightness != applied_brightness))
    {
        controller->SetBrightness(active.brightness);
        applied_brightness = active.brightness;
    }

    /*-----------------------------------------------------*\
    | A brightness change alone must not rewrite the tables: |
    | resending them restarts the lighting and makes the bar |
    | flicker while the slider is dragged.                   |
    \*-----------------------------------------------------*/
    if(!persist && applied_mode == active.value && applied_colors == active.colors
    && applied_speed == active.speed && applied_direction == active.direction)
    {
        return;
    }

    applied_colors      = active.colors;
    applied_speed       = active.speed;
    applied_direction   = active.direction;

    switch(active.value)
    {
        case MSIGE66_BAR_MODE_DIRECT:
            /*---------------------------------------------*\
            | Direct is the mode selected at startup, with  |
            | an all black color buffer. Writing it then    |
            | would turn off whatever the bar is showing,   |
            | so the first write waits for a color change.  |
            | After another mode, the zones have to go back |
            | to host stream first.                         |
            \*---------------------------------------------*/
            if(applied_mode != MSIGE66_BAR_MODE_NONE)
            {
                controller->SetHostStream();
                DeviceUpdateLEDs();
            }
            applied_mode = active.value;
            return;

        case MSIGE66_BAR_MODE_STATIC:
            controller->SetStatic(active.colors[0], persist);
            break;

        case MSIGE66_BAR_MODE_COLOR_SHIFT:
            SteelSeriesMSIGE66Controller::FillEffect(&effect, MSIGE66_EFFECT_COLORSHIFT, active.colors, active.speed);
            controller->SetEffect(&effect, persist);
            break;

        case MSIGE66_BAR_MODE_COLOR_WAVE:
        case MSIGE66_BAR_MODE_RAINBOW_WAVE:
            {
                std::vector<RGBColor> wave_colors = active.colors;

                if(active.value == MSIGE66_BAR_MODE_RAINBOW_WAVE)
                {
                    wave_colors.clear();
                    wave_colors.push_back(ToRGBColor(255, 0, 0));
                    wave_colors.push_back(ToRGBColor(255, 255, 0));
                    wave_colors.push_back(ToRGBColor(0, 255, 0));
                    wave_colors.push_back(ToRGBColor(0, 255, 255));
                    wave_colors.push_back(ToRGBColor(0, 0, 255));
                    wave_colors.push_back(ToRGBColor(255, 0, 255));
                }

                SteelSeriesMSIGE66Controller::FillEffect(&effect, MSIGE66_EFFECT_COLORSHIFT, wave_colors, active.speed);
                effect.has_direction        = 1;
                effect.direction_type       = MSIGE66_DIRECTION_HORIZONTAL;
                effect.direction_inverted   = (active.direction == MODE_DIRECTION_LEFT) ? 1 : 0;
                effect.scale                = MSIGE66_BAR_WAVE_SCALE;
                controller->SetEffect(&effect, persist);
            }
            break;

        case MSIGE66_BAR_MODE_BREATHING:
            SteelSeriesMSIGE66Controller::FillEffect(&effect, MSIGE66_EFFECT_BREATHE, active.colors, active.speed);
            controller->SetEffect(&effect, persist);
            break;

        case MSIGE66_BAR_MODE_OFF:
            controller->SetStatic(ToRGBColor(0, 0, 0), persist);
            break;
    }

    applied_mode = active.value;
}
