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
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=lambda c: _latest_day(c).get("readingSum"),
    ),
    ShenzhenGasSensorDescription(
        key="yesterday_usage",
        name="昨日用气量",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=lambda c: _yesterday_day(c).get("readingSum"),
    ),
    ShenzhenGasSensorDescription(
        key="latest_reading_date",
        name="用气日期",
        value_fn=lambda c: _latest_day(c).get("readingDate"),
    ),
    ShenzhenGasSensorDescription(
        key="balance",
        name="余额",
        native_unit_of_measurement="CNY",
        value_fn=lambda c: _internet_things(c).get("residualAmount"),
    ),
    ShenzhenGasSensorDescription(
        key="raw_reading",
        name="最新读数",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=lambda c: _internet_things(c).get("rawReading"),
    ),
    ShenzhenGasSensorDescription(
        key="receive_time",
        name="最近更新",
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