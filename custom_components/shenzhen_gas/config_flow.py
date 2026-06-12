from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenGasApi, ShenzhenGasApiError
from .const import (
    CONF_ACCOUNT_CHANNEL_ID,
    CONF_CCB_CUST_NO,
    CONF_CODE_ID,
    CONF_METER_NO,
    DEFAULT_ACCOUNT_CHANNEL_ID,
    DOMAIN,
)


class ShenzhenGasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shenzhen Gas."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)

            api = ShenzhenGasApi(
                session,
                ccb_cust_no=user_input[CONF_CCB_CUST_NO],
                meter_no=user_input[CONF_METER_NO],
                code_id=user_input[CONF_CODE_ID],
            )

            try:
                await api.async_get_day_data()
            except ShenzhenGasApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_CCB_CUST_NO]}_{user_input[CONF_METER_NO]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"深圳燃气 {user_input[CONF_METER_NO]}",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CCB_CUST_NO): str,
                vol.Required(CONF_METER_NO): str,
                vol.Required(CONF_CODE_ID): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )