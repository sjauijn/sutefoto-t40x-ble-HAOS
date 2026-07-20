# SuteFoto LED Light — Home Assistant Integration

Custom Home Assistant integration for the **SuteFoto T40X/T40C RGB** video light
(the one controlled by the "SS LED" app), connected directly over Bluetooth LE —
no cloud, no hub required. Protocol reverse engineered from BLE HCI snoop logs.

## Important: this light has no state feedback

The light's BLE protocol is write-only — it never reports its actual on/off
state, brightness, or color back to Home Assistant. This is a hardware/firmware
limitation, not a bug in this integration (the same is true of most cheap BLE
LED controllers). Entities are therefore marked as **assumed state**: Home
Assistant shows whatever it last *told* the light, not what the light is
*actually* doing. If the light is also controlled from the SS LED app, or loses
power, Home Assistant's view of it can get out of sync until you send a new
command.

Also note: the light's Bluetooth radio advertises whenever it has mains power,
independent of whether its LEDs are switched on. Seeing it in Home Assistant's
"discovered" list does not mean the light is currently lit.

## Features

- **Light entity** — on/off, brightness, HS color (HSI mode), color temperature (CCT mode)
- **Select: Mode** — switch between HSI / CCT / RGBCW / FX
- **Select: FX Effect** — Lightning, Police, Fire truck, Ambulance, Fire, Fireworks,
  Fault bulb, TV, RGB Circle, Paparazzi
- **Number entities** — Green/Magenta compensation (CCT mode), RGBCW channel levels,
  FX Frequency

## Installation via HACS (custom repository)

1. HACS → Integrations → ⋮ menu (top right) → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **SuteFoto LED Light**, restart Home Assistant

## Setup

1. Settings → Devices & services → **Add Integration** → search for "SuteFoto LED"
2. If discovered, select your light from the list; otherwise choose
   **"Enter MAC address manually…"** and type it in (find it with a BLE scanner
   app such as nRF Connect — look for a device named like `ST40CRGB-XXXXXX`)
3. Home Assistant will attempt an actual Bluetooth connection during setup to
   confirm the light is reachable before the integration is added. If this
   fails, make sure the light is not currently connected to the SS LED app.

## Requirements

- Home Assistant instance with Bluetooth support (built-in adapter or a
  [Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)) within
  range of the light
- The light must not be actively connected to the SS LED phone app at setup
  time or while Home Assistant is controlling it (BLE only allows one active
  connection)

## Disclaimer

This is an unofficial, community-reverse-engineered integration and is not
affiliated with or endorsed by SuteFoto.
