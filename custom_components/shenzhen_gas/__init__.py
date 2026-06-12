from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenGasApi
from .const import (
    CONF_ACCOUNT_CHANNEL_ID,
    CONF_CCB_CUST_NO,
    CONF_CODE_ID,
    CONF_METER_NO,
    DEFAULT_ACCOUNT_CHANNEL_ID,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ShenzhenGasCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    api = ShenzhenGasApi(
        session,
        ccb_cust_no=entry.data[CONF_CCB_CUST_NO],
        meter_no=entry.data[CONF_METER_NO],
        code_id=entry.data[CONF_CODE_ID],
        account_channel_id=entry.data.get(
            CONF_ACCOUNT_CHANNEL_ID,
            DEFAULT_ACCOUNT_CHANNEL_ID,
        ),
        authorization=entry.data.get(CONF_AUTHORIZATION),
    )

    coordinator = ShenzhenGasCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok