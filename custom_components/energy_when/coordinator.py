"""Refresh the cheapest-window plan from price + solar entities."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALL_IN_SENSOR,
    CONF_APPLIANCE_W,
    CONF_BASE_LOAD_W,
    CONF_DURATION,
    CONF_HOUSE_POWER,
    CONF_PRICE_SENSOR,
    CONF_SOLAR_NOW,
    CONF_SOLAR_REMAINING,
    CONF_SOLAR_TOMORROW,
    CONF_SURCHARGE,
    DEFAULT_APPLIANCE_W,
    DEFAULT_BASE_LOAD_W,
    DEFAULT_DURATION,
    DEFAULT_SURCHARGE,
    DOMAIN,
)
from .planner import Plan, build_plan, estimate_solar_curve, parse_price_points


def _num(hass: HomeAssistant, eid: str | None, default: float = 0.0) -> float:
    if not eid:
        return default
    st = hass.states.get(eid)
    if st is None or st.state in ("unknown", "unavailable", "", "None"):
        return default
    try:
        return float(st.state)
    except (TypeError, ValueError):
        return default


def _sun_point(hass: HomeAssistant, attr: str) -> datetime | None:
    sun = hass.states.get("sun.sun")
    if sun is None:
        return None
    raw = (sun.attributes or {}).get(attr)
    if not raw:
        return None
    try:
        return dt_util.parse_datetime(str(raw))
    except (TypeError, ValueError):
        return None


class EnergyWhenCoordinator(DataUpdateCoordinator[Plan]):
    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id[:8]}",
            update_interval=timedelta(minutes=1),
        )
        self.entry = entry

    @property
    def cfg(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    async def _async_update_data(self) -> Plan:
        return self._compute()

    def _compute(self) -> Plan:
        cfg = self.cfg
        price_eid = cfg.get(CONF_PRICE_SENSOR)
        st = self.hass.states.get(price_eid) if price_eid else None
        attrs = dict(st.attributes) if st else {}
        raw = (
            attrs.get("Prices")
            or attrs.get("prices")
            or attrs.get("today")
            or attrs.get("raw_today")
        )
        surcharge = float(cfg.get(CONF_SURCHARGE, DEFAULT_SURCHARGE) or 0)
        all_in_eid = cfg.get(CONF_ALL_IN_SENSOR)
        if all_in_eid and st is not None:
            try:
                market = float(st.state)
                all_in = _num(self.hass, all_in_eid, market)
                if market and abs(all_in - market) < 1.0:
                    surcharge = all_in - market
            except (TypeError, ValueError):
                pass
        prices = parse_price_points(raw, surcharge=surcharge)
        now = dt_util.now()
        hour_starts = [p[0] for p in prices]
        solar_now = _num(self.hass, cfg.get(CONF_SOLAR_NOW), 0.0)
        # If house power is a P1 net meter (negative = export), current house load
        # is solar + p1. Use it as base load for the current hour only via default.
        house = cfg.get(CONF_HOUSE_POWER)
        p1 = _num(self.hass, house, 0.0) if house else 0.0
        base = float(cfg.get(CONF_BASE_LOAD_W, DEFAULT_BASE_LOAD_W) or DEFAULT_BASE_LOAD_W)
        if house and solar_now:
            # P1 negative = export. house_load = solar + p1
            live_house = solar_now + p1
            if 50 < live_house < 20000:
                base = live_house

        remaining = _num(self.hass, cfg.get(CONF_SOLAR_REMAINING), 0.0)
        tomorrow = _num(self.hass, cfg.get(CONF_SOLAR_TOMORROW), 0.0)
        solar = estimate_solar_curve(
            hour_starts,
            now=now,
            solar_now_w=solar_now,
            remaining_today_kwh=remaining or None,
            tomorrow_kwh=tomorrow or None,
            sunrise=_sun_point(self.hass, "next_rising")
            if now.hour > 16
            else _sun_point(self.hass, "next_rising"),
            sunset=_sun_point(self.hass, "next_setting"),
        )
        duration = float(cfg.get(CONF_DURATION, DEFAULT_DURATION) or DEFAULT_DURATION)
        watts = float(cfg.get(CONF_APPLIANCE_W, DEFAULT_APPLIANCE_W) or DEFAULT_APPLIANCE_W)
        return build_plan(
            prices,
            solar,
            now=now,
            duration_h=duration,
            appliance_w=watts,
            base_load_w=base,
        )
