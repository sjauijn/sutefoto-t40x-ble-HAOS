"""Select platform for SuteFoto LED: light mode and FX effect."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MAC,
    DOMAIN,
    FX_EFFECTS,
    FX_EFFECTS_REVERSE,
    MODE_CCT,
    MODE_FX,
    MODE_HSI,
    MODE_RGBCW,
    MODES,
)
from .device import SuteFotoDevice

PARALLEL_UPDATES = 0

MODE_LABELS = {
    MODE_HSI: "HSI (Color)",
    MODE_CCT: "CCT (White)",
    MODE_RGBCW: "RGBCW",
    MODE_FX: "FX (Effects)",
}
MODE_LABELS_REVERSE = {v: k for k, v in MODE_LABELS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    device: SuteFotoDevice = entry.runtime_data
    async_add_entities(
        [
            SuteFotoModeSelect(device, entry),
            SuteFotoFxEffectSelect(device, entry),
        ]
    )


class _BaseSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

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


class SuteFotoModeSelect(_BaseSelect):
    """Select the active light mode: HSI / CCT / RGBCW / FX."""

    _attr_translation_key = "mode"
    _attr_options = [MODE_LABELS[m] for m in MODES]

    def __init__(self, device: SuteFotoDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{self._mac}_mode"

    @property
    def current_option(self) -> str:
        return MODE_LABELS[self._device.state.mode]

    async def async_select_option(self, option: str) -> None:
        mode = MODE_LABELS_REVERSE[option]
        await self._device.async_set_mode(mode)


class SuteFotoFxEffectSelect(_BaseSelect):
    """Select the active FX effect."""

    _attr_translation_key = "fx_effect"
    _attr_options = list(FX_EFFECTS.values())

    def __init__(self, device: SuteFotoDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_unique_id = f"{self._mac}_fx_effect"

    @property
    def current_option(self) -> str:
        return FX_EFFECTS[self._device.state.fx_effect]

    async def async_select_option(self, option: str) -> None:
        effect_id = FX_EFFECTS_REVERSE[option]
        await self._device.async_set_fx(effect_id=effect_id)
