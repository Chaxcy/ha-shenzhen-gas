from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.const import UnitOfVolume, PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)


@dataclass(frozen=True, kw_only=True)
class ShenzhenGasSensorDescription(SensorEntityDescription):
    value_fn: Callable


def _latest_day(coordinator):
    return coordinator.latest_day or {}


def _yesterday_day(coordinator):
    datas = (
        coordinator.data
        .get("day_data", {})
        .get("datas", [])
        if coordinator.data
        else []
    )

    if len(datas) < 2:
        return {}

    return datas[-2]


def _internet_things(coordinator):
    return coordinator.internet_things or {}


def _valve_status(coordinator):
    return coordinator.valve_status or {}


def _bill_data(coordinator):
    return coordinator.bill_data or {}


def _last_bill(coordinator):
    bill_list = _bill_data(coordinator).get("billList", [])

    if not bill_list:
        return {}

    return bill_list[0]


def _last_bill_params(coordinator):
    data_params = _last_bill(coordinator).get("dataParams", {})

    if isinstance(data_params, dict):
        return data_params

    return {}


def _last_bill_charge_detail(coordinator):
    mx_list = _last_bill_params(coordinator).get("mxList")

    if isinstance(mx_list, dict):
        return mx_list.get("billDescr")

    if isinstance(mx_list, list):
        for item in mx_list:
            if isinstance(item, dict) and item.get("billDescr"):
                return item.get("billDescr")

    return None


def _iter_dicts(value):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _iter_dicts(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_dicts(item)


def _first_value(coordinator, keys):
    """Return the first non-empty value matching any key in coordinator data."""
    if not coordinator.data:
        return None

    data_sources = [
        coordinator.data.get("bill_data", {}),
        coordinator.data.get("balance", {}),
        coordinator.internet_things,
    ]

    normalized_keys = {key.lower() for key in keys}

    for source in data_sources:
        for item in _iter_dicts(source):
            for key, value in item.items():
                if str(key).lower() in normalized_keys and value not in (None, ""):
                    return value

    return None


def _last_bill_amount(coordinator):
    return (
        _last_bill(coordinator).get("calcAmt")
        or _last_bill_params(coordinator).get("calcAmt")
        or _last_bill_params(coordinator).get("remainAmt")
        or _bill_data(coordinator).get("arreasAmt")
        or _first_value(
            coordinator,
            (
                "lastBillAmount",
                "lastBillAmt",
                "lastMonthAmount",
                "lastMonthBillAmount",
                "lastPeriodAmount",
                "lastPeriodBillAmount",
                "lastCycleAmount",
                "lastCycleBillAmount",
                "lastFee",
                "lastBillFee",
                "lastPayAmount",
                "lastGasFee",
                "lastAmount",
                "previousBillAmount",
                "previousFee",
                "previousAmount",
                "preBillAmount",
                "preBillFee",
                "preGasFee",
                "preAmount",
                "billAmount",
                "arreasAmt",
                "应缴金额",
                "账单金额",
                "上期账单金额",
            ),
        )
    )


def _last_bill_usage(coordinator):
    return (
        _last_bill(coordinator).get("msrQty")
        or _last_bill_params(coordinator).get("bqyql")
        or _bill_data(coordinator).get("gasConsumption")
        or _first_value(
            coordinator,
            (
                "lastBillUsage",
                "lastBillGas",
                "lastMonthGas",
                "lastMonthUsage",
                "lastMonthUseGas",
                "lastPeriodGas",
                "lastPeriodUsage",
                "lastPeriodUseGas",
                "lastCycleGas",
                "lastCycleUsage",
                "lastCycleUseGas",
                "lastGasQuantity",
                "lastDosage",
                "lastGas",
                "lastUsage",
                "lastUseGas",
                "previousBillUsage",
                "previousGas",
                "previousGasQuantity",
                "previousDosage",
                "previousUsage",
                "previousUseGas",
                "preBillUsage",
                "preGas",
                "preGasQuantity",
                "preDosage",
                "preUsage",
                "preUseGas",
                "gasConsumption",
                "gasUsage",
                "useGas",
                "用气量",
                "上期用气量",
            ),
        )
    )


def _last_bill_period(coordinator):
    return (
        _last_bill(coordinator).get("bsegPeriod")
        or _last_bill_params(coordinator).get("bsegPeriod")
    )


def _next_bill_date(coordinator):
    return (
        _last_bill(coordinator).get("wyjDt")
        or _last_bill_params(coordinator).get("wyjDt")
        or _bill_data(coordinator).get("dayEndDate")
    )


SENSORS = [
    ShenzhenGasSensorDescription(
        key="meter_reading",
        name="累计读数",
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=lambda c: _latest_day(c).get("readingData"),
    ),
    ShenzhenGasSensorDescription(
        key="daily_usage",
        name="今日用气量",
        icon="mdi:gas-burner",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=lambda c: _latest_day(c).get("readingSum"),
    ),
    ShenzhenGasSensorDescription(
        key="yesterday_usage",
        name="昨日用气量",
        icon="mdi:gas-burner",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=lambda c: _yesterday_day(c).get("readingSum"),
    ),
    ShenzhenGasSensorDescription(
        key="latest_reading_date",
        name="用气日期",
        icon="mdi:calendar-today",
        value_fn=lambda c: _latest_day(c).get("readingDate"),
    ),
    ShenzhenGasSensorDescription(
        key="balance",
        name="余额",
        icon="mdi:cash",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="CNY",
        value_fn=lambda c: _internet_things(c).get("residualAmount"),
    ),
    ShenzhenGasSensorDescription(
        key="last_bill_amount",
        name="上期账单金额",
        icon="mdi:cash",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="CNY",
        value_fn=_last_bill_amount,
    ),
    ShenzhenGasSensorDescription(
        key="last_bill_usage",
        name="上期用气量",
        icon="mdi:gas-burner",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=_last_bill_usage,
    ),
    ShenzhenGasSensorDescription(
        key="last_bill_charge_detail",
        name="第一阶梯气费",
        icon="mdi:cash",
        value_fn=_last_bill_charge_detail,
    ),
    ShenzhenGasSensorDescription(
        key="last_bill_period",
        name="上期账单周期",
        icon="mdi:receipt-text-check",
        value_fn=_last_bill_period,
    ),
    ShenzhenGasSensorDescription(
        key="next_bill_date",
        name="下一账单日",
        icon="mdi:receipt-text-clock",
        value_fn=_next_bill_date,
    ),
    ShenzhenGasSensorDescription(
        key="raw_reading",
        name="最新读数",
        icon="mdi:meter-gas",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=lambda c: _internet_things(c).get("rawReading"),
    ),
    ShenzhenGasSensorDescription(
        key="receive_time",
        name="最近更新",
        icon="mdi:calendar-today",
        value_fn=lambda c: _internet_things(c).get("receiveTime"),
    ),
    ShenzhenGasSensorDescription(
        key="valve_status",
        name="阀门状态",
        value_fn=lambda c: _valve_status(c).get("valveStatus"),
    ),
    ShenzhenGasSensorDescription(
        key="battery",
        name="电池电量",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda c: _valve_status(c).get("batteryVoltage"),
    ),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ShenzhenGasSensor(coordinator, entry, description)
        for description in SENSORS
    )


class ShenzhenGasSensor(CoordinatorEntity, SensorEntity):
    entity_description: ShenzhenGasSensorDescription

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = f"深圳燃气 {description.name}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.meter_no)},
            "name": f"深圳燃气 {self.coordinator.api.meter_no}",
            "manufacturer": "深圳燃气",
            "model": "物联网燃气表",
        }

    @property
    def native_value(self):
        value = self.entity_description.value_fn(self.coordinator)

        if value == "":
            return None

        return value

    @property
    def extra_state_attributes(self):
        if self.entity_description.key != "daily_usage":
            return None

        day_data = self.coordinator.data.get("day_data", {}) if self.coordinator.data else {}
        return {
            "month_data": day_data.get("datas", []),
            "meter_no": day_data.get("rmid"),
        }
