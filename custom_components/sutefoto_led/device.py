"""BLE device wrapper for a SuteFoto T40X light."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    CHAR_UUID,
    DEFAULT_CCT,
    DEFAULT_FX_EFFECT,
    DEFAULT_FX_FREQUENCY,
    DEFAULT_FX_INTENSITY,
    DEFAULT_GM,
    DEFAULT_HUE,
    DEFAULT_SATURATION,
    MODE_CCT,
    MODE_FX,
    MODE_HSI,
    MODE_RGBCW,
)
from . import protocol

_LOGGER = logging.getLogger(__name__)

DISCONNECT_DELAY = 30


class SuteFotoState:
    """In-memory state of the light (device has no read-back for these)."""

    def __init__(self) -> None:
        self.is_on: bool = False
        self.mode: str = MODE_HSI
        self.brightness_pct: int = 100

        self.hue: int = DEFAULT_HUE
        self.saturation: int = DEFAULT_SATURATION

        self.cct_kelvin: int = DEFAULT_CCT
        self.gm_compensation: int = DEFAULT_GM

        self.rgbcw_red: int = 100
        self.rgbcw_green: int = 0
        self.rgbcw_blue: int = 0
        self.rgbcw_less_warm: int = 0
        self.rgbcw_more_warm: int = 0

        self.fx_effect: int = DEFAULT_FX_EFFECT
        self.fx_frequency: int = DEFAULT_FX_FREQUENCY
        self.fx_intensity: int = DEFAULT_FX_INTENSITY

        # brightness used before turning off, restored on turn_on
        self._last_brightness_pct: int = 100


class SuteFotoDevice:
    """Manages the BLE connection and command dispatch to the light."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self.state = SuteFotoState()
        self._listeners: list[Callable[[], None]] = []

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback to be notified on state changes.

        Returns a function that removes the listener again.
        """
        self._listeners.append(callback)

        def _remove() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return _remove

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    async def _ensure_connected(self) -> BleakClientWithServiceCache:
        if self._client is not None and self._client.is_connected:
            return self._client
        _LOGGER.debug("Connecting to %s", self._ble_device.address)
        client = await establish_connection(
            BleakClientWithServiceCache,
            self._ble_device,
            self._ble_device.address,
        )
        self._client = client
        return client

    async def _write(self, data: bytes) -> None:
        async with self._lock:
            client = await self._ensure_connected()
            await client.write_gatt_char(CHAR_UUID, data, response=False)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_disconnect(self) -> None:
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    # -- High level commands -------------------------------------------------

    async def async_send_current_mode(self) -> None:
        """(Re)send the command matching the current in-memory state."""
        s = self.state
        brightness = s.brightness_pct if s.is_on else 0

        if s.mode == MODE_HSI:
            data = protocol.build_hsi(brightness, s.saturation, s.hue)
        elif s.mode == MODE_CCT:
            data = protocol.build_cct(brightness, s.cct_kelvin, s.gm_compensation)
        elif s.mode == MODE_RGBCW:
            if s.is_on:
                data = protocol.build_rgbcw(
                    s.rgbcw_red,
                    s.rgbcw_green,
                    s.rgbcw_blue,
                    s.rgbcw_less_warm,
                    s.rgbcw_more_warm,
                )
            else:
                data = protocol.build_rgbcw(0, 0, 0, 0, 0)
        elif s.mode == MODE_FX:
            fx_intensity = max(10, brightness) if s.is_on else 10
            data = protocol.build_fx(s.fx_effect, s.fx_frequency, fx_intensity)
        else:
            return

        # Reflect the new state in the UI immediately - the light itself
        # has no way to report its state back, so we treat the command we
        # are about to send as authoritative right away instead of waiting
        # for the (possibly slow, possibly failing) BLE write to finish.
        self._notify()
        await self._write(data)

    async def async_turn_on(self, brightness_pct: int | None = None) -> None:
        s = self.state
        s.is_on = True
        if brightness_pct is not None:
            s.brightness_pct = max(1, brightness_pct)
        elif s.brightness_pct <= 0:
            s.brightness_pct = s._last_brightness_pct or 100
        await self.async_send_current_mode()

    async def async_turn_off(self) -> None:
        s = self.state
        if s.brightness_pct > 0:
            s._last_brightness_pct = s.brightness_pct
        s.is_on = False
        await self.async_send_current_mode()

    async def async_set_brightness_pct(self, brightness_pct: int) -> None:
        s = self.state
        s.brightness_pct = max(0, min(100, brightness_pct))
        s.is_on = s.brightness_pct > 0
        await self.async_send_current_mode()

    async def async_set_mode(self, mode: str) -> None:
        self.state.mode = mode
        await self.async_send_current_mode()

    async def async_set_hsi(
        self, hue: int | None = None, saturation: int | None = None
    ) -> None:
        s = self.state
        if hue is not None:
            s.hue = hue
        if saturation is not None:
            s.saturation = saturation
        s.mode = MODE_HSI
        await self.async_send_current_mode()

    async def async_set_cct(
        self,
        color_temp_k: int | None = None,
        gm_compensation: int | None = None,
    ) -> None:
        s = self.state
        if color_temp_k is not None:
            s.cct_kelvin = color_temp_k
        if gm_compensation is not None:
            s.gm_compensation = gm_compensation
        s.mode = MODE_CCT
        await self.async_send_current_mode()

    async def async_set_rgbcw(
        self,
        red: int | None = None,
        green: int | None = None,
        blue: int | None = None,
        less_warm: int | None = None,
        more_warm: int | None = None,
    ) -> None:
        s = self.state
        if red is not None:
            s.rgbcw_red = red
        if green is not None:
            s.rgbcw_green = green
        if blue is not None:
            s.rgbcw_blue = blue
        if less_warm is not None:
            s.rgbcw_less_warm = less_warm
        if more_warm is not None:
            s.rgbcw_more_warm = more_warm
        s.mode = MODE_RGBCW
        await self.async_send_current_mode()

    async def async_set_fx(
        self,
        effect_id: int | None = None,
        frequency: int | None = None,
        intensity: int | None = None,
    ) -> None:
        s = self.state
        if effect_id is not None:
            s.fx_effect = effect_id
        if frequency is not None:
            s.fx_frequency = frequency
        if intensity is not None:
            s.fx_intensity = intensity
            s.brightness_pct = intensity
        s.mode = MODE_FX
        await self.async_send_current_mode()
