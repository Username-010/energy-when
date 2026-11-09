"""Sensors for Energy When."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergyWhenCoordinator
from .planner import Plan


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord: EnergyWhenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            BestStartSensor(coord, entry),
            BestCostSensor(coord, entry),
            NowCostSensor(coord, entry),
            SavingsSensor(coord, entry),
            PlanSensor(coord, entry),
        ]
    )


class _Base(CoordinatorEntity[EnergyWhenCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: EnergyWhenCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Energy When",
            "model": "Load planner",
        }

    @property
    def plan(self) -> Plan | None:
        return self.coordinator.data


class BestStartSensor(_Base):
    _attr_translation_key = "best_start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:washing-machine"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "best_start")

    @property
    def native_value(self):
        p = self.plan
        return None if p is None else p.best_start


class BestCostSensor(_Base):
    _attr_translation_key = "best_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR"
    _attr_icon = "mdi:cash-check"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "best_cost")

    @property
    def native_value(self):
        p = self.plan
        return None if p is None else p.best_cost


class NowCostSensor(_Base):
    _attr_translation_key = "now_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR"
    _attr_icon = "mdi:cash-clock"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "now_cost")

    @property
    def native_value(self):
        p = self.plan
        return None if p is None else p.now_cost


class SavingsSensor(_Base):
    _attr_translation_key = "savings"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR"
    _attr_icon = "mdi:piggy-bank"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "savings")

    @property
    def native_value(self):
        p = self.plan
        return None if p is None else p.savings


class PlanSensor(_Base):
    """One sensor the Lovelace card reads — state is a short verdict, hours in attributes."""

    _attr_translation_key = "plan"
    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "plan")

    @property
    def native_value(self):
        p = self.plan
        if p is None or p.best_start is None:
            return "unknown"
        if p.reason == "now":
            return "now"
        return p.best_start.isoformat()

    @property
    def extra_state_attributes(self):
        p = self.plan
        if p is None:
            return {}
        return p.as_attr_dict()
