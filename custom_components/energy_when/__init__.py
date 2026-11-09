"""Energy When — cheapest time to run a wash/dryer/EV, with solar on the same graph."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import EnergyWhenCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
CARD_URL = "/energy_when/energy-when-card.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await _register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coord = EnergyWhenCoordinator(hass, entry)
    await coord.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await _register_card(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _register_card(hass: HomeAssistant) -> None:
    www = Path(__file__).parent / "www"
    js = www / "energy-when-card.js"
    if not js.is_file():
        return
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig("/energy_when", str(www), False)]
        )
    except Exception:  # noqa: BLE001 — already registered after reload
        _LOGGER.debug("static path already registered")
    try:
        resources = hass.data.get("lovelace")
        if resources is None:
            return
        store = getattr(resources, "resources", None) or resources
        existing = []
        if hasattr(store, "async_items"):
            existing = list(store.async_items())
        elif isinstance(store, dict):
            existing = list(store.values()) if store else []
        urls = {str(i.get("url")) for i in existing if isinstance(i, dict)}
        if CARD_URL not in urls and hasattr(store, "async_create_item"):
            await store.async_create_item({"res_type": "module", "url": CARD_URL})
    except Exception:  # noqa: BLE001
        _LOGGER.debug("could not auto-add Lovelace resource")
