/*---------------------------------------------------------*\
| RGBController_SteelSeriesMSIGE66Keyboard.cpp              |
|                                                           |
|   RGBController for the MSI GE66 Raider keyboard          |
|   (SteelSeries KLC, 1038:1122)                            |
|                                                           |
|   This file is part of the OpenRGB project                |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include "RGBController_SteelSeriesMSIGE66Keyboard.h"
#include "RGBControllerKeyNames.h"
#include "KeyboardLayoutManager.h"

#define MSIGE66_KEYBOARD_COLOR_SHIFT_MAX_COLORS     14
#define MSIGE66_KEYBOARD_BREATHING_MAX_COLORS       8

/*---------------------------------------------------------*\
| GE66 key matrix (6 rows by 17 columns, English layout)    |
| from the msi-ge66-klc hidcode-matrix-layout-nonvariant.   |
| The value of each key is its HID usage code, which is     |
| also the key ID on the wire.                              |
\*---------------------------------------------------------*/
keyboard_keymap_overlay_values msi_ge66_keyboard_layout
{
    KEYBOARD_SIZE_EMPTY,
    {
        {   /* Values not set in empty keyboard */   },
        {
            /* Add more regional layout fixes here */
        }
    },
    {
        /*-----------------------------------------------------------------------------------------------------------------------------*\
        | Edit Keys                                                                                                                     |
        |   Zone,   Row,    Column,     Value,      Key,                        Alt name,               OpCode,                         |
        \*-----------------------------------------------------------------------------------------------------------------------------*/
        {   0,      0,      0,         41,        KEY_EN_ESCAPE,             KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      1,         58,        KEY_EN_F1,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      2,         59,        KEY_EN_F2,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      3,         60,        KEY_EN_F3,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      4,         61,        KEY_EN_F4,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      5,         62,        KEY_EN_F5,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      6,         63,        KEY_EN_F6,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      7,         64,        KEY_EN_F7,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      8,         65,        KEY_EN_F8,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,      9,         66,        KEY_EN_F9,                 KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,     10,         67,        KEY_EN_F10,                KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,     11,         68,        KEY_EN_F11,                KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,     12,         69,        KEY_EN_F12,                KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,     14,         73,        KEY_EN_INSERT,             KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      0,     15,        102,        KEY_EN_POWER,              KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      0,         53,        KEY_EN_BACK_TICK,          KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      1,         30,        KEY_EN_1,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      2,         31,        KEY_EN_2,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      3,         32,        KEY_EN_3,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      4,         33,        KEY_EN_4,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      5,         34,        KEY_EN_5,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      6,         35,        KEY_EN_6,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      7,         36,        KEY_EN_7,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      8,         37,        KEY_EN_8,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,      9,         38,        KEY_EN_9,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,     10,         39,        KEY_EN_0,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,     11,         45,        KEY_EN_MINUS,              KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,     12,         46,        KEY_EN_EQUALS,             KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,     14,         42,        KEY_EN_BACKSPACE,          KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      1,     16,         74,        KEY_EN_HOME,               KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      0,         43,        KEY_EN_TAB,                KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      1,         20,        KEY_EN_Q,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      2,         26,        KEY_EN_W,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      3,          8,        KEY_EN_E,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      4,         21,        KEY_EN_R,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      5,         23,        KEY_EN_T,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      6,         28,        KEY_EN_Y,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      7,         24,        KEY_EN_U,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      8,         12,        KEY_EN_I,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,      9,         18,        KEY_EN_O,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,     10,         19,        KEY_EN_P,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,     11,         47,        KEY_EN_LEFT_BRACKET,       KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,     12,         48,        KEY_EN_RIGHT_BRACKET,      KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,     13,         49,        KEY_EN_ANSI_BACK_SLASH,    KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      2,     15,         75,        KEY_EN_PAGE_UP,            KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      0,         57,        KEY_EN_CAPS_LOCK,          KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      1,          4,        KEY_EN_A,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      2,         22,        KEY_EN_S,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      3,          7,        KEY_EN_D,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      4,          9,        KEY_EN_F,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      5,         10,        KEY_EN_G,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      6,         11,        KEY_EN_H,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      7,         13,        KEY_EN_J,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      8,         14,        KEY_EN_K,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,      9,         15,        KEY_EN_L,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,     10,         51,        KEY_EN_SEMICOLON,          KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,     11,         52,        KEY_EN_QUOTE,              KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,     13,         40,        KEY_EN_ANSI_ENTER,         KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      3,     15,         78,        KEY_EN_PAGE_DOWN,          KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      0,        225,        KEY_EN_LEFT_SHIFT,         KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      2,         29,        KEY_EN_Z,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      3,         27,        KEY_EN_X,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      4,          6,        KEY_EN_C,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      5,         25,        KEY_EN_V,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      6,          5,        KEY_EN_B,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      7,         17,        KEY_EN_N,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      8,         16,        KEY_EN_M,                  KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,      9,         54,        KEY_EN_COMMA,              KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,     10,         55,        KEY_EN_PERIOD,             KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,     11,         56,        KEY_EN_FORWARD_SLASH,      KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,     13,        229,        KEY_EN_RIGHT_SHIFT,        KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,     15,         82,        KEY_EN_UP_ARROW,           KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      4,     16,         77,        KEY_EN_END,                KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,      0,        224,        KEY_EN_LEFT_CONTROL,       KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,      2,        227,        KEY_EN_LEFT_WINDOWS,       KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,      3,        226,        KEY_EN_LEFT_ALT,           KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,      6,         44,        KEY_EN_SPACE,              KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,      9,        230,        KEY_EN_RIGHT_ALT,          KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,     10,        100,        KEY_EN_ISO_BACK_SLASH,     KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,     11,        240,        "Fn",                      KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,     12,        228,        KEY_EN_RIGHT_CONTROL,      KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,     14,         80,        KEY_EN_LEFT_ARROW,         KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,     15,         81,        KEY_EN_DOWN_ARROW,         KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
        {   0,      5,     16,         79,        KEY_EN_RIGHT_ARROW,        KEY_EN_UNUSED,            KEYBOARD_OPCODE_INSERT_SHIFT_RIGHT, },
    }
};

/**------------------------------------------------------------------*\
    @name MSI GE66 Raider Keyboard
    @category Keyboard
    @type USB
    @save :white_check_mark:
    @direct :white_check_mark:
    @effects :white_check_mark:
    @detectors DetectSteelSeriesMSIGE66Keyboard
    @comment The keyboard is a SteelSeries KLC device (1038:1122).
        Static and Direct were tested on firmware 2.36.
\*-------------------------------------------------------------------*/

RGBController_SteelSeriesMSIGE66Keyboard::RGBController_SteelSeriesMSIGE66Keyboard(SteelSeriesMSIGE66KeyboardController* controller_ptr)
{
    controller                  = controller_ptr;

    name                        = controller->GetName();
    vendor                      = "MSI";
    type                        = DEVICE_TYPE_KEYBOARD;
    description                 = "MSI GE66 Raider Keyboard (SteelSeries KLC)";
    location                    = controller->GetLocation();
    serial                      = controller->GetSerial();
    version                     = controller->GetVersion();

    stream_ready                = false;

    mode Direct;
    Direct.name                 = "Direct";
    Direct.value                = MSIGE66_KEYBOARD_MODE_DIRECT;
    Direct.flags                = MODE_FLAG_HAS_PER_LED_COLOR;
    Direct.color_mode           = MODE_COLORS_PER_LED;
    modes.push_back(Direct);

    mode Static;
    Static.name                 = "Static";
    Static.value                = MSIGE66_KEYBOARD_MODE_STATIC;
    Static.flags                = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_MANUAL_SAVE;
    Static.color_mode           = MODE_COLORS_MODE_SPECIFIC;
    Static.colors_min           = 1;
    Static.colors_max           = 1;
    Static.colors.resize(1);
    Static.colors[0]            = ToRGBColor(255, 255, 255);
    modes.push_back(Static);

    mode ColorShift;
    ColorShift.name             = "Color Shift";
    ColorShift.value            = MSIGE66_KEYBOARD_MODE_COLOR_SHIFT;
    ColorShift.flags            = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_HAS_SPEED | MODE_FLAG_MANUAL_SAVE;
    ColorShift.color_mode       = MODE_COLORS_MODE_SPECIFIC;
    ColorShift.speed_min        = MSIGE66_SPEED_MIN;
    ColorShift.speed_max        = MSIGE66_SPEED_MAX;
    ColorShift.speed            = MSIGE66_SPEED_DEFAULT;
    ColorShift.colors_min       = 2;
    ColorShift.colors_max       = MSIGE66_KEYBOARD_COLOR_SHIFT_MAX_COLORS;
    ColorShift.colors.resize(2);
    ColorShift.colors[0]        = ToRGBColor(255, 0, 0);
    ColorShift.colors[1]        = ToRGBColor(0, 0, 255);
    modes.push_back(ColorShift);

    mode Breathing;
    Breathing.name              = "Breathing";
    Breathing.value             = MSIGE66_KEYBOARD_MODE_BREATHING;
    Breathing.flags             = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_HAS_SPEED | MODE_FLAG_MANUAL_SAVE;
    Breathing.color_mode        = MODE_COLORS_MODE_SPECIFIC;
    Breathing.speed_min         = MSIGE66_SPEED_MIN;
    Breathing.speed_max         = MSIGE66_SPEED_MAX;
    Breathing.speed             = MSIGE66_SPEED_DEFAULT;
    Breathing.colors_min        = 1;
    Breathing.colors_max        = MSIGE66_KEYBOARD_BREATHING_MAX_COLORS;
    Breathing.colors.resize(1);
    Breathing.colors[0]         = ToRGBColor(255, 255, 255);
    modes.push_back(Breathing);

    /*---------------------------------------------------------*\
    | Reactive colors are the color keys rest at, then the      |
    | color they flash when pressed                             |
    \*---------------------------------------------------------*/
    mode Reactive;
    Reactive.name               = "Reactive";
    Reactive.value              = MSIGE66_KEYBOARD_MODE_REACTIVE;
    Reactive.flags              = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_MANUAL_SAVE;
    Reactive.color_mode         = MODE_COLORS_MODE_SPECIFIC;
    Reactive.colors_min         = 2;
    Reactive.colors_max         = 2;
    Reactive.colors.resize(2);
    Reactive.colors[0]          = ToRGBColor(0, 0, 64);
    Reactive.colors[1]          = ToRGBColor(255, 255, 255);
    modes.push_back(Reactive);

    mode Off;
    Off.name                    = "Off";
    Off.value                   = MSIGE66_KEYBOARD_MODE_OFF;
    Off.flags                   = MODE_FLAG_MANUAL_SAVE;
    Off.color_mode              = MODE_COLORS_NONE;
    modes.push_back(Off);

    SetupZones();
}

RGBController_SteelSeriesMSIGE66Keyboard::~RGBController_SteelSeriesMSIGE66Keyboard()
{
    /*---------------------------------------------------------*\
    | Delete the matrix map                                     |
    \*---------------------------------------------------------*/
    for(unsigned int zone_index = 0; zone_index < zones.size(); zone_index++)
    {
        if(zones[zone_index].matrix_map != NULL)
        {
            delete[] zones[zone_index].matrix_map->map;
            delete zones[zone_index].matrix_map;
        }
    }

    delete controller;
}

void RGBController_SteelSeriesMSIGE66Keyboard::SetupZones()
{
    KeyboardLayoutManager new_kb(KEYBOARD_LAYOUT_ANSI_QWERTY, KEYBOARD_SIZE_EMPTY);
    new_kb.ChangeKeys(msi_ge66_keyboard_layout);

    zone new_zone;
    matrix_map_type* new_map        = new matrix_map_type;

    new_zone.name                   = "Keyboard";
    new_zone.type                   = ZONE_TYPE_MATRIX;
    new_zone.matrix_map             = new_map;
    new_zone.matrix_map->height     = new_kb.GetRowCount();
    new_zone.matrix_map->width      = new_kb.GetColumnCount();
    new_zone.matrix_map->map        = new unsigned int[new_map->height * new_map->width];
    new_zone.leds_count             = new_kb.GetKeyCount();
    new_zone.leds_min               = new_zone.leds_count;
    new_zone.leds_max               = new_zone.leds_count;

    new_kb.GetKeyMap(new_map->map, KEYBOARD_MAP_FILL_TYPE_COUNT);

    for(unsigned int led_idx = 0; led_idx < new_zone.leds_count; led_idx++)
    {
        led new_led;
        new_led.name                = new_kb.GetKeyNameAt(led_idx);
        new_led.value               = new_kb.GetKeyValueAt(led_idx);
        leds.push_back(new_led);
    }

    zones.push_back(new_zone);

    SetupColors();
}

void RGBController_SteelSeriesMSIGE66Keyboard::ResizeZone(int /*zone*/, int /*new_size*/)
{
    /*---------------------------------------------------------*\
    | This device does not support resizing zones               |
    \*---------------------------------------------------------*/
}

void RGBController_SteelSeriesMSIGE66Keyboard::DeviceUpdateLEDs()
{
    unsigned char   ids[MSIGE66_KEY_COUNT];
    msige66_color   key_colors[MSIGE66_KEY_COUNT];
    unsigned int    key_count = 0;

    if(modes[active_mode].value != MSIGE66_KEYBOARD_MODE_DIRECT)
    {
        return;
    }

    /*---------------------------------------------------------*\
    | Keys have to be in host stream mode before direct writes  |
    \*---------------------------------------------------------*/
    if(!stream_ready)
    {
        controller->SetHostStream();
        stream_ready = true;
    }

    for(unsigned int led_idx = 0; led_idx < leds.size() && key_count < MSIGE66_KEY_COUNT; led_idx++)
    {
        ids[key_count]              = leds[led_idx].value;
        key_colors[key_count].red   = RGBGetRValue(colors[led_idx]);
        key_colors[key_count].green = RGBGetGValue(colors[led_idx]);
        key_colors[key_count].blue  = RGBGetBValue(colors[led_idx]);
        key_count++;
    }

    controller->SetDirect(key_count, ids, key_colors);
}

void RGBController_SteelSeriesMSIGE66Keyboard::UpdateZoneLEDs(int /*zone*/)
{
    DeviceUpdateLEDs();
}

void RGBController_SteelSeriesMSIGE66Keyboard::UpdateSingleLED(int /*led*/)
{
    DeviceUpdateLEDs();
}

void RGBController_SteelSeriesMSIGE66Keyboard::DeviceUpdateMode()
{
    ApplyMode(false);
}

/*---------------------------------------------------------*\
| save_to_flash is only sent from here, when the user asks  |
| to save the active mode. Direct mode has nothing to save. |
\*---------------------------------------------------------*/
void RGBController_SteelSeriesMSIGE66Keyboard::DeviceSaveMode()
{
    if(modes[active_mode].flags & MODE_FLAG_MANUAL_SAVE)
    {
        ApplyMode(true);
    }
}

void RGBController_SteelSeriesMSIGE66Keyboard::ApplyMode(bool persist)
{
    mode&           active = modes[active_mode];
    msige66_effect  effect;

    if(active.value == MSIGE66_KEYBOARD_MODE_DIRECT)
    {
        DeviceUpdateLEDs();
        return;
    }

    /*---------------------------------------------------------*\
    | Any table sent below takes the keys out of host stream    |
    \*---------------------------------------------------------*/
    stream_ready = false;

    switch(active.value)
    {
        case MSIGE66_KEYBOARD_MODE_STATIC:
            controller->SetStatic(active.colors[0], persist);
            break;

        case MSIGE66_KEYBOARD_MODE_COLOR_SHIFT:
            SteelSeriesMSIGE66Controller::FillEffect(&effect, MSIGE66_EFFECT_COLORSHIFT, active.colors, active.speed);
            controller->SetEffect(&effect, persist);
            break;

        case MSIGE66_KEYBOARD_MODE_BREATHING:
            SteelSeriesMSIGE66Controller::FillEffect(&effect, MSIGE66_EFFECT_BREATHE, active.colors, active.speed);
            controller->SetEffect(&effect, persist);
            break;

        case MSIGE66_KEYBOARD_MODE_REACTIVE:
            controller->SetReactive(active.colors[0], active.colors[1], MSIGE66_KEY_REACT_TIME_DEFAULT, persist);
            break;

        case MSIGE66_KEYBOARD_MODE_OFF:
            controller->SetStatic(ToRGBColor(0, 0, 0), persist);
            break;
    }
}
