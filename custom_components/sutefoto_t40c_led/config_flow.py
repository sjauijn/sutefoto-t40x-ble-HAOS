"""Config flow for SuteFoto LED integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.device_registry import format_mac

from .const import CONF_MAC, DOMAIN
from .sutefoto import SuteFotoInstance

_LOGGER = logging.getLogger(__name__)

MANUAL_ENTRY = "__manual__"


async def _async_validate_device(hass, mac: str) -> str | None:
    """Try to actually connect to the device. Return an error key, or None on success."""
    ble_device = async_ble_device_from_address(hass, mac, connectable=True)
    if ble_device is None:
        return "not_found"

    instance = SuteFotoInstance(ble_device)
    try:
        await instance.async_connect()
    except Exception:  # noqa: BLE001 - any BLE failure means "can't set this up"
        _LOGGER.debug("Could not connect to %s during setup", mac, exc_info=True)
        return "cannot_connect"
    finally:
        await instance.async_disconnect()
    return None


class SuteFotoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SuteFoto LED."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_mac: str | None = None
        self._discovered_name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle discovery via Bluetooth advertisement.

        Note: the light advertises over BLE whenever it has power, whether
        or not its LEDs are currently on - this step only means "a light was
        seen nearby", not "a light is currently lit".
        """
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        self._discovered_mac = discovery_info.address
        self._discovered_name = discovery_info.name or discovery_info.address
        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await _async_validate_device(self.hass, self._discovered_mac)
            if error is None:
                return self.async_create_entry(
                    title=self._discovered_name or self._discovered_mac,
                    data={CONF_MAC: self._discovered_mac},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered_name},
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user: pick a discovered device or enter manually."""
        discovered: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass, connectable=True):
            name = (info.name or "").upper()
            if name.startswith("ST40"):
                discovered[info.address] = f"{info.name} ({info.address})"

        if not discovered:
            return await self.async_step_manual()

        if user_input is not None:
            if user_input[CONF_MAC] == MANUAL_ENTRY:
                return await self.async_step_manual()
            mac = user_input[CONF_MAC]
            await self.async_set_unique_id(format_mac(mac))
            self._abort_if_unique_id_configured()

            error = await _async_validate_device(self.hass, mac)
            if error is None:
                return self.async_create_entry(
                    title=discovered[mac],
                    data={CONF_MAC: mac},
                )
            return self.async_show_form(
                step_id="user",
                data_schema=self._user_schema(discovered),
                errors={"base": error},
            )

        return self.async_show_form(
            step_id="user", data_schema=self._user_schema(discovered)
        )

    @staticmethod
    def _user_schema(discovered: dict[str, str]) -> vol.Schema:
        options = {**discovered, MANUAL_ENTRY: "Enter MAC address manually…"}
        return vol.Schema({vol.Required(CONF_MAC): vol.In(options)})

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual MAC address entry, with real connection validation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mac_raw = user_input[CONF_MAC].strip()
            try:
                mac = format_mac(mac_raw).upper()
            except ValueError:
                mac = ""

            if not mac or len(mac.replace(":", "")) != 12:
                errors["base"] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()

                error = await _async_validate_device(self.hass, mac)
                if error is None:
                    return self.async_create_entry(
                        title=f"SuteFoto LED ({mac})",
                        data={CONF_MAC: mac},
                    )
                errors["base"] = error

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_MAC): str}),
            errors=errors,
        )
