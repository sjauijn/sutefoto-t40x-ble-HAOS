"""Number platform for SuteFoto LED: extra tunable parameters."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MAC, DOMAIN
from .device import SuteFotoDevice

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    device: SuteFotoDevice = entry.runtime_data
    entities = [
        SuteFotoGMNumber(device, entry),
        SuteFotoRgbcwNumber(device, entry, "red", "RGBCW Red"),
        SuteFotoRgbcwNumber(device, entry, "green", "RGBCW Green"),
        SuteFotoRgbcwNumber(device, entry, "blue", "RGBCW Blue"),
        SuteFotoRgbcwNumber(device, entry, "less_warm", "RGBCW Less Warm"),
        SuteFotoRgbcwNumber(device, entry, "more_warm", "RGBCW More Warm"),
        SuteFotoFxFrequencyNumber(device, entry),
    ]
    async_add_entities(entities)


class _BaseNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.SLIDER

    def __init__(self, device: SuteFotoDevice, entry: ConfigEntry) -> None:
        self._device = device
        self._mac = entry.data[CONF_MAC]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=entry.title,
            manufacturer="SuteFoto",
            model="T40X",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._device.add_listener(self.async_write_ha_state))


class SuteFotoGMNumber(_BaseNumber):
    """Green/Magenta compensation, used in CCT mode."""

    _attr_translation_key = "gm_compensation"
    _attr_native_min_value = -10
    _attr_native_max_value = 10
    _attr_native_step = 1

    def __init__(self, device: SuteFotoDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{self._mac}_gm_compensation"

    @property
    def native_value(self) -> float:
        return self._device.state.gm_compensation

    async def async_set_native_value(self, value: float) -> None:
        await self._device.async_set_cct(gm_compensation=round(value))


class SuteFotoRgbcwNumber(_BaseNumber):
    """One channel (R/G/B/LessWarm/MoreWarm) of RGBCW mode."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self, device: SuteFotoDevice, entry: ConfigEntry, field: str, name: str
    ) -> None:
        super().__init__(device, entry)
        self._field = field
        self._attr_translation_key = f"rgbcw_{field}"
        self._attr_unique_id = f"{self._mac}_rgbcw_{field}"

    @property
    def native_value(self) -> float:
        return getattr(self._device.state, f"rgbcw_{self._field}")

    async def async_set_native_value(self, value: float) -> None:
        kwargs = {self._field: round(value)}
        await self._device.async_set_rgbcw(**kwargs)


class SuteFotoFxFrequencyNumber(_BaseNumber):
    """Frequency parameter used in FX mode."""

    _attr_translation_key = "fx_frequency"
    _attr_native_min_value = 1
    _attr_native_max_value = 10
    _attr_native_step = 1

    def __init__(self, device: SuteFotoDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{self._mac}_fx_frequency"

    @property
    def native_value(self) -> float:
        return self._device.state.fx_frequency

    async def async_set_native_value(self, value: float) -> None:
        await self._device.async_set_fx(frequency=round(value))
