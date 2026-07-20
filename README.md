# SuteFoto LED Light — Home Assistant Integration

Custom Home Assistant integration for the **SuteFoto T40X/T40C RGB** video light
(the one controlled by the "SS LED" app), connected directly over Bluetooth LE —
no cloud, no hub required.

The BLE protocol was reverse engineered from BLE HCI snoop logs of the official app.

## Features

- **Light entity** — on/off, brightness, HS color (HSI mode), color temperature (CCT mode)
- **Select: Mode** — switch between HSI / CCT / RGBCW / FX
- **Select: FX Effect** — Lightning, Police, Fire truck, Ambulance, Fire, Fireworks,
  Fault bulb, TV, RGB Circle, Paparazzi
- **Number entities** — Green/Magenta compensation (CCT mode), RGBCW channel levels
  (Red/Green/Blue/Less Warm/More Warm), FX Frequency

## Installation via HACS (custom repository)

1. HACS → Integrations → ⋮ menu (top right) → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **SuteFoto LED Light**, restart Home Assistant

## Setup

1. Settings → Devices & services → **Add Integration** → search for "SuteFoto LED"
2. If your light is discovered automatically it will appear in the list; otherwise
   enter its Bluetooth MAC address manually (find it with a BLE scanner app such as
   nRF Connect — look for a device named like `ST40CRGB-XXXXXX`)

## Requirements

- Home Assistant instance with Bluetooth support (built-in adapter or a
  [Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)) within
  range of the light
- The light must not be actively connected to the SS LED phone app at the same time
  (BLE only allows one active connection)

## Disclaimer

This is an unofficial, community-reverse-engineered integration and is not
affiliated with or endorsed by SuteFoto.
