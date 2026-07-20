"""BLE connection and state for a single SuteFoto T40X light."""
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

FX_EFFECTS: dict[int, str] = {
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
    """Owns the BLE connection to one light and its (assumed) state.

    The light has no way to report its actual state back to us, so all
    state here is optimistic: we assume a write succeeded if it didn't
    raise, and we reflect that assumption immediately in the entities.
    """

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()

        # --- assumed state ---
        self.is_on: bool = False
        self.mode: str = MODE_HSI
        self.brightness_pct: int = 100
        self._last_brightness_pct: int = 100

        self.hue: int = 0
        self.saturation: int = 100

        self.cct_kelvin: int = 5600
        self.gm_compensation: int = 0

        self.rgbcw_red: int = 100
        self.rgbcw_green: int = 0
        self.rgbcw_blue: int = 0
        self.rgbcw_less_warm: int = 0
        self.rgbcw_more_warm: int = 0

        self.fx_effect: int = 1
        self.fx_frequency: int = 5

        self._update_callbacks: list = []

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    def register_callback(self, callback) -> None:
        self._update_callbacks.append(callback)

    def remove_callback(self, callback) -> None:
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    def _push_update(self) -> None:
        for cb in self._update_callbacks:
            cb()

    async def async_connect(self) -> None:
        """Establish (or verify) the BLE connection. Raises on failure."""
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
        """Write a command, (re)connecting if necessary. Raises on failure."""
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

        # Update the UI immediately: this device cannot report its real
        # state back, so we treat our own command as authoritative right
        # away. We do NOT wait for the BLE write, because BLE writes can
        # take many seconds or silently hang, and if we waited the UI
        # would look "stuck on the old value" for that whole time - which
        # is exactly the symptom we're avoiding here.
        self._push_update()
        await self._write(data)

    # -- Public commands, each raises on BLE failure so callers can report it --

    async def async_turn_on(self, brightness_pct: int | None = None) -> None:
        self.is_on = True
        if brightness_pct is not None:
            self.brightness_pct = max(1, brightness_pct)
        elif self.brightness_pct <= 0:
            self.brightness_pct = self._last_brightness_pct or 100
        await self._send_current_mode()

    async def async_turn_off(self) -> None:
        if self.brightness_pct > 0:
            self._last_brightness_pct = self.brightness_pct
        self.is_on = False
        await self._send_current_mode()

    async def async_set_brightness_pct(self, brightness_pct: int) -> None:
        self.brightness_pct = max(0, min(100, brightness_pct))
        self.is_on = self.brightness_pct > 0
        await self._send_current_mode()

    async def async_set_mode(self, mode: str, send: bool = True) -> None:
        if self.mode == MODE_RGBCW and mode != MODE_RGBCW:
            self._reset_rgbcw()
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
        self.mode = MODE_RGBCW
        await self._send_current_mode()

    async def async_set_fx(
        self,
        effect_id: int | None = None,
        frequency: int | None = None,
        intensity: int | None = None,
    ) -> None:
        if effect_id is not None:
            self.fx_effect = effect_id
        if frequency is not None:
            self.fx_frequency = frequency
        if intensity is not None:
            self.brightness_pct = intensity
        self.mode = MODE_FX
        await self._send_current_mode()
