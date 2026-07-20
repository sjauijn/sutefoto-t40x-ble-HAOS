"""Light platform for SuteFoto LED."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MAC,
    DOMAIN,
    MAX_CCT_KELVIN,
    MIN_CCT_KELVIN,
    MODE_CCT,
    MODE_HSI,
)
from .device import SuteFotoDevice

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the light platform."""
    device: SuteFotoDevice = entry.runtime_data
    async_add_entities([SuteFotoLight(device, entry)])


class SuteFotoLight(LightEntity):
    """Representation of the SuteFoto light (HSI + CCT color modes)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_supported_color_modes = {ColorMode.HS, ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = MIN_CCT_KELVIN
    _attr_max_color_temp_kelvin = MAX_CCT_KELVIN

    def __init__(self, device: SuteFotoDevice, entry: ConfigEntry) -> None:
        self._device = device
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=entry.title,
            manufacturer="SuteFoto",
            model="T40X",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._device.add_listener(self.async_write_ha_state))

    async def async_will_remove_from_hass(self) -> None:
        pass

    @property
    def is_on(self) -> bool:
        return self._device.state.is_on

    @property
    def brightness(self) -> int:
        return round(self._device.state.brightness_pct * 255 / 100)

    @property
    def color_mode(self) -> ColorMode:
        if self._device.state.mode == MODE_CCT:
            return ColorMode.COLOR_TEMP
        return ColorMode.HS

    @property
    def hs_color(self) -> tuple[float, float] | None:
        s = self._device.state
        return (s.hue / 255 * 360, float(s.saturation))

    @property
    def color_temp_kelvin(self) -> int | None:
        return self._device.state.cct_kelvin

    async def async_turn_on(self, **kwargs: Any) -> None:
        s = self._device.state

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            s.mode = MODE_CCT
            s.cct_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
        elif ATTR_HS_COLOR in kwargs:
            s.mode = MODE_HSI
            hue, sat = kwargs[ATTR_HS_COLOR]
            s.hue = round(hue / 360 * 255)
            s.saturation = round(sat)

        brightness_pct = None
        if ATTR_BRIGHTNESS in kwargs:
            brightness_pct = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)

        await self._device.async_turn_on(brightness_pct)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.async_turn_off()
