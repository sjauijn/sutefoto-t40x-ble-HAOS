"""Number platform for SuteFoto LED: extra tunable parameters."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MAC, DOMAIN
from .sutefoto import SuteFotoInstance

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    instance: SuteFotoInstance = entry.runtime_data
    async_add_entities(
        [
            SuteFotoGMNumber(instance, entry),
            SuteFotoRgbcwNumber(instance, entry, "red"),
            SuteFotoRgbcwNumber(instance, entry, "green"),
            SuteFotoRgbcwNumber(instance, entry, "blue"),
            SuteFotoRgbcwNumber(instance, entry, "less_warm"),
            SuteFotoRgbcwNumber(instance, entry, "more_warm"),
            SuteFotoFxFrequencyNumber(instance, entry),
        ]
    )


class _BaseNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_mode = NumberMode.SLIDER

    def __init__(self, instance: SuteFotoInstance, entry: ConfigEntry) -> None:
        self._instance = instance
        self._mac = entry.data[CONF_MAC]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=entry.title,
            manufacturer="SuteFoto",
            model="T40X",
        )

    async def async_added_to_hass(self) -> None:
        self._instance.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._instance.remove_callback(self.async_write_ha_state)


class SuteFotoGMNumber(_BaseNumber):
    _attr_translation_key = "gm_compensation"
    _attr_native_min_value = -10
    _attr_native_max_value = 10
    _attr_native_step = 1

    def __init__(self, instance: SuteFotoInstance, entry: ConfigEntry) -> None:
        super().__init__(instance, entry)
        self._attr_unique_id = f"{self._mac}_gm_compensation"

    @property
    def native_value(self) -> float:
        return self._instance.gm_compensation

    async def async_set_native_value(self, value: float) -> None:
        await self._instance.async_set_cct(gm_compensation=round(value))


class SuteFotoRgbcwNumber(_BaseNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self, instance: SuteFotoInstance, entry: ConfigEntry, field: str
    ) -> None:
        super().__init__(instance, entry)
        self._field = field
        self._attr_translation_key = f"rgbcw_{field}"
        self._attr_unique_id = f"{self._mac}_rgbcw_{field}"

    @property
    def native_value(self) -> float:
        return getattr(self._instance, f"rgbcw_{self._field}")

    async def async_set_native_value(self, value: float) -> None:
        await self._instance.async_set_rgbcw(**{self._field: round(value)})


class SuteFotoFxFrequencyNumber(_BaseNumber):
    _attr_translation_key = "fx_frequency"
    _attr_native_min_value = 1
    _attr_native_max_value = 10
    _attr_native_step = 1

    def __init__(self, instance: SuteFotoInstance, entry: ConfigEntry) -> None:
        super().__init__(instance, entry)
        self._attr_unique_id = f"{self._mac}_fx_frequency"

    @property
    def native_value(self) -> float:
        return self._instance.fx_frequency

    async def async_set_native_value(self, value: float) -> None:
        await self._instance.async_set_fx(frequency=round(value))
