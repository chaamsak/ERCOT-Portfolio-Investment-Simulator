# ERCOT Portfolio Investment Simulator

A Streamlit-based interactive tool for modeling generation portfolio economics in the ERCOT market, with full PPA structuring, financial forecasting, and grid stability analysis.

---

## What This Does

This app lets you build hypothetical power generation portfolios (batteries, gas plants, solar, wind) and instantly see:

- **Financial viability**: NPV, IRR, payback period, Monte Carlo risk analysis
- **PPA impact**: How different contract structures change risk/return profiles
- **Grid services**: Frequency response, ancillary services revenue, inertia contribution
- **Engineering risks**: Thermal derating, gas supply, battery degradation, emissions exposure
- **Market context**: Price duration curves, arbitrage potential, spike analysis
- **Scenario stress testing**: Compare portfolios across 6 pre-built market scenarios

---

## App Structure (10 Tabs)

| Tab | Purpose |
|-----|---------|
| 1. Portfolio | Build portfolios from asset templates, set MW, save/compare |
| 2. PPA & Offtake | Configure PPAs per asset, MTM valuation, optimization |
| 3. Executive Summary | KPIs, radar chart scoring, cumulative cashflow |
| 4. Financial Model | Stacked revenue, tornado sensitivity, Monte Carlo |
| 5. Market Prices | ERCOT price curves, BESS arbitrage, heatmaps |
| 6. Load vs Capacity | Demand forecast with data center growth projections |
| 7. Frequency | Inertia calculation, frequency event simulation, AS revenue |
| 8. Transmission | Congestion costs, interconnection estimates, VPPA basis risk |
| 9. Engineering Risks | Derating, gas supply, emissions, supply chain, degradation |
| 10. Scenarios | Multi-scenario NPV comparison with portfolio scoring |

---

## Asset Types Available

- **BESS (4hr / 2hr)** — Battery storage with arbitrage + ancillary services
- **Combined Cycle (CC)** — Baseload gas with high capacity factor
- **RICE Peaker** — Fast-start reciprocating engines for peak hours
- **Solar** — Utility-scale PV
- **Wind** — Onshore wind
- **Flex/DR** — Demand response / flexible load

---

## PPA Revenue Modes

Each asset can be configured with a different contract structure:

- **Merchant** — Full exposure to spot prices
- **Physical PPA** — Fixed $/MWh for contracted volume
- **Virtual PPA (VPPA)** — Contract for differences, no physical delivery
- **Tolling** — Fixed $/kW-month capacity payment
- **Hybrid** — Partial PPA + partial merchant

---

## Portfolio Scoring (9 Dimensions, 0-10 each)

| Dimension | Formula |
|-----------|---------|
| Financial Return | CLIP(NPV / $200M + 5, 0, 10) |
| Speed to Deploy | CLIP(10 - avg_months / 6, 0, 10) |
| Reliability | firm_MW / total_MW × 10 |
| Frequency Support | MIN(10, fast_response_MW / total × 12) |
| Emissions | Tiered: 0 tons = 10, >10M tons = 0 |
| Fuel Risk | 10 - gas_generation_share × 10 |
| Customer Fit | (firm + freq) / total × 6 + bonuses |
| Regulatory | Base 5, +3 storage, +2 firm >1GW, penalties for CO2 |
| Revenue Certainty | contracted_% / 10, -1 for concentration risk |

---

## File Structure

```
├── streamlit_app.py          # Main app with 10-tab layout
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── config.toml           # Dark theme configuration
└── modules/
    ├── __init__.py
    ├── data_loader.py        # ERCOT data (gridstatus or synthetic fallback)
    ├── portfolio.py          # Asset templates, portfolio builders
    ├── ppa.py                # PPA revenue, MTM, optimization
    ├── financial.py          # Cashflow, NPV, IRR, Monte Carlo
    ├── scoring.py            # 9-dimension portfolio scoring
    ├── market.py             # Price analysis, spike detection
    ├── frequency.py          # Inertia, freq simulation, AS revenue
    ├── transmission.py       # Congestion, interconnection, basis risk
    ├── risks.py              # Derating, gas, emissions, degradation
    └── scenarios.py          # 6 pre-built scenario definitions
```

---

## Scenarios Included

| Scenario | Description |
|----------|-------------|
| A: Conservative | Flat gas, low energy, no carbon price |
| B: Base Case | Moderate growth, 2% escalation |
| C: High Energy | $60/MWh base, high volatility |
| D: Low Energy | $25/MWh — PPAs very valuable here |
| E: Carbon Tax | $50/ton CO2, renewables + storage win |
| F: Supply Stress | High gas, 2x volatility, supply delays |

---

## Setup (Local)

```bash
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Opens at http://localhost:8501

---

## Live Data (Optional)

The app uses synthetic ERCOT-like data by default. To pull real market prices:

```bash
pip install gridstatus duckdb
```

No API key needed — gridstatus scrapes public ERCOT reports. Data is cached locally in DuckDB.

---

## Key Design Principles

1. **Transparency** — Every number is traceable. Formulas and methodology shown in expandable sections.
2. **PPA is Central** — Contract structure fundamentally changes risk/return. The app makes this obvious.
3. **Interactivity** — Every input instantly updates all outputs.
4. **Comparison** — Always shows "vs what?" (PPA vs merchant, scenario A vs B).
5. **Education** — Expandable sections explain ERCOT concepts for non-experts.

---

## Tech Stack

- **Frontend**: Streamlit
- **Charts**: Plotly (interactive, hover tooltips, downloadable)
- **Compute**: NumPy, SciPy (Monte Carlo, optimization)
- **Data**: Pandas, DuckDB (optional cache), gridstatus (optional live ERCOT)

---

## License

Internal tool — not for redistribution.
