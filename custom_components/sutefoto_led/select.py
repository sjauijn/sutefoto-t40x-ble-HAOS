"""Select platform for SuteFoto LED: light mode and FX effect."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MAC, DOMAIN
from .sutefoto import FX_EFFECTS, MODE_CCT, MODE_FX, MODE_HSI, MODE_RGBCW, SuteFotoInstance

PARALLEL_UPDATES = 0

MODE_LABELS = {
    MODE_HSI: "HSI (Color)",
    MODE_CCT: "CCT (White)",
    MODE_RGBCW: "RGBCW",
    MODE_FX: "FX (Effects)",
}
MODE_LABELS_REVERSE = {v: k for k, v in MODE_LABELS.items()}
FX_EFFECTS_REVERSE = {v: k for k, v in FX_EFFECTS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    instance: SuteFotoInstance = entry.runtime_data
    async_add_entities(
        [
            SuteFotoModeSelect(instance, entry),
            SuteFotoFxEffectSelect(instance, entry),
        ]
    )


class _BaseSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True

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


class SuteFotoModeSelect(_BaseSelect):
    _attr_translation_key = "mode"
    _attr_options = list(MODE_LABELS.values())

    def __init__(self, instance: SuteFotoInstance, entry: ConfigEntry) -> None:
        super().__init__(instance, entry)
        self._attr_unique_id = f"{self._mac}_mode"

    @property
    def current_option(self) -> str:
        return MODE_LABELS[self._instance.mode]

    async def async_select_option(self, option: str) -> None:
        await self._instance.async_set_mode(MODE_LABELS_REVERSE[option])


class SuteFotoFxEffectSelect(_BaseSelect):
    _attr_translation_key = "fx_effect"
    _attr_options = list(FX_EFFECTS.values())

    def __init__(self, instance: SuteFotoInstance, entry: ConfigEntry) -> None:
        super().__init__(instance, entry)
        self._attr_unique_id = f"{self._mac}_fx_effect"

    @property
    def current_option(self) -> str:
        return FX_EFFECTS[self._instance.fx_effect]

    async def async_select_option(self, option: str) -> None:
        await self._instance.async_set_fx(effect_id=FX_EFFECTS_REVERSE[option])
