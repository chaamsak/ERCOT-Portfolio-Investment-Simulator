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
| 5. Market Prices | Price duration curve, hourly profile, spike analysis, BESS arbitrage, zone selector |
| 6. Load vs Capacity | Zone demand forecast with phased portfolio ramp-up, new demand vs capacity gap |
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

## Load vs Capacity — How Tab 6 Works

Tab 6 has two charts that answer different questions:

### Chart 1: Absolute Demand vs Portfolio
Shows total zone peak demand (baseline + all growth) vs your portfolio capacity as assets come online. Answers: "How big is our portfolio relative to the whole zone?"

### Chart 2: Portfolio vs New Demand Growth
Shows ONLY the incremental new load being added to the zone (starting from zero), compared to your portfolio ramping up through construction. Answers: "Can our portfolio absorb the new demand coming into the zone?"

### How the portfolio ramp-up works:
Each asset has a construction time. The green line on the chart starts at 0 and grows as assets reach COD (Commercial Operation Date), then slowly declines due to degradation:

| Asset | COD | Why |
|-------|-----|-----|
| Flex/DR | Month 6 | Controls and contracts only |
| Solar | Month 14 | Panels and racking, fast |
| BESS (2hr) | Month 14 | Smaller footprint |
| BESS (4hr) | Month 18 | Larger battery install |
| RICE Peaker | Month 22 | Modular but needs gas interconnection |
| Wind | Month 24 | Foundation and tower |
| Combined Cycle | Month 36 | Major construction, environmental permits |

### The 4 metrics explained:

| Metric | What it means |
|--------|---------------|
| **Full Portfolio Online** | Year when 95%+ of total capacity is available (e.g., Year 3 for CC-heavy portfolios) |
| **Year 1 Available** | How many MW are actually online at end of Year 1 (often only fast assets like solar) |
| **Demand Exceeds Portfolio** | Year when new zone demand surpasses portfolio capacity. **Only counted after Full Portfolio Online** — ignores construction gap |
| **Year N Capacity (w/ degradation)** | Portfolio delivery at end of horizon after battery fade and thermal degradation |

### Example — Balanced 2GW, LZ_SOUTH (LCRA), 20-year horizon:
- **Full Portfolio Online**: Year 3 (CC takes 36 months)
- **Year 1 Available**: ~400 MW (only Solar is commissioning, BESS not yet done)
- **Demand Exceeds Portfolio**: Year 8-10 (depends on DC conversion rate in sidebar)
- **Year 20 Capacity**: ~1,700 MW (BESS lost ~35% capacity over 17 years of operation)

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

## Market Data

The app uses public ERCOT market data sourced from [Grid Status](https://gridstatus.io), which aggregates publicly available ERCOT reports with no login required.

Data is loaded automatically — no setup needed. If Grid Status data is unavailable, the app falls back to statistically calibrated synthetic data (see the **About the Synthetic Data** section).

To manually refresh the CSV data files in `data/`, download the latest datasets from https://gridstatus.io and save them as:
- `data/ercot_lmp.csv` — LMP by settlement point (columns: `timestamp`, `lmp`, `zone`)
- `data/ercot_load.csv` — System load (columns: `timestamp`, `load_mw`)
- `data/ercot_fuel_mix.csv` — Generation by fuel (columns: `timestamp`, `gas`, `wind`, `solar`, `nuclear`, `coal`, `hydro`, `other`)
- `data/ercot_as_prices.csv` — Ancillary service prices (columns: `timestamp`, `as_type`, `price`)

---

## What This Tool Is Not

- **Not a market forecast** — it doesn't predict prices, it models consequences of your assumptions
- **Not a dispatch model** — it doesn't simulate hourly unit commitment or economic dispatch
- **Not a replacement for an IRP** — it's a decision support layer that helps compare options quickly
- **Not a trading tool** — no real-time signals, no position management

## What It Is

A structured way to say: "Under these 6 futures, across these 9 dimensions, Portfolio A scores 7.2 and Portfolio B scores 6.8 — here's exactly why, and here's what each one risks."

---

## Glossary

| Term | Full Name | Plain English |
|------|-----------|---------------|
| **NPV** | Net Present Value | Total value a project creates in today's dollars. Positive = makes money. Negative = loses money. Accounts for the time value of money (a dollar today > a dollar in 10 years). |
| **IRR** | Internal Rate of Return | The annual return percentage the project earns. If IRR > your cost of capital (WACC), the project is worth doing. |
| **WACC** | Weighted Average Cost of Capital | How much it costs you to fund the project (mix of debt interest + equity return expectations). Used as the discount rate for NPV. |
| **CAPEX** | Capital Expenditure | Upfront cost to build the asset (construction, equipment, interconnection). Spent before the asset earns revenue. |
| **OPEX** | Operating Expenditure | Ongoing annual costs (maintenance, fuel, labor). Spent every year the asset operates. |
| **PPA** | Power Purchase Agreement | A contract where a buyer agrees to purchase electricity from a generator at a fixed price for a set number of years. Reduces revenue uncertainty for the seller. |
| **VPPA** | Virtual Power Purchase Agreement | A financial-only PPA. No physical electricity delivered. Buyer and seller settle the price difference in cash. Used when buyer and generator are in different locations. |
| **MTM** | Mark-to-Market | Current value of a PPA contract. If your PPA price is above today's market price, the contract is "in the money" (positive MTM). |
| **LMP** | Locational Marginal Price | The wholesale price of electricity at a specific point on the grid at a specific time. What generators get paid. |
| **ERCOT** | Electric Reliability Council of Texas | The organization that operates the Texas power grid and wholesale market. |
| **MW** | Megawatt | A unit of power capacity. 1 MW powers ~200-1000 homes depending on time of day. |
| **MWh** | Megawatt-hour | A unit of energy. 1 MW running for 1 hour = 1 MWh. What you actually sell. |
| **CF** | Capacity Factor | % of time an asset actually generates at full power. Solar ~26%, CC ~85%, BESS ~85%. |
| **BESS** | Battery Energy Storage System | Grid-scale batteries. Earn revenue from arbitrage (buy low, sell high) and grid services. |
| **CC** | Combined Cycle | Gas turbine + steam turbine power plant. High efficiency, runs most of the time (baseload). |
| **RICE** | Reciprocating Internal Combustion Engine | Fast-start gas engines used for peaking. Start in seconds, run during high-price hours. |
| **AS** | Ancillary Services | Grid stability products (frequency regulation, reserves). Generators get paid to be available, even if not dispatching energy. |
| **FFR** | Fast Frequency Response | Sub-second response to frequency deviations. Batteries excel here. Highest-paid AS product. |
| **RRS** | Responsive Reserve Service | Must respond within 10 minutes to arrest frequency decline. |
| **ECRS** | ERCOT Contingency Reserve Service | 10-minute reserve to cover generator trips. Newer ERCOT product. |
| **RegUp/RegDn** | Regulation Up / Regulation Down | Second-by-second frequency balancing. Generators follow AGC signals up or down. |
| **NonSpin** | Non-Spinning Reserve | Offline capacity that can start within 30 minutes. Cheapest AS product. |
| **RoCoF** | Rate of Change of Frequency | How fast grid frequency drops after a generator trips (Hz/s). Lower = safer. |
| **UFLS** | Under-Frequency Load Shedding | Emergency automatic disconnection of customers when frequency drops below 59.3 Hz. Last resort. |
| **Inertia** | Rotational Inertia | Spinning mass in generators that naturally resists frequency changes. Batteries don't have it but can mimic it (synthetic inertia). |
| **SB6** | Senate Bill 6 (Texas) | 2023 Texas law requiring dispatchable generation investment to maintain grid reliability. |
| **COD** | Commercial Operation Date | The day an asset starts generating revenue. |
| **DCF** | Discounted Cash Flow | Method of valuing a project by discounting all future cash to present value. NPV is a DCF calculation. |
| **Monte Carlo** | Monte Carlo Simulation | Running the financial model 1000+ times with random price variations to see the range of possible outcomes (P10/P50/P90). |
| **P10/P50/P90** | Probability Percentiles | P10 = 90% chance outcome is better. P50 = median (50/50). P90 = only 10% chance it's this good. Used to express risk. |
| **Basis Risk** | Locational Price Difference | The risk that prices differ between where you generate and where your contract settles. Costs money on VPPAs. |
| **DR** | Demand Response | Reducing load on command instead of adding generation. Gets paid like a generator. |
| **FOR** | Forced Outage Rate | % of time an asset is unexpectedly broken/offline. Higher = less reliable. |

---

## How PPA Works in This App

**You are always the plant OWNER.** You build it, you own it. The revenue mode only describes how you sell the output and who bears market risk:

| Mode | Who bears market risk | Revenue formula | Typical use case |
|------|-----------------------|-----------------|-----------------|
| **Merchant** | You (100%) | MW × CF × spot_price | Peakers, BESS arbitrage — you bet on high prices |
| **Physical PPA** | Shared — contracted % is protected, rest is spot | X% at fixed $/MWh + rest at spot | Solar, wind, CC selling to data centers or utilities |
| **VPPA** | You bear basis risk | Strike price paid as financial swap, no physical delivery | Wind/solar seller to distant corporate buyer |
| **Tolling** | Buyer (100%) | Fixed $/kW-month regardless of dispatch | BESS or peaker capacity sold to a utility or data center |
| **Hybrid** | Shared — only contracted share is protected | X% at PPA + (100-X)% at spot | Any asset wanting partial certainty + partial upside |

### Tolling in plain language:

You build a 200 MW BESS. A data center signs a tolling agreement: they pay you $8/kW-month = $1.6M/month whether they dispatch 0 hours or 24 hours per day. You get a guaranteed monthly check. They decide when to charge and discharge the battery. You have zero exposure to power prices — they do.

**When to use Tolling**: When you want revenue certainty and don't want to trade power. Common for BESS and fast-start peakers where a single large buyer (data center, utility, industrial) wants dedicated capacity.

### Which mode to use when building a new plant:

| If your goal is... | Use |
|--------------------|-----|
| Maximize upside, accept risk | Merchant |
| Stable revenue for project financing | Physical PPA or Tolling |
| Sell to a distant corporate buyer (ESG) | VPPA |
| Balance certainty and upside | Hybrid |
| Dedicated capacity for one buyer | Tolling |

### You can MIX modes across assets:

```
Portfolio example:
- Solar 400 MW → Physical PPA at $32/MWh × 15yr (stable, bankable)
- BESS 400 MW → Tolling at $8/kW-mo (guaranteed monthly payment)
- CC 700 MW → Hybrid: 80% PPA at $55 + 20% merchant (mostly stable)
- Peaker 300 MW → Merchant (only runs during high prices anyway)
- Wind 200 MW → VPPA at $28/MWh (financial contract with corporate buyer)
```

### What the app shows you:

1. **Contracted %** — Fraction of total revenue under contract (higher = more certain)
2. **PPA vs Merchant comparison** — Same portfolio, three scenarios: all merchant / current mix / fully contracted
3. **Mark-to-Market** — Are your PPAs above or below today's market price?
4. **Revenue Certainty Score** — 0-10 based on contracted %. Penalizes concentration risk.
5. **Optimization** — Recommends optimal contract % per asset for your volatility tolerance

### The key insight:

> PPAs and tolling reduce your NPV slightly (you give up upside) but dramatically reduce downside risk. Under Scenario D (low energy, $25/MWh), fully-merchant portfolios lose money while contracted ones remain stable. The question is not "PPA yes or no" — it's "how much certainty are you willing to pay for?"

---

## License

Internal tool — not for redistribution.
