from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ShenzhenGasOnlineBinarySensor(coordinator, entry)])


class ShenzhenGasOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_online"
        self._attr_name = "深圳燃气 在线状态"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.meter_no)},
            "name": f"深圳燃气 {self.coordinator.api.meter_no}",
            "manufacturer": "深圳燃气",
            "model": "物联网燃气表",
        }

    @property
    def is_on(self):
        valve_status = self.coordinator.valve_status or {}
        return valve_status.get("online") == 1