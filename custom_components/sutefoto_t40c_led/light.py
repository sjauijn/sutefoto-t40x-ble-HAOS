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

from .const import CONF_MAC, DOMAIN, MAX_CCT_KELVIN, MIN_CCT_KELVIN
from .sutefoto import MODE_CCT, SuteFotoInstance

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    instance: SuteFotoInstance = entry.runtime_data
    async_add_entities([SuteFotoLight(instance, entry)])


class SuteFotoLight(LightEntity):
    """The light entity (HSI + CCT color modes). No state read-back exists."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_supported_color_modes = {ColorMode.HS, ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = MIN_CCT_KELVIN
    _attr_max_color_temp_kelvin = MAX_CCT_KELVIN

    def __init__(self, instance: SuteFotoInstance, entry: ConfigEntry) -> None:
        self._instance = instance
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=entry.title,
            manufacturer="SuteFoto",
            model="T40X",
        )

    async def async_added_to_hass(self) -> None:
        self._instance.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._instance.remove_callback(self.async_write_ha_state)

    @property
    def is_on(self) -> bool:
        return self._instance.is_on

    @property
    def brightness(self) -> int:
        return round(self._instance.brightness_pct * 255 / 100)

    @property
    def color_mode(self) -> ColorMode:
        if self._instance.mode == MODE_CCT:
            return ColorMode.COLOR_TEMP
        return ColorMode.HS

    @property
    def hs_color(self) -> tuple[float, float]:
        return (self._instance.hue / 255 * 360, float(self._instance.saturation))

    @property
    def color_temp_kelvin(self) -> int:
        return self._instance.cct_kelvin

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            await self._instance.async_set_cct(
                color_temp_k=kwargs[ATTR_COLOR_TEMP_KELVIN], send=False
            )
        elif ATTR_HS_COLOR in kwargs:
            hue, sat = kwargs[ATTR_HS_COLOR]
            await self._instance.async_set_hsi(
                hue=round(hue / 360 * 255), saturation=round(sat), send=False
            )

        brightness_pct = None
        if ATTR_BRIGHTNESS in kwargs:
            brightness_pct = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)

        await self._instance.async_turn_on(brightness_pct)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._instance.async_turn_off()
