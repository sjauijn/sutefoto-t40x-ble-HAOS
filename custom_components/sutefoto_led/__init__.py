"""The SuteFoto LED integration."""
from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_MAC
from .sutefoto import SuteFotoInstance

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.SELECT, Platform.NUMBER]

type SuteFotoConfigEntry = ConfigEntry[SuteFotoInstance]


async def async_setup_entry(hass: HomeAssistant, entry: SuteFotoConfigEntry) -> bool:
    """Set up SuteFoto LED from a config entry."""
    mac = entry.data[CONF_MAC]

    ble_device = bluetooth.async_ble_device_from_address(hass, mac, connectable=True)
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Could not find a SuteFoto LED light with address {mac} nearby"
        )

    instance = SuteFotoInstance(ble_device)

    try:
        await instance.async_connect()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(
            f"Could not connect to SuteFoto LED light {mac}: {err}"
        ) from err

    entry.runtime_data = instance

    @callback
    def _async_update_ble(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        instance.set_ble_device(service_info.device)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_update_ble,
            {"address": mac},
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SuteFotoConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.runtime_data is not None:
        await entry.runtime_data.async_disconnect()
    return unload_ok
