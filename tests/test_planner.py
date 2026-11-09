import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "energy_when"))
from planner import build_plan, estimate_solar_curve, parse_price_points


TZ = timezone.utc
NOW = datetime(2026, 11, 9, 14, 30, tzinfo=TZ)


def hours(n=24, start=None, base=0.40, bump_at=None, bump=0.10):
    start = start or datetime(2026, 11, 9, 14, tzinfo=TZ)
    out = []
    for i in range(n):
        p = base
        if bump_at is not None and i == bump_at:
            p = bump
        out.append((start + timedelta(hours=i), p))
    return out


def test_parse_energyzero_prices():
    raw = [
        {"readingDate": "2026-11-09T02:00:00Z", "price": 0.27},
        {"readingDate": "2026-11-09T03:00:00Z", "price": 0.28},
    ]
    pts = parse_price_points(raw, surcharge=0.11)
    assert len(pts) == 2
    assert abs(pts[0][1] - 0.38) < 1e-9


def test_night_beats_day_without_solar():
    prices = hours(10, base=0.50)
    prices[7] = (prices[7][0], 0.20)
    prices[8] = (prices[8][0], 0.20)
    plan = build_plan(prices, {}, now=NOW, duration_h=2, appliance_w=1000, base_load_w=800)
    assert plan.best_start == prices[7][0]
    assert plan.now_cost is not None
    assert plan.best_cost is not None
    assert plan.best_cost < plan.now_cost


def test_solar_can_beat_cheap_night():
    start = datetime(2026, 11, 9, 14, tzinfo=TZ)
    prices = [(start + timedelta(hours=i), 0.50) for i in range(12)]
    # cheap night at +10h
    prices[10] = (prices[10][0], 0.15)
    solar = {start: 4000.0, start + timedelta(hours=1): 3500.0}  # now is sunny
    plan = build_plan(
        prices, solar, now=NOW, duration_h=2, appliance_w=600, base_load_w=800
    )
    # surplus 3200W > appliance 600W → now is free, cheaper than 0.15 night
    assert plan.best_start == start
    assert plan.best_cost is not None
    assert plan.best_cost < 0.01


def test_solar_curve_pins_now():
    hs = [NOW.replace(minute=0, second=0, microsecond=0) + timedelta(hours=i) for i in range(6)]
    curve = estimate_solar_curve(
        hs,
        now=NOW,
        solar_now_w=2632,
        remaining_today_kwh=4.0,
        tomorrow_kwh=6.0,
        sunrise=NOW.replace(hour=8, minute=0),
        sunset=NOW.replace(hour=17, minute=0),
    )
    current = hs[0]
    assert curve[current] == 2632
