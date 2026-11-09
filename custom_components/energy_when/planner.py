"""Pure planning math — no Home Assistant imports (unit-testable)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from math import cos, pi
from typing import Any


@dataclass
class HourSlot:
    start: datetime
    price: float  # EUR/kWh all-in
    solar_w: float
    surplus_w: float
    grid_w: float
    cost: float  # EUR to run the appliance during this one hour
    effective: float  # EUR/kWh after solar


@dataclass
class Plan:
    best_start: datetime | None
    best_end: datetime | None
    best_cost: float | None
    now_cost: float | None
    savings: float | None
    currency: str
    duration_h: float
    appliance_w: float
    hours: list[HourSlot]
    reason: str

    def as_attr_dict(self) -> dict[str, Any]:
        hours = []
        for h in self.hours:
            hours.append(
                {
                    "start": h.start.isoformat(),
                    "price": round(h.price, 5),
                    "solar_w": round(h.solar_w, 1),
                    "surplus_w": round(h.surplus_w, 1),
                    "grid_w": round(h.grid_w, 1),
                    "cost": round(h.cost, 4),
                    "effective": round(h.effective, 5),
                }
            )
        return {
            "best_start": self.best_start.isoformat() if self.best_start else None,
            "best_end": self.best_end.isoformat() if self.best_end else None,
            "best_cost": None if self.best_cost is None else round(self.best_cost, 4),
            "now_cost": None if self.now_cost is None else round(self.now_cost, 4),
            "savings": None if self.savings is None else round(self.savings, 4),
            "currency": self.currency,
            "duration_h": self.duration_h,
            "appliance_w": self.appliance_w,
            "reason": self.reason,
            "hours": hours,
        }


def parse_price_points(raw: Any, surcharge: float = 0.0) -> list[tuple[datetime, float]]:
    """Accept EnergyZero Prices, Nordpool-style lists, or {iso: price} maps."""
    out: list[tuple[datetime, float]] = []
    if raw is None:
        return out
    if isinstance(raw, dict):
        for key, val in raw.items():
            ts = _as_dt(key)
            price = _as_float(val)
            if ts is not None and price is not None:
                out.append((ts, price + surcharge))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                ts = _as_dt(
                    item.get("readingDate")
                    or item.get("start")
                    or item.get("time")
                    or item.get("hour")
                    or item.get("datetime")
                )
                price = _as_float(
                    item.get("price")
                    if item.get("price") is not None
                    else item.get("value")
                    if item.get("value") is not None
                    else item.get("price_per_kwh")
                )
                if ts is not None and price is not None:
                    out.append((ts, price + surcharge))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                ts = _as_dt(item[0])
                price = _as_float(item[1])
                if ts is not None and price is not None:
                    out.append((ts, price + surcharge))
    out.sort(key=lambda x: x[0])
    return out


def estimate_solar_curve(
    hours: list[datetime],
    *,
    now: datetime,
    solar_now_w: float,
    remaining_today_kwh: float | None,
    tomorrow_kwh: float | None,
    sunrise: datetime | None,
    sunset: datetime | None,
    sunrise_tomorrow: datetime | None = None,
    sunset_tomorrow: datetime | None = None,
) -> dict[datetime, float]:
    """Hourly solar watts. Prefers a cosine bell scaled to remaining kWh."""
    result: dict[datetime, float] = {h: 0.0 for h in hours}
    if not hours:
        return result

    def fill(start: datetime, end: datetime, total_kwh: float) -> None:
        if total_kwh <= 0 or end <= start:
            return
        span = (end - start).total_seconds()
        if span <= 0:
            return
        weights: list[tuple[datetime, float]] = []
        for h in hours:
            mid = h + timedelta(minutes=30)
            if mid < start or mid > end:
                continue
            t = (mid - start).total_seconds() / span
            # half-cosine bell, peak at solar noon
            w = max(0.0, cos((t - 0.5) * pi)) ** 1.4
            weights.append((h, w))
        s = sum(w for _, w in weights) or 1.0
        for h, w in weights:
            # total_kwh spread across those hours → average watts
            result[h] = result.get(h, 0.0) + (total_kwh * 1000.0) * (w / s)

    today = now.date()
    sr = sunrise or now.replace(hour=8, minute=0, second=0, microsecond=0)
    ss = sunset or now.replace(hour=17, minute=0, second=0, microsecond=0)
    if remaining_today_kwh is not None:
        fill(max(now, sr), ss, remaining_today_kwh)
    if tomorrow_kwh is not None:
        tmr = today + timedelta(days=1)
        sr2 = sunrise_tomorrow or sr + timedelta(days=1)
        ss2 = sunset_tomorrow or ss + timedelta(days=1)
        if sr2.date() != tmr:
            sr2 = sr2.replace(year=tmr.year, month=tmr.month, day=tmr.day)
        if ss2.date() != tmr:
            ss2 = ss2.replace(year=tmr.year, month=tmr.month, day=tmr.day)
        fill(sr2, ss2, tomorrow_kwh)

    # pin current hour to live inverter/forecast reading
    if solar_now_w > 0:
        current = min(hours, key=lambda h: abs((h - now).total_seconds()))
        if abs((current - now).total_seconds()) < 3600:
            result[current] = solar_now_w
    return result


def build_plan(
    prices: list[tuple[datetime, float]],
    solar: dict[datetime, float],
    *,
    now: datetime,
    duration_h: float = 2.5,
    appliance_w: float = 600.0,
    base_load_w: float = 800.0,
    currency: str = "EUR",
) -> Plan:
    if not prices:
        return Plan(None, None, None, None, None, currency, duration_h, appliance_w, [], "no prices")

    slots: list[HourSlot] = []
    for start, price in prices:
        if start + timedelta(hours=1) <= now:
            continue  # skip fully past hours
        solar_w = float(solar.get(start, 0.0) or 0.0)
        surplus = max(0.0, solar_w - max(0.0, base_load_w))
        grid_w = max(0.0, appliance_w - surplus)
        kwh = grid_w / 1000.0
        cost = kwh * max(price, 0.0)
        effective = cost if appliance_w <= 0 else (cost / (appliance_w / 1000.0))
        slots.append(
            HourSlot(start, price, solar_w, surplus, grid_w, cost, effective)
        )

    if not slots:
        return Plan(None, None, None, None, None, currency, duration_h, appliance_w, [], "no future hours")

    # sliding window of duration_h hours (partial last hour)
    n_full = int(duration_h)
    frac = duration_h - n_full
    window_len = n_full + (1 if frac > 1e-6 else 0)
    if window_len < 1:
        window_len = 1
        frac = 0.0

    def window_cost(i: int) -> float | None:
        if i + window_len > len(slots) and not (window_len == 1):
            if i >= len(slots):
                return None
        total = 0.0
        hours_used = 0.0
        for j in range(window_len):
            if i + j >= len(slots):
                return None
            part = 1.0 if j < n_full else (frac if frac > 0 else 1.0)
            total += slots[i + j].cost * part
            hours_used += part
        if hours_used < duration_h - 1e-6:
            return None
        return total

    best_i = 0
    best_c: float | None = None
    for i in range(len(slots)):
        c = window_cost(i)
        if c is None:
            continue
        if best_c is None or c < best_c - 1e-9:
            best_c = c
            best_i = i

    now_i = 0
    now_c = window_cost(0)
    best_start = slots[best_i].start if best_c is not None else None
    best_end = (
        best_start + timedelta(hours=duration_h) if best_start is not None else None
    )
    savings = None
    if now_c is not None and best_c is not None:
        savings = max(0.0, now_c - best_c)

    reason = "now" if best_i == 0 else "wait"
    if best_c is not None and best_c <= 0.005:
        reason = "solar" if any(slots[best_i + j].solar_w > base_load_w for j in range(min(window_len, len(slots) - best_i))) else "free"
    return Plan(
        best_start=best_start,
        best_end=best_end,
        best_cost=best_c,
        now_cost=now_c,
        savings=savings,
        currency=currency,
        duration_h=duration_h,
        appliance_w=appliance_w,
        hours=slots,
        reason=reason,
    )


def _as_float(val: Any) -> float | None:
    try:
        if val is None or val in ("", "unknown", "unavailable", "None"):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _as_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
    elif isinstance(val, (int, float)):
        ts = float(val)
        if ts > 10_000_000_000:
            ts /= 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def slot_to_dict(h: HourSlot) -> dict[str, Any]:
    return asdict(h)
