from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

import aiohttp
import async_timeout


class ShenzhenGasApiError(Exception):
    """Shenzhen Gas API error."""


class ShenzhenGasAuthError(ShenzhenGasApiError):
    """Shenzhen Gas auth error."""


class ShenzhenGasApi:
    """Client for Shenzhen Gas mini-program API."""

    BASE_URL = "https://wechat.szgas.com.cn"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        ccb_cust_no: str,
        meter_no: str,
        code_id: str,
        account_channel_id: str = "538273580",
    ) -> None:
        self._session = session
        self._ccb_cust_no = ccb_cust_no
        self._meter_no = meter_no
        self._code_id = code_id
        self._account_channel_id = account_channel_id

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    @property
    def meter_no(self) -> str:
        """Return gas meter number."""
        return self._meter_no

    def update_meter_no(self, meter_no: str) -> None:
        """Update gas meter number."""
        self._meter_no = meter_no

    @property
    def ccb_cust_no(self) -> str:
        """Return customer number."""
        return self._ccb_cust_no

    @property
    def auth_headers(self) -> dict[str, str]:
        """Return headers for token request."""
        return {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "accountChannelId": self._account_channel_id,
            "ChannelTye": "WX_XCX",
            "Referer": "https://servicewechat.com/wx6188bb06271804e1/326/page-frame.html",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 MiniProgramEnv/Mac "
                "MicroMessenger/7.0.20"
            ),
        }

    def _build_headers(self, access_token: str) -> dict[str, str]:
        """Return request headers."""
        return {
            "Authorization": f"bearer {access_token}",
            "CodeId": self._code_id,
            "accountChannelId": self._account_channel_id,
            "ChannelTye": "WX_XCX",
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Referer": "https://servicewechat.com/wx6188bb06271804e1/326/page-frame.html",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 MiniProgramEnv/Mac "
                "MicroMessenger/7.0.20"
            ),
        }

    async def async_login(self) -> str:
        """Get OAuth access token."""
        url = f"{self.BASE_URL}/api/auth/oauth/token"

        try:
            async with async_timeout.timeout(20):
                async with self._session.post(
                    url,
                    headers=self.auth_headers,
                    auth=aiohttp.BasicAuth("test", "test"),
                    data={
                        "grant_type": "client_credentials",
                        "scope": "server",
                    },
                ) as resp:
                    text = await resp.text()

                    if resp.status != 200:
                        raise ShenzhenGasAuthError(
                            f"Auth HTTP {resp.status}: {text[:300]}"
                        )

                    data = await resp.json(content_type=None)

        except ShenzhenGasApiError:
            raise
        except Exception as err:
            raise ShenzhenGasAuthError(f"Auth request failed: {err}") from err

        access_token = data.get("access_token")
        if not access_token:
            raise ShenzhenGasAuthError(f"No access_token in auth response: {data}")

        expires_in = int(data.get("expires_in") or 7200)

        self._access_token = access_token

        # 提前 5 分钟刷新，避免刚好过期
        self._token_expires_at = datetime.now() + timedelta(
            seconds=max(expires_in - 300, 60)
        )

        return access_token

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now() < self._token_expires_at
        ):
            return self._access_token

        return await self.async_login()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        retry_auth: bool = True,
    ) -> dict:
        """Send request to Shenzhen Gas API."""
        url = f"{self.BASE_URL}{path}"
        access_token = await self.async_get_access_token()

        try:
            async with async_timeout.timeout(20):
                async with self._session.request(
                    method,
                    url,
                    headers=self._build_headers(access_token),
                    params=params,
                    json=json,
                ) as resp:
                    text = await resp.text()

                    if resp.status in (401, 403) and retry_auth:
                        self._access_token = None
                        self._token_expires_at = None
                        return await self._request(
                            method,
                            path,
                            params=params,
                            json=json,
                            retry_auth=False,
                        )

                    if resp.status != 200:
                        raise ShenzhenGasApiError(
                            f"HTTP {resp.status}: {text[:300]}"
                        )

                    data = await resp.json(content_type=None)

        except ShenzhenGasApiError:
            raise
        except Exception as err:
            raise ShenzhenGasApiError(f"Request failed: {err}") from err

        if data.get("code") != 0:
            # 有些后端登录失效不一定返回 HTTP 401，而是 JSON 里提示。
            msg = str(data)
            if retry_auth and (
                "token" in msg.lower()
                or "unauthorized" in msg.lower()
                or "未登录" in msg
                or "登录" in msg
            ):
                self._access_token = None
                self._token_expires_at = None
                return await self._request(
                    method,
                    path,
                    params=params,
                    json=json,
                    retry_auth=False,
                )

            raise ShenzhenGasApiError(f"API error: {data}")

        return data.get("data") or {}

    async def async_get_day_data(self, year_month: str | None = None) -> dict:
        """Get daily gas usage data for the given month."""
        if year_month is None:
            year_month = datetime.now().strftime("%Y%m")

        return await self._request(
            "GET",
            "/api/handle/network/queryDayData",
            params={
                "ccbCustNo": self._ccb_cust_no,
                "mph": self._meter_no,
                "yearMonth": year_month,
            },
        )

    async def async_get_bound_accounts(self) -> list[dict]:
        """Get accounts bound to the current mini-program user."""
        data = await self._request(
            "POST",
            "/api/newcis/frbindingport/receiveBandingAcctIdList",
            json={
                "accountChannelId": self._account_channel_id,
                "pageNum": 1,
                "pageSize": 100,
                "areaId": "",
                "type": "",
            },
        )

        records = data.get("records", [])
        if not isinstance(records, list):
            return []

        return [record for record in records if isinstance(record, dict)]

    async def async_get_valve_status(self) -> dict:
        """Get gas meter valve status."""
        return await self._request(
            "GET",
            "/api/handle/network/valveStatus",
            params={
                "ccbCustNo": self._ccb_cust_no,
                "mph": self._meter_no,
            },
        )

    async def async_get_balance(self) -> dict:
        """Get prepaid gas balance and IoT meter data."""
        return await self._request(
            "POST",
            "/api/handle/gasThings/getInternetOfThings",
            json={
                "ccbCustNo": self._ccb_cust_no,
                "isPrePaid": True,
                "xcxMtrFlg": "2",
            },
        )

    async def async_get_bill_data_info(self) -> dict:
        """Get historical bill data."""
        return await self._request(
            "POST",
            "/api/handle/gasBill/getUserBillDataInfo",
            json={
                "acct": self._ccb_cust_no,
            },
        )

    async def async_get_bill_date(self) -> dict:
        """Get homepage bill amount and gas consumption."""
        return await self._request(
            "GET",
            "/api/newcis/homepage/getBillDate",
            params={
                "accountChannelId": self._account_channel_id,
            },
        )

    async def async_get_all(self) -> dict:
        """Get all Shenzhen Gas data."""
        balance = {}
        try:
            balance = await self.async_get_balance()
        except ShenzhenGasApiError:
            balance = {}

        meter_no = next(_iter_meter_values(balance), None)
        if meter_no and meter_no != self._meter_no:
            self.update_meter_no(meter_no)

        day_data = {}
        try:
            day_data = await self.async_get_day_data()
        except ShenzhenGasApiError:
            day_data = {}

        valve_status = {}
        try:
            valve_status = await self.async_get_valve_status()
        except ShenzhenGasApiError:
            valve_status = {}

        bill_data = {}
        try:
            bill_data = await self.async_get_bill_data_info()
        except ShenzhenGasApiError:
            try:
                bill_data = await self.async_get_bill_date()
            except ShenzhenGasApiError:
                bill_data = {}

        return {
            "day_data": day_data,
            "valve_status": valve_status,
            "balance": balance,
            "bill_data": bill_data,
        }


METER_KEYS = {
    "deviceno",
    "deviceid",
    "gasmeterid",
    "gasmeterno",
    "meterid",
    "meter_id",
    "meterno",
    "meter_no",
    "meternum",
    "meternumber",
    "metersn",
    "mph",
    "mtrno",
    "mtr_no",
    "rawmeterno",
    "rmid",
}


def _iter_meter_values(value) -> Iterable[str]:
    """Yield likely meter numbers from nested API data."""
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in METER_KEYS and item not in (None, ""):
                yield str(item)

            yield from _iter_meter_values(item)

    elif isinstance(value, list):
        for item in value:
            yield from _iter_meter_values(item)
