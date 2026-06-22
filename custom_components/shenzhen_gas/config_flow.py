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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._accounts: list[dict] = []
        self._selected_account: dict | None = None
        self._code_id: str | None = None
        self._account_channel_id: str = DEFAULT_ACCOUNT_CHANNEL_ID

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            self._code_id = user_input[CONF_CODE_ID]
            self._account_channel_id = DEFAULT_ACCOUNT_CHANNEL_ID

            try:
                self._accounts = await self._async_get_bound_accounts()
            except ShenzhenGasApiError:
                errors["base"] = "cannot_connect"
            else:
                if len(self._accounts) == 1:
                    self._selected_account = self._accounts[0]
                    return await self._async_auto_create_or_ask_meter()

                elif self._accounts:
                    return await self.async_step_account()

                else:
                    errors["base"] = "no_accounts"

        schema = vol.Schema(
            {
                vol.Required(CONF_CODE_ID): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_account(self, user_input=None):
        """Handle account selection when multiple bound accounts exist."""
        errors = {}

        if user_input is not None:
            try:
                self._selected_account = self._accounts[int(user_input["account"])]
                return await self._async_auto_create_or_ask_meter()
            except (IndexError, ValueError):
                errors["base"] = "cannot_connect"

        account_options = {
            str(index): self._account_label(account)
            for index, account in enumerate(self._accounts)
        }

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema({vol.Required("account"): vol.In(account_options)}),
            errors=errors,
        )

    async def async_step_meter(self, user_input=None):
        """Handle manual meter number fallback."""
        errors = {}

        if user_input is not None:
            try:
                return await self._async_create_entry_from_account(
                    self._selected_account or {},
                    user_input[CONF_METER_NO],
                    validate=True,
                )
            except ShenzhenGasApiError:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="meter",
            data_schema=vol.Schema({vol.Required(CONF_METER_NO): str}),
            errors=errors,
        )

    async def _async_get_bound_accounts(self) -> list[dict]:
        """Return accounts bound to the supplied CodeId."""
        session = async_get_clientsession(self.hass)
        api = ShenzhenGasApi(
            session,
            ccb_cust_no="",
            meter_no="",
            code_id=self._code_id or "",
            account_channel_id=self._account_channel_id,
        )

        return await api.async_get_bound_accounts()

    async def _async_auto_create_or_ask_meter(self):
        """Create entry automatically or ask for meter number."""
        try:
            ccb_cust_no = (self._selected_account or {}).get("ccbCustNo")
            meter_no = await self._async_find_working_meter_no(
                self._selected_account or {},
                ccb_cust_no,
            )
        except ShenzhenGasApiError:
            return await self.async_step_meter()

        return await self._async_create_entry_from_account(
            self._selected_account or {},
            meter_no,
            validate=False,
        )

    async def _async_create_entry_from_account(
        self,
        account: dict,
        meter_no: str,
        *,
        validate: bool,
    ):
        """Create a config entry from a bound account."""
        ccb_cust_no = account.get("ccbCustNo")
        if not ccb_cust_no:
            raise ShenzhenGasApiError("Bound account has no ccbCustNo")

        if validate:
            await self._async_validate_meter_no(ccb_cust_no, meter_no)

        await self.async_set_unique_id(f"{ccb_cust_no}_{meter_no}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"深圳燃气 {meter_no}",
            data={
                CONF_CCB_CUST_NO: ccb_cust_no,
                CONF_METER_NO: meter_no,
                CONF_CODE_ID: self._code_id,
                CONF_ACCOUNT_CHANNEL_ID: self._account_channel_id,
            },
        )

    async def _async_find_working_meter_no(
        self,
        account: dict,
        ccb_cust_no: str | None,
    ) -> str:
        """Find the bound account field accepted by the meter data API."""
        if not ccb_cust_no:
            raise ShenzhenGasApiError("Bound account has no ccbCustNo")

        candidates = [
            account.get("premId"),
            account.get("extAcctId"),
            account.get("ccbCustNo"),
        ]

        for candidate in dict.fromkeys(value for value in candidates if value):
            try:
                await self._async_validate_meter_no(ccb_cust_no, str(candidate))
            except ShenzhenGasApiError:
                continue

            return str(candidate)

        raise ShenzhenGasApiError("No working meter number found")

    async def _async_validate_meter_no(self, ccb_cust_no: str, meter_no: str) -> None:
        """Validate customer and meter number against daily meter data API."""
        session = async_get_clientsession(self.hass)
        api = ShenzhenGasApi(
            session,
            ccb_cust_no=ccb_cust_no,
            meter_no=meter_no,
            code_id=self._code_id or "",
            account_channel_id=self._account_channel_id,
        )
        await api.async_get_day_data()

    @staticmethod
    def _account_label(account: dict) -> str:
        """Return a human-readable label for a bound account."""
        parts = [
            account.get("address"),
            account.get("ccbCustNo"),
            account.get("premId"),
        ]

        return " / ".join(str(part) for part in parts if part) or "未命名账户"
