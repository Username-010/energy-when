const CARD = "energy-when-card";

function euro(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("nl-NL", { style: "currency", currency: "EUR" });
}

function hhmm(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function isNl(hass) {
  const lang = (hass && hass.locale && hass.locale.language) || (hass && hass.language) || "";
  return String(lang).toLowerCase().startsWith("nl");
}

class EnergyWhenCard extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (!config || !config.entity) throw new Error("Set entity to the Energy When plan sensor");
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return { entity: "" };
  }

  static getConfigElement() {
    return document.createElement("energy-when-card-editor");
  }

  _render() {
    const hass = this._hass;
    const cfg = this._config || {};
    if (!hass || !cfg.entity) {
      this.shadowRoot.innerHTML = `<ha-card><div class="pad">Pick a plan sensor</div></ha-card>`;
      return;
    }
    const st = hass.states[cfg.entity];
    if (!st) {
      this.shadowRoot.innerHTML = `<ha-card><div class="pad">Missing ${cfg.entity}</div></ha-card>`;
      return;
    }
    const a = st.attributes || {};
    const hours = Array.isArray(a.hours) ? a.hours : [];
    const nl = isNl(hass);
    const t = nl
      ? {
          nowWash: "Was nu",
          washAt: "Was om",
          nowCosts: "Nu wassen kost",
          save: "je bespaart",
          vsNow: "ten opzichte van nu",
          solar: "zon",
          price: "prijs",
          best: "goedkoopste blok",
          grid: "van het net",
          free: "gratis zon",
          empty: "Nog geen prijzen. Wacht tot EnergyZero binnen is.",
        }
      : {
          nowWash: "Wash now",
          washAt: "Wash at",
          nowCosts: "Washing now costs",
          save: "you save",
          vsNow: "versus now",
          solar: "solar",
          price: "price",
          best: "cheapest block",
          grid: "from grid",
          free: "free solar",
          empty: "No prices yet.",
        };

    const bestStart = a.best_start;
    const isNow = st.state === "now" || a.reason === "now";
    const title = isNow ? t.nowWash : bestStart ? `${t.washAt} ${hhmm(bestStart)}` : t.empty;
    const savings = Number(a.savings || 0);
    const nowCost = a.now_cost;
    const bestCost = a.best_cost;
    const sub = hours.length
      ? `${t.nowCosts} ${euro(nowCost)} · ${t.save} ${euro(savings)} ${t.vsNow}`
      : t.empty;

    const svg = this._chart(hours, a, nl);

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 0; overflow: hidden; }
        .hero {
          padding: 16px 16px 8px;
          display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
        }
        .verdict {
          font-size: 1.55rem; font-weight: 700; line-height: 1.15;
          letter-spacing: -0.02em;
        }
        .verdict.now { color: var(--success-color, #3d9a50); }
        .verdict.wait { color: var(--primary-color, #03a9f4); }
        .cost {
          font-size: 1.35rem; font-weight: 700; white-space: nowrap;
        }
        .sub { padding: 0 16px 8px; color: var(--secondary-text-color); font-size: 0.92rem; }
        .chart { padding: 0 8px 4px; }
        .legend {
          display: flex; gap: 14px; padding: 0 16px 14px;
          color: var(--secondary-text-color); font-size: 0.78rem; flex-wrap: wrap;
        }
        .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
        .pad { padding: 16px; }
      </style>
      <ha-card header="">
        <div class="hero">
          <div class="verdict ${isNow ? "now" : "wait"}">${title}</div>
          <div class="cost">${euro(bestCost)}</div>
        </div>
        <div class="sub">${sub}</div>
        <div class="chart">${svg}</div>
        <div class="legend">
          <span><span class="swatch" style="background:#5b8def"></span>${t.price}</span>
          <span><span class="swatch" style="background:#f5c542"></span>${t.solar}</span>
          <span><span class="swatch" style="background:rgba(61,154,80,.35)"></span>${t.best}</span>
        </div>
      </ha-card>
    `;
  }

  _chart(hours, a) {
    if (!hours.length) return "";
    const w = 640, h = 180, padL = 36, padR = 12, padT = 16, padB = 28;
    const innerW = w - padL - padR, innerH = h - padT - padB;
    const prices = hours.map((x) => Number(x.price) || 0);
    const solars = hours.map((x) => Number(x.solar_w) || 0);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices, minP + 0.01);
    const maxS = Math.max(...solars, 1);
    const n = hours.length;
    const xAt = (i) => padL + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
    const yPrice = (p) => padT + (1 - (p - minP) / (maxP - minP)) * innerH;
    const ySolar = (s) => padT + (1 - s / maxS) * innerH;

    const priceLine = hours
      .map((x, i) => `${i === 0 ? "M" : "L"} ${xAt(i).toFixed(1)} ${yPrice(x.price).toFixed(1)}`)
      .join(" ");

    const solarArea = [
      `M ${xAt(0).toFixed(1)} ${ySolar(0).toFixed(1)}`,
      ...hours.map((x, i) => `L ${xAt(i).toFixed(1)} ${ySolar(x.solar_w).toFixed(1)}`),
      `L ${xAt(n - 1).toFixed(1)} ${ySolar(0).toFixed(1)} Z`,
    ].join(" ");

    let band = "";
    if (a.best_start) {
      const bs = new Date(a.best_start).getTime();
      const be = a.best_end ? new Date(a.best_end).getTime() : bs + (a.duration_h || 2) * 3600000;
      const i0 = hours.findIndex((x) => new Date(x.start).getTime() >= bs - 60000);
      let i1 = hours.findIndex((x) => new Date(x.start).getTime() >= be - 60000);
      if (i0 >= 0) {
        if (i1 < 0) i1 = Math.min(n - 1, i0 + 1);
        const x0 = xAt(Math.max(0, i0));
        const x1 = xAt(Math.max(i0, i1));
        band = `<rect x="${x0}" y="${padT}" width="${Math.max(8, x1 - x0)}" height="${innerH}" fill="rgba(61,154,80,0.22)" rx="3"/>`;
      }
    }

    const now = Date.now();
    let nowX = null;
    for (let i = 0; i < n; i++) {
      const t0 = new Date(hours[i].start).getTime();
      const t1 = t0 + 3600000;
      if (now >= t0 && now < t1) {
        nowX = xAt(i) + (n > 1 ? ((now - t0) / 3600000) * (xAt(Math.min(n - 1, i + 1)) - xAt(i)) : 0);
        break;
      }
    }

    const ticks = [];
    const step = n > 30 ? 6 : n > 16 ? 4 : 3;
    for (let i = 0; i < n; i += step) {
      ticks.push(
        `<text x="${xAt(i)}" y="${h - 8}" text-anchor="middle" fill="var(--secondary-text-color)" font-size="11">${hhmm(hours[i].start)}</text>`
      );
    }

    const nowLine = nowX
      ? `<line x1="${nowX}" x2="${nowX}" y1="${padT}" y2="${padT + innerH}" stroke="var(--primary-text-color)" stroke-dasharray="3 3" opacity="0.55"/>`
      : "";

    return `
      <svg viewBox="0 0 ${w} ${h}" width="100%" height="180" role="img">
        ${band}
        <path d="${solarArea}" fill="rgba(245,197,66,0.35)" stroke="none"/>
        <path d="${priceLine}" fill="none" stroke="#5b8def" stroke-width="2.4" stroke-linejoin="round"/>
        ${nowLine}
        ${ticks.join("")}
      </svg>
    `;
  }
}

class EnergyWhenCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    this._render();
  }
  _render() {
    if (!this._hass) return;
    const cfg = this._config || {};
    this.innerHTML = `
      <div style="padding:8px 0">
        <ha-entity-picker></ha-entity-picker>
      </div>
    `;
    const picker = this.querySelector("ha-entity-picker");
    if (picker) {
      picker.hass = this._hass;
      picker.value = cfg.entity || "";
      picker.includeDomains = ["sensor"];
      picker.addEventListener("value-changed", (ev) => {
        this._config = { ...cfg, entity: ev.detail.value };
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config } }));
      });
    }
  }
}

customElements.define(CARD, EnergyWhenCard);
customElements.define("energy-when-card-editor", EnergyWhenCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD,
  name: "Energy When",
  description: "When to wash: price curve + solar, cheapest block highlighted.",
});
