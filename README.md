# ERCOT Portfolio Investment Simulator

A multi-criteria decision support tool for evaluating power generation portfolio options in the ERCOT market. Built for planning teams who need to compare asset configurations across financial, operational, environmental, and regulatory dimensions simultaneously.

---

## Purpose

This tool answers one question: **"Given our assumptions about the future, which portfolio configuration best balances our competing objectives?"**

It is NOT a market forecast tool or a dispatch simulator. It is a **parametric scenario modeler** — you define assumptions (energy prices, gas costs, carbon policy, load growth) and it shows the consequences of those assumptions across different portfolio configurations and contract structures.

### Who it's for:
- Generation planning teams evaluating new build options
- Executives comparing portfolio strategies (risk vs return)
- Analysts stress-testing PPA structuring decisions
- Anyone who needs to turn "I think storage is better" into a quantified multi-dimensional comparison

---

## How It Works

### Inputs (you control these):

- **Portfolio composition**: Pick assets from templates (BESS, CC, peaker, solar, wind, flex/DR), set MW capacities
- **PPA structure per asset**: Merchant, physical PPA, VPPA, tolling, or hybrid — with price, tenor, escalation, buyer type
- **Market assumptions**: Base energy price, gas price, escalation rates, volatility, peak/off-peak ratio
- **Policy assumptions**: Carbon price, discount rate, projection years
- **Load growth**: Organic growth + data center announcements with conversion rate

### Outputs (the tool computes these):

- NPV, IRR, payback period, Monte Carlo risk distribution
- 9-dimension portfolio score (radar chart)
- PPA vs merchant revenue comparison
- Frequency response simulation (nadir, RoCoF)
- Emissions exposure, thermal derating, gas supply risk
- Scenario comparison across 6 pre-built futures

### Key principle:

Every input instantly updates all outputs. The tool forces you to see trade-offs: optimizing for one dimension (e.g., lowest cost) may score poorly on another (e.g., emissions, speed to deploy, revenue certainty). This is by design.

---

## The 10 Tabs

| Tab | What it does |
|-----|--------------|
| 1. Portfolio | Build portfolios from templates, adjust MW, set revenue mode, save/compare |
| 2. PPA & Offtake | Compare merchant vs contracted, MTM valuation, optimize PPA mix |
| 3. Executive Summary | KPIs at a glance, CAPEX pie chart, radar score, cumulative cashflow |
| 4. Financial Model | Revenue waterfall, tornado sensitivity, Monte Carlo, cashflow table |
| 5. Market Prices | Price duration curve, hourly profile, spike analysis, BESS arbitrage |
| 6. Load vs Capacity | Demand projection with data center growth, reserve margin |
| 7. Frequency | Inertia calculation, frequency event simulation, AS revenue breakdown |
| 8. Transmission | Congestion costs, interconnection estimates, VPPA basis risk |
| 9. Engineering Risks | Thermal derating, gas supply, emissions, supply chain, degradation |
| 10. Scenarios | Compare portfolios across 6 market futures with scoring |

---

## Portfolio Scoring (9 Dimensions)

Each portfolio is scored 0-10 on 9 dimensions. The methodology is transparent and displayed in the app:

| Dimension | What it measures | Formula |
|-----------|-----------------|---------|
| Financial Return | NPV performance | CLIP(NPV_$M / 200 + 5, 0, 10) |
| Speed to Deploy | MW-weighted time to COD | CLIP(10 - avg_months / 6, 0, 10) |
| Reliability | Firm capacity share | firm_MW / total_MW x 10 |
| Frequency Support | Fast-response share | MIN(10, fast_MW / total x 12) |
| Emissions | Annual CO2 output | Tiered: 0 tons = 10, >10M = 0 |
| Fuel Risk | Gas dependence | 10 - gas_gen_share x 10 |
| Customer Fit | Meets customer needs | (firm + freq) / total x 6 + bonuses |
| Regulatory | SB6 and policy alignment | Base 5, +3 storage, +2 firm >1GW, penalties |
| Revenue Certainty | Contracted revenue share | contracted_% / 10, -1 concentration |

**Overall Score** = average of all 9 dimensions.

---

## Market Price Data (Tab 5)

### Data source options:

The app supports three data modes:
1. **CSV export** from Snowflake (real ERCOT data from Grid Status marketplace listing)
2. **gridstatus.io API** (requires API key)
3. **Synthetic fallback** (auto-generated, calibrated to ERCOT characteristics)

### About the synthetic data:

When real data is unavailable, the app generates statistically calibrated synthetic prices:

```
price[hour] = base + diurnal + seasonal + noise + spikes
```

| Component | Value | Calibration basis |
|-----------|-------|-------------------|
| Base price | $35/MWh (varies by zone) | ERCOT 2023-2025 average RT price ($30-45/MWh) |
| Diurnal swing | +/-$15 (sine, 24hr period) | Real ERCOT peak/off-peak spread: $20-30 |
| Seasonal swing | +/-$10 (sine, 365-day period) | Summer premium: $10-20 above shoulder months |
| Random noise | Normal distribution, sigma=$8 | Hourly price volatility |
| Spike probability | 0.5% of hours | Real ERCOT: 30-80 hours/year above $100 (~0.3-0.9%) |
| Spike magnitude | $100-$2000 | ERCOT ORDC cap: $2000/MWh (current) |
| Price floor | -$10 | Real negative prices occur 2-5% in high-wind periods |
| Zone offsets | West -$3, Houston +$4 | Reflects real congestion patterns |

**Important**: The financial model (NPV, IRR, Monte Carlo) does NOT use this market data. It uses the sidebar assumptions (base price, escalation, volatility) to project forward. Tab 5 provides **market context** — validating that your assumptions are reasonable relative to recent observed prices.

---

## ERCOT Load Zones

| Zone | Description |
|------|-------------|
| **LZ_SOUTH (LCRA)** | Load Zone South — LCRA service territory (default) |
| LZ_WEST | Load Zone West — wind-heavy, lowest prices |
| LZ_NORTH | Load Zone North — Dallas/Fort Worth metro |
| LZ_HOUSTON | Load Zone Houston — highest demand center |
| HB_SOUTH | Hub South — generation-weighted average |
| HB_NORTH | Hub North — generation-weighted average |
| HB_WEST | Hub West — generation-weighted average |
| HB_HOUSTON | Hub Houston — generation-weighted average |

**LZ vs HB**: Load Zones are load-weighted settlement prices (relevant for buyers). Hubs are generation-weighted (relevant for sellers). For utility planning, LZ is the primary reference.

---

## Scenarios

| Scenario | Gas | Energy | Carbon | Volatility | Description |
|----------|-----|--------|--------|------------|-------------|
| A: Conservative | $3.50 flat | $35 flat | $0 | 0.8x | No growth, no carbon |
| B: Base Case | $3.50 +2%/yr | $40 +2%/yr | $0 | 1.0x | Moderate growth |
| C: High Energy | $4.50 +3%/yr | $60 +3%/yr | $0 | 1.5x | High prices, volatile |
| D: Low Energy | $2.50 +1%/yr | $25 +1%/yr | $0 | 0.6x | PPAs very valuable |
| E: Carbon Tax | $4.00 +2%/yr | $50 +2.5%/yr | $50/ton | 1.2x | Renewables + storage win |
| F: Supply Stress | $5.00 +4%/yr | $55 +3%/yr | $0 | 2.0x | Delays, tariffs, gas risk |

---

## File Structure

```
├── streamlit_app.py        # Main app (10 tabs)
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Dark theme
├── data/                   # Market data CSVs (optional)
│   ├── ercot_lmp.csv
│   ├── ercot_load.csv
│   ├── ercot_fuel_mix.csv
│   └── ercot_as_prices.csv
└── modules/
    ├── __init__.py
    ├── data_loader.py      # CSV/API/synthetic data loading
    ├── portfolio.py        # Asset templates, portfolio builders
    ├── ppa.py              # PPA revenue, MTM, optimization
    ├── financial.py        # Cashflow, NPV, IRR, Monte Carlo
    ├── scoring.py          # 9-dimension scoring
    ├── market.py           # Price analysis, spike detection
    ├── frequency.py        # Inertia, freq simulation, AS revenue
    ├── transmission.py     # Congestion, interconnection, basis risk
    ├── risks.py            # Derating, gas, emissions, degradation
    └── scenarios.py        # 6 scenario definitions
```

---

## Setup

```bash
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Opens at http://localhost:8501

---

## Refreshing Market Data

To update the CSV data, run these queries in Snowflake against the Grid Status marketplace share and re-upload:

```sql
-- LMP (save as data/ercot_lmp.csv)
SELECT INTERVAL_START_LOCAL AS timestamp, LMP AS lmp, LOCATION AS zone
FROM GRID_STATUS__ERCOT_DATASETS.SHARE.ERCOT_LMP_BY_SETTLEMENT_POINT
WHERE INTERVAL_START_LOCAL >= DATEADD(day, -90, CURRENT_TIMESTAMP())
AND LOCATION IN ('LZ_SOUTH', 'LZ_WEST', 'LZ_NORTH', 'LZ_HOUSTON')
ORDER BY INTERVAL_START_LOCAL;

-- Load (save as data/ercot_load.csv)
SELECT INTERVAL_START_LOCAL AS timestamp, LOAD AS load_mw
FROM GRID_STATUS__ERCOT_DATASETS.SHARE.ERCOT_LOAD
WHERE INTERVAL_START_LOCAL >= DATEADD(day, -365, CURRENT_TIMESTAMP())
ORDER BY INTERVAL_START_LOCAL;

-- Fuel Mix (save as data/ercot_fuel_mix.csv)
SELECT INTERVAL_START_LOCAL AS timestamp, NATURAL_GAS AS gas, WIND AS wind,
       SOLAR AS solar, NUCLEAR AS nuclear, COAL_AND_LIGNITE AS coal,
       HYDRO AS hydro, OTHER AS other
FROM GRID_STATUS__ERCOT_DATASETS.SHARE.ERCOT_FUEL_MIX
WHERE INTERVAL_START_LOCAL >= DATEADD(day, -90, CURRENT_TIMESTAMP())
ORDER BY INTERVAL_START_LOCAL;
```

---

## What This Tool Is Not

- **Not a market forecast** — it doesn't predict prices, it models consequences of your assumptions
- **Not a dispatch model** — it doesn't simulate hourly unit commitment or economic dispatch
- **Not a replacement for an IRP** — it's a decision support layer that helps compare options quickly
- **Not a trading tool** — no real-time signals, no position management

## What It Is

A structured way to say: "Under these 6 futures, across these 9 dimensions, Portfolio A scores 7.2 and Portfolio B scores 6.8 — here's exactly why, and here's what each one risks."

---

## License

Internal tool — not for redistribution.
