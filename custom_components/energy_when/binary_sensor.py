"""Binary sensor: it's a good moment to run the load."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import EnergyWhenCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord: EnergyWhenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GoodTimeSensor(coord, entry)])


class GoodTimeSensor(CoordinatorEntity[EnergyWhenCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "good_time"
    _attr_icon = "mdi:clock-check"

    def __init__(self, coordinator: EnergyWhenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_good_time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Energy When",
        }

    @property
    def is_on(self) -> bool:
        p = self.coordinator.data
        if p is None or p.best_start is None:
            return False
        now = dt_util.now()
        if p.best_end is None:
            return False
        return p.best_start <= now < p.best_end
