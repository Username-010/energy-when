# Energy When

Home Assistant integration + Lovelace card that answers one question:

**When should I run the washing machine (or dryer / dishwasher / EV)?**

Not “look at this energy dashboard”. A big verdict, a price curve, solar on the same graph, and the cheapest block highlighted — including **free solar**, overnight if that’s actually cheaper.

![card](https://raw.githubusercontent.com/Username-010/energy-when/main/docs/card.png)

## Why

The built-in Energy dashboard shows kWh. Dynamic tariffs show a price. Neither tells you “wash at 02:00, you’ll save €0.51 versus now” when midday solar can beat a cheap night — or the other way around on a grey day.

Energy When combines:

1. Hourly (or 15-minute) **import prices** (EnergyZero, Nordpool, Tibber, …)
2. **Solar now** + remaining today / tomorrow (Forecast.Solar or your inverter)
3. Your **house load** (P1) so surplus solar is what actually covers the wash

Effective cost per hour:

```
surplus = max(0, solar_W − house_W)
grid_W  = max(0, appliance_W − surplus)
cost    = grid_W / 1000 × all_in_€/kWh
```

Then a sliding window of your cycle length (default 2.5 h).

## Install (HACS)

1. HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/Username-010/energy-when` as **Integration**
3. Download **Energy When**, restart Home Assistant
4. Settings → Devices & services → Add **Energy When**
5. Add the card:

```yaml
type: custom:energy-when-card
entity: sensor.was_plan
```

The card is registered at `/energy_when/energy-when-card.js`. If it doesn’t show up, add that URL as a Lovelace **JavaScript module** resource.

## Sensors

| Entity | Meaning |
| --- | --- |
| `sensor.*_plan` | `now` or the ISO start time; `hours` attribute feeds the card |
| `sensor.*_best_start` | timestamp — use in automations |
| `sensor.*_best_cost` / `now_cost` / `savings` | euros for one cycle |
| `binary_sensor.*_good_time` | on while you’re inside the cheapest window |

## Card

- Hero: **Was nu** or **Was om 02:00** plus the euro cost of that window
- Subline: what it would cost if you started now, and how much you save
- Graph: blue price curve, yellow solar area, green cheapest block, dashed “now”

Dutch UI when Home Assistant language is `nl`.

## License

MIT
