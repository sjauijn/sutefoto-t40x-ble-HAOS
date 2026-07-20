from __future__ import annotations

import asyncio
import logging

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from . import protocol

_LOGGER = logging.getLogger(__name__)

CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

MODE_HSI = "hsi"
MODE_CCT = "cct"
MODE_RGBCW = "rgbcw"
MODE_FX = "fx"

FX_EFFECT_OFF = 0

FX_EFFECTS: dict[int, str] = {
    0: "Off",
    1: "Lightning",
    2: "Police",
    3: "Fire truck",
    4: "Ambulance",
    5: "Fire",
    6: "Fireworks",
    7: "Fault bulb",
    8: "TV",
    9: "RGB Circle",
    10: "Paparazzi",
}


class SuteFotoInstance:

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()


        self.is_on: bool = False
        self.mode: str = MODE_HSI
        self.brightness_pct: int = 100
        self._last_brightness_pct: int = 100

        self.available: bool = True

        self.hue: int = 0
        self.saturation: int = 100

        self.cct_kelvin: int = 5600
        self.gm_compensation: int = 0

        self.rgbcw_red: int = 0
        self.rgbcw_green: int = 0
        self.rgbcw_blue: int = 0
        self.rgbcw_less_warm: int = 0
        self.rgbcw_more_warm: int = 0

        self.fx_effect: int = FX_EFFECT_OFF
        self.fx_frequency: int = 5

        self._update_callbacks: list = []

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    def set_available(self, available: bool) -> None:
        if self.available != available:
            self.available = available
            if not available:
                self._client = None
            self._push_update()

    def register_callback(self, callback) -> None:
        self._update_callbacks.append(callback)

    def remove_callback(self, callback) -> None:
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    def _push_update(self) -> None:
        for cb in self._update_callbacks:
            cb()

    async def async_connect(self) -> None:
        if self._client is not None and self._client.is_connected:
            return
        async with self._lock:
            if self._client is not None and self._client.is_connected:
                return
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self._ble_device.address,
            )

    async def async_disconnect(self) -> None:
        if self._client is not None and self._client.is_connected:
            try:
                await self._client.disconnect()
            except BleakError:
                pass
        self._client = None

    async def _write(self, data: bytes) -> None:
        async with self._lock:
            if self._client is None or not self._client.is_connected:
                self._client = await establish_connection(
                    BleakClientWithServiceCache,
                    self._ble_device,
                    self._ble_device.address,
                )
            await self._client.write_gatt_char(CHAR_UUID, data, response=False)

    async def _send_current_mode(self) -> None:
        brightness = self.brightness_pct if self.is_on else 0

        if self.mode == MODE_HSI:
            data = protocol.build_hsi(brightness, self.hue, self.saturation)
        elif self.mode == MODE_CCT:
            data = protocol.build_cct(
                brightness, self.cct_kelvin, self.gm_compensation
            )
        elif self.mode == MODE_RGBCW:
            if self.is_on:
                data = protocol.build_rgbcw(
                    self.rgbcw_red,
                    self.rgbcw_green,
                    self.rgbcw_blue,
                    self.rgbcw_less_warm,
                    self.rgbcw_more_warm,
                )
            else:
                data = protocol.build_rgbcw(0, 0, 0, 0, 0)
        elif self.mode == MODE_FX:
            fx_intensity = max(10, brightness) if self.is_on else 10
            data = protocol.build_fx(self.fx_effect, self.fx_frequency, fx_intensity)
        else:
            return


        self._push_update()
        await self._write(data)


    async def async_turn_on(
        self, brightness_pct: int | None = None, mode_changed: bool = False
    ) -> None:
        was_off = not self.is_on
        self.is_on = True
        if brightness_pct is not None:
            self.brightness_pct = max(1, brightness_pct)
        elif self.brightness_pct <= 0:
            self.brightness_pct = self._last_brightness_pct or 100
        await self._send_current_mode()
        if was_off and mode_changed:
            await asyncio.sleep(0.5)
            await self._send_current_mode()

    async def async_turn_off(self) -> None:
        if self.brightness_pct > 0:
            self._last_brightness_pct = self.brightness_pct
        self.is_on = False
        was_fx = self.mode == MODE_FX
        if was_fx:
            self.fx_effect = FX_EFFECT_OFF
            self.mode = MODE_HSI
        await self._send_current_mode()
        if was_fx:
            await asyncio.sleep(0.5)
            await self._send_current_mode()

    async def async_set_brightness_pct(self, brightness_pct: int) -> None:
        self.brightness_pct = max(0, min(100, brightness_pct))
        self.is_on = self.brightness_pct > 0
        await self._send_current_mode()

    async def async_set_mode(self, mode: str, send: bool = True) -> None:
        if self.mode == MODE_RGBCW and mode != MODE_RGBCW:
            self._reset_rgbcw()
        if self.mode == MODE_FX and mode != MODE_FX:
            self.fx_effect = FX_EFFECT_OFF
        if mode == MODE_FX:
            self.mode = mode
            self._push_update()
            return
        self.mode = mode
        if send:
            await self._send_current_mode()

    def _reset_rgbcw(self) -> None:
        self.rgbcw_red = 0
        self.rgbcw_green = 0
        self.rgbcw_blue = 0
        self.rgbcw_less_warm = 0
        self.rgbcw_more_warm = 0

    async def async_set_hsi(
        self,
        hue: int | None = None,
        saturation: int | None = None,
        send: bool = True,
    ) -> None:
        if hue is not None:
            self.hue = hue
        if saturation is not None:
            self.saturation = saturation
        if self.mode == MODE_RGBCW:
            self._reset_rgbcw()
        if self.mode == MODE_FX:
            self.fx_effect = FX_EFFECT_OFF
        self.mode = MODE_HSI
        if send:
            await self._send_current_mode()

    async def async_set_cct(
        self,
        color_temp_k: int | None = None,
        gm_compensation: int | None = None,
        send: bool = True,
    ) -> None:
        if color_temp_k is not None:
            self.cct_kelvin = color_temp_k
        if gm_compensation is not None:
            self.gm_compensation = gm_compensation
        if self.mode == MODE_RGBCW:
            self._reset_rgbcw()
        if self.mode == MODE_FX:
            self.fx_effect = FX_EFFECT_OFF
        self.mode = MODE_CCT
        if send:
            await self._send_current_mode()

    async def async_set_rgbcw(
        self,
        red: int | None = None,
        green: int | None = None,
        blue: int | None = None,
        less_warm: int | None = None,
        more_warm: int | None = None,
    ) -> None:
        if red is not None:
            self.rgbcw_red = red
        if green is not None:
            self.rgbcw_green = green
        if blue is not None:
            self.rgbcw_blue = blue
        if less_warm is not None:
            self.rgbcw_less_warm = less_warm
        if more_warm is not None:
            self.rgbcw_more_warm = more_warm
        if self.mode == MODE_FX:
            self.fx_effect = FX_EFFECT_OFF
        self.mode = MODE_RGBCW
        await self._send_current_mode()

    async def async_set_fx(
        self,
        effect_id: int | None = None,
        frequency: int | None = None,
        intensity: int | None = None,
    ) -> None:
        if effect_id == FX_EFFECT_OFF:
            self._push_update()
            return
        was_off = self.fx_effect == FX_EFFECT_OFF
        if effect_id is not None:
            self.fx_effect = effect_id
        if frequency is not None:
            self.fx_frequency = frequency
        if intensity is not None:
            self.brightness_pct = intensity
        self.mode = MODE_FX
        await self._send_current_mode()
        if was_off:
            await asyncio.sleep(0.5)
            await self._send_current_mode()
