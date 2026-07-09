# ERCOT Portfolio Simulation and PPA Structuring Tool
# Co-authored with CoCo
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from modules.portfolio import (
    ASSET_TEMPLATES, PORTFOLIO_TEMPLATES, create_asset,
    load_portfolio_template, get_total_mw, get_total_capex,
)
from modules.ppa import (
    calc_ppa_revenue_asset, calc_ppa_risk_metrics,
    calc_mark_to_market, optimize_ppa_mix,
)
from modules.financial import (
    run_financial_model, run_monte_carlo, build_energy_prices,
)
from modules.scoring import score_portfolio, SCORING_METHODOLOGY
from modules.market import (
    generate_synthetic_prices, calc_price_duration_curve,
    calc_hourly_profile, calc_spike_analysis, calc_bess_arbitrage,
    calc_price_heatmap, get_ppa_benchmark_prices,
)
from modules.frequency import (
    calc_portfolio_inertia, simulate_frequency_event, calc_as_revenue,
)
from modules.transmission import (
    calc_congestion_cost, calc_interconnection_costs, calc_basis_risk,
)
from modules.risks import (
    calc_thermal_derating, calc_gas_supply_risk, calc_emissions,
    calc_supply_chain_delays, calc_battery_degradation, calc_forced_outage,
)
from modules.scenarios import SCENARIOS, get_scenario_params
from modules.data_loader import get_ercot_lmp, get_ercot_load, ERCOT_ZONES

st.set_page_config(page_title="ERCOT Portfolio Simulator", layout="wide")
st.title("ERCOT Portfolio Investment Simulator")

# --- Session State Initialization ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
if "saved_portfolios" not in st.session_state:
    st.session_state.saved_portfolios = {}
if "next_id" not in st.session_state:
    st.session_state.next_id = 1

# --- Sidebar: Global Parameters ---
st.sidebar.header("Global Parameters")

with st.sidebar.expander("Energy Market", expanded=True):
    base_energy_price = st.slider("Base Energy Price ($/MWh)", 20.0, 80.0, 40.0)
    energy_escalation = st.slider("Energy Escalation (%/yr)", 0.0, 5.0, 2.0)
    peak_offpeak_ratio = st.slider("Peak/Off-Peak Ratio", 1.2, 3.0, 1.8)
    volatility_multiplier = st.slider("Volatility Multiplier", 0.5, 3.0, 1.0)

with st.sidebar.expander("Gas Market"):
    gas_price = st.slider("Natural Gas ($/MMBtu)", 2.0, 8.0, 3.50)
    gas_escalation = st.slider("Gas Escalation (%/yr)", 0.0, 5.0, 2.0)

with st.sidebar.expander("Financial"):
    discount_rate = st.slider("Discount Rate / WACC (%)", 6.0, 14.0, 8.0)
    carbon_price = st.slider("Carbon Price ($/ton CO2)", 0.0, 75.0, 0.0)
    projection_years = st.slider("Projection Years", 5, 30, 20)
    inflation_rate = st.slider("Inflation Rate (%)", 0.0, 5.0, 2.5)

with st.sidebar.expander("Load Growth"):
    organic_growth = st.slider("Annual Organic Growth (MW)", 300, 1500, 800)
    dc_announcements = st.slider("Data Center Announcements (MW)", 1000, 5600, 3000)
    dc_conversion = st.slider("DC Conversion Rate (%)", 20, 90, 50)

params = {
    "base_energy_price": base_energy_price, "energy_escalation": energy_escalation,
    "peak_offpeak_ratio": peak_offpeak_ratio, "volatility_multiplier": volatility_multiplier,
    "gas_price": gas_price, "gas_escalation": gas_escalation,
    "discount_rate": discount_rate, "carbon_price": carbon_price,
    "projection_years": projection_years, "inflation_rate": inflation_rate,
    "organic_growth": organic_growth, "dc_announcements": dc_announcements,
    "dc_conversion": dc_conversion,
}

# --- Main Tabs ---
tabs = st.tabs([
    "1. Portfolio", "2. PPA & Offtake", "3. Executive Summary",
    "4. Financial Model", "5. Market Prices", "6. Load vs Capacity",
    "7. Frequency", "8. Transmission", "9. Engineering Risks",
    "10. Scenarios",
])

# ============================================================
# TAB 1: PORTFOLIO MANAGER
# ============================================================
with tabs[0]:
    st.header("Portfolio Manager")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Add Asset")
        template = st.selectbox("Asset Template", list(ASSET_TEMPLATES.keys()))
        custom_mw = st.number_input("Capacity (MW)", min_value=10, max_value=5000,
                                     value=ASSET_TEMPLATES[template]["mw"])

        if st.button("Add to Portfolio"):
            asset = create_asset(template, {"mw": custom_mw})
            asset["id"] = st.session_state.next_id
            st.session_state.next_id += 1
            st.session_state.portfolio.append(asset)
            st.rerun()

        st.divider()
        st.subheader("Load Template")
        tmpl = st.selectbox("Portfolio Template", list(PORTFOLIO_TEMPLATES.keys()))
        if st.button("Load Template"):
            st.session_state.portfolio = load_portfolio_template(tmpl)
            for i, a in enumerate(st.session_state.portfolio):
                a["id"] = i + 1
            st.session_state.next_id = len(st.session_state.portfolio) + 1
            st.rerun()

        st.divider()
        st.subheader("Save / Compare")
        save_name = st.text_input("Portfolio Name")
        if st.button("Save Current") and save_name:
            st.session_state.saved_portfolios[save_name] = st.session_state.portfolio.copy()
            st.success(f"Saved '{save_name}'")

        if st.button("Clear Portfolio"):
            st.session_state.portfolio = []
            st.rerun()

    with col2:
        st.subheader(f"Current Portfolio ({get_total_mw(st.session_state.portfolio)} MW)")

        if st.session_state.portfolio:
            for i, asset in enumerate(st.session_state.portfolio):
                ppa_badge = ""
                if asset["revenue_mode"] == "merchant":
                    ppa_badge = "Merchant"
                elif asset["revenue_mode"] == "physical_ppa":
                    ppa_badge = f"PPA ${asset['ppa_price']}/MWh x {asset['ppa_tenor']}yr"
                elif asset["revenue_mode"] == "vppa":
                    ppa_badge = f"VPPA ${asset['ppa_price']}/MWh"
                elif asset["revenue_mode"] == "tolling":
                    ppa_badge = f"Tolling ${asset['tolling_rate_kw_month']}/kW-mo"
                elif asset["revenue_mode"] == "hybrid":
                    ppa_badge = f"Hybrid {asset['ppa_pct_contracted']}% @ ${asset['ppa_price']}"

                with st.expander(f"{asset['name']} - {asset['mw']} MW | {ppa_badge}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        asset["mw"] = st.number_input("MW", value=asset["mw"], key=f"mw_{i}")
                        asset["capacity_factor"] = st.number_input(
                            "Capacity Factor", value=asset["capacity_factor"],
                            min_value=0.05, max_value=1.0, step=0.05, key=f"cf_{i}")
                    with c2:
                        asset["revenue_mode"] = st.selectbox(
                            "Revenue Mode",
                            ["merchant", "physical_ppa", "vppa", "tolling", "hybrid"],
                            index=["merchant", "physical_ppa", "vppa", "tolling", "hybrid"].index(asset["revenue_mode"]),
                            key=f"mode_{i}")
                        if asset["revenue_mode"] in ("physical_ppa", "vppa", "hybrid"):
                            asset["ppa_price"] = st.number_input(
                                "PPA Price ($/MWh)", value=max(20.0, float(asset["ppa_price"])),
                                min_value=20.0, max_value=120.0, key=f"ppa_{i}")
                            asset["ppa_pct_contracted"] = st.slider(
                                "% Contracted", 0, 100, asset["ppa_pct_contracted"], key=f"pct_{i}")
                    with c3:
                        if asset["revenue_mode"] in ("physical_ppa", "vppa", "hybrid"):
                            asset["ppa_tenor"] = st.number_input(
                                "Tenor (years)", value=asset["ppa_tenor"],
                                min_value=5, max_value=25, key=f"tenor_{i}")
                            asset["ppa_escalation"] = st.number_input(
                                "Escalation (%/yr)", value=asset["ppa_escalation"],
                                min_value=0.0, max_value=3.0, step=0.25, key=f"esc_{i}")
                            asset["ppa_buyer_type"] = st.selectbox(
                                "Buyer Type",
                                ["Data Center", "Municipal Utility", "Retail Electric Provider",
                                 "Crypto Miner", "Industrial", "Cooperative", "Corporate (ESG)"],
                                key=f"buyer_{i}")
                        if asset["revenue_mode"] == "tolling":
                            asset["tolling_rate_kw_month"] = st.number_input(
                                "Tolling Rate ($/kW-mo)", value=float(asset["tolling_rate_kw_month"]),
                                min_value=4.0, max_value=20.0, key=f"toll_{i}")

                    if st.button("Remove", key=f"rm_{i}"):
                        st.session_state.portfolio.pop(i)
                        st.rerun()

            summary_df = pd.DataFrame([
                {"Asset": a["name"], "MW": a["mw"], "Type": a["type"],
                 "Revenue Mode": a["revenue_mode"],
                 "CAPEX ($M)": round(a["mw"] * a["capex_per_kw"] * 1000 / 1e6, 1)}
                for a in st.session_state.portfolio
            ])
            st.dataframe(summary_df, use_container_width=True)
        else:
            st.info("Add assets or load a template to get started.")

# ============================================================
# TAB 2: PPA & OFFTAKE
# ============================================================
with tabs[1]:
    st.header("PPA & Offtake Structuring")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        energy_prices_y1 = {"avg": base_energy_price}
        ppa_metrics = calc_ppa_risk_metrics(st.session_state.portfolio, energy_prices_y1, projection_years)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Contracted %", f"{ppa_metrics['contracted_pct']:.1f}%")
        k2.metric("Avg PPA Tenor", f"{ppa_metrics['avg_tenor']:.1f} yrs")
        k3.metric("Max Concentration", f"{ppa_metrics['max_concentration']:.1f}%")
        k4.metric("Revenue Certainty", f"{ppa_metrics['contracted_pct']/10:.1f}/10")

        st.divider()

        st.subheader("PPA vs Merchant Comparison")
        col_a, col_b, col_c = st.columns(3)

        merchant_portfolio = [a.copy() for a in st.session_state.portfolio]
        for a in merchant_portfolio:
            a["revenue_mode"] = "merchant"
        merchant_result = run_financial_model(merchant_portfolio, params)

        current_result = run_financial_model(st.session_state.portfolio, params)

        contracted_portfolio = [a.copy() for a in st.session_state.portfolio]
        for a in contracted_portfolio:
            if a["type"] == "storage":
                a["revenue_mode"] = "tolling"
            else:
                a["revenue_mode"] = "physical_ppa"
            a["ppa_pct_contracted"] = 100
        contracted_result = run_financial_model(contracted_portfolio, params)

        with col_a:
            st.markdown("**All Merchant**")
            st.metric("NPV", f"${merchant_result['npv']:.0f}M")
            st.metric("IRR", f"{merchant_result['irr']:.1f}%" if merchant_result['irr'] else "N/A")
        with col_b:
            st.markdown("**Current PPA Mix**")
            st.metric("NPV", f"${current_result['npv']:.0f}M")
            st.metric("IRR", f"{current_result['irr']:.1f}%" if current_result['irr'] else "N/A")
        with col_c:
            st.markdown("**Fully Contracted**")
            st.metric("NPV", f"${contracted_result['npv']:.0f}M")
            st.metric("IRR", f"{contracted_result['irr']:.1f}%" if contracted_result['irr'] else "N/A")

        st.divider()

        st.subheader("Mark-to-Market Valuation")
        current_market = st.number_input("Current Market Price ($/MWh)", value=40.0, min_value=10.0, max_value=100.0)
        mtm = calc_mark_to_market(st.session_state.portfolio, current_market)
        mtm_df = pd.DataFrame(mtm)
        total_mtm = mtm_df["mtm"].sum()
        st.metric("Total Portfolio MTM", f"${total_mtm:.1f}M",
                  delta="In the Money" if total_mtm > 0 else "Underwater")
        fig_mtm = px.bar(mtm_df, x="name", y="mtm", color="mtm",
                         color_continuous_scale=["red", "gray", "green"],
                         title="Mark-to-Market by Asset ($M)")
        st.plotly_chart(fig_mtm, use_container_width=True)

        st.divider()

        st.subheader("PPA Mix Optimization")
        max_vol = st.slider("Max Revenue Volatility ($M)", 10, 200, 50)
        if st.button("Optimize PPA Mix"):
            optimal = optimize_ppa_mix(st.session_state.portfolio, energy_prices_y1, max_vol)
            st.write("**Recommended Contracted %:**")
            for name, pct in optimal.items():
                st.write(f"- {name}: {pct}%")

        with st.expander("PPA Types Explained"):
            st.markdown("""
**Physical PPA**: Seller delivers physical MWh to buyer at contracted price. Buyer takes volume risk.

**Virtual PPA (VPPA)**: Financial contract for differences. No physical delivery. Basis risk exists.

**Tolling Agreement**: Buyer pays fixed $/kW-month for dispatch rights. Seller earns guaranteed revenue.

**Hybrid**: X% contracted at PPA price, remainder at market. Balances certainty and upside.

**Typical 2024-2025 PPA Prices:**
- Solar: $25-40/MWh
- Wind: $20-35/MWh
- CC: $45-75/MWh
- BESS Tolling: $6-12/kW-mo
""")

# ============================================================
# TAB 3: EXECUTIVE SUMMARY
# ============================================================
with tabs[2]:
    st.header("Executive Summary")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        result = run_financial_model(st.session_state.portfolio, params)
        energy_prices_y1 = {"avg": base_energy_price}
        ppa_m = calc_ppa_risk_metrics(st.session_state.portfolio, energy_prices_y1, projection_years)
        scores = score_portfolio(st.session_state.portfolio, result, ppa_m)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total MW", f"{get_total_mw(st.session_state.portfolio):,.0f}")
        c2.metric("Total CAPEX", f"${result['total_capex']:,.0f}M")
        c3.metric("NPV", f"${result['npv']:,.0f}M")
        c4.metric("IRR", f"{result['irr']:.1f}%" if result['irr'] else "N/A")
        c5.metric("Payback", f"Year {result['payback']}" if result['payback'] else "N/A")

        c6, c7, c8 = st.columns(3)
        c6.metric("Contracted %", f"{ppa_m['contracted_pct']:.0f}%")
        c7.metric("Overall Score", f"{scores['Overall']:.1f}/10")
        c8.metric("Revenue Certainty", f"{scores['Revenue Certainty']:.1f}/10")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            capex_data = [{"Asset": a["name"], "CAPEX_M": a["mw"] * a["capex_per_kw"] * 1000 / 1e6}
                          for a in st.session_state.portfolio]
            fig_capex = px.pie(pd.DataFrame(capex_data), values="CAPEX_M", names="Asset",
                               title="CAPEX Breakdown")
            st.plotly_chart(fig_capex, use_container_width=True)

        with col2:
            categories = [k for k in scores if k != "Overall"]
            values = [scores[k] for k in categories]
            fig_radar = go.Figure(go.Scatterpolar(r=values + [values[0]],
                                                   theta=categories + [categories[0]], fill='toself'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(range=[0, 10])),
                                     title="Portfolio Score")
            st.plotly_chart(fig_radar, use_container_width=True)

        years_data = result["yearly_data"]
        cf_df = pd.DataFrame([{"Year": d["year"], "Cumulative ($M)": d["cumulative"]} for d in years_data])
        fig_cf = px.line(cf_df, x="Year", y="Cumulative ($M)", title="Cumulative Cashflow")
        fig_cf.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_cf, use_container_width=True)

# ============================================================
# TAB 4: FINANCIAL MODEL
# ============================================================
with tabs[3]:
    st.header("Financial Model")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        result = run_financial_model(st.session_state.portfolio, params)

        rev_data = []
        for yd in result["yearly_data"]:
            for ad in yd["asset_details"]:
                rev_data.append({"Year": yd["year"], "Asset": ad["name"], "Net ($M)": ad["net"]})
        rev_df = pd.DataFrame(rev_data)
        fig_rev = px.bar(rev_df, x="Year", y="Net ($M)", color="Asset",
                         title="Net Revenue by Asset per Year")
        st.plotly_chart(fig_rev, use_container_width=True)

        st.subheader("NPV Sensitivity (Tornado)")
        base_npv = result["npv"]
        sensitivities = {}
        for param_name, low, high in [
            ("gas_price", gas_price * 0.7, gas_price * 1.3),
            ("base_energy_price", base_energy_price * 0.7, base_energy_price * 1.3),
            ("discount_rate", discount_rate - 2, discount_rate + 2),
            ("carbon_price", 0, 50),
        ]:
            p_low = params.copy()
            p_low[param_name] = low
            p_high = params.copy()
            p_high[param_name] = high
            npv_low = run_financial_model(st.session_state.portfolio, p_low)["npv"]
            npv_high = run_financial_model(st.session_state.portfolio, p_high)["npv"]
            sensitivities[param_name] = (npv_low - base_npv, npv_high - base_npv)

        tornado_df = pd.DataFrame([
            {"Parameter": k, "Low": v[0], "High": v[1], "Range": abs(v[1] - v[0])}
            for k, v in sensitivities.items()
        ]).sort_values("Range", ascending=True)

        fig_tornado = go.Figure()
        for _, row in tornado_df.iterrows():
            fig_tornado.add_trace(go.Bar(name="Low", x=[row["Low"]], y=[row["Parameter"]],
                                          orientation='h', marker_color='red', showlegend=False))
            fig_tornado.add_trace(go.Bar(name="High", x=[row["High"]], y=[row["Parameter"]],
                                          orientation='h', marker_color='green', showlegend=False))
        fig_tornado.update_layout(title=f"NPV Sensitivity (Base: ${base_npv:.0f}M)", barmode='overlay')
        st.plotly_chart(fig_tornado, use_container_width=True)

        st.subheader("Monte Carlo Analysis")
        n_sims = st.selectbox("Simulations", [200, 500, 1000], index=0)
        if st.button("Run Monte Carlo"):
            with st.spinner("Running simulations..."):
                mc = run_monte_carlo(st.session_state.portfolio, params, n_sims)
            c1, c2, c3 = st.columns(3)
            c1.metric("P10 NPV", f"${mc['p10']:.0f}M")
            c2.metric("P50 NPV", f"${mc['p50']:.0f}M")
            c3.metric("P90 NPV", f"${mc['p90']:.0f}M")
            fig_mc = px.histogram(x=mc["all_npvs"], nbins=50, title="NPV Distribution (Monte Carlo)")
            fig_mc.add_vline(x=mc["p10"], line_dash="dash", annotation_text="P10")
            fig_mc.add_vline(x=mc["p50"], line_dash="dash", annotation_text="P50")
            fig_mc.add_vline(x=mc["p90"], line_dash="dash", annotation_text="P90")
            st.plotly_chart(fig_mc, use_container_width=True)

        st.subheader("Year-by-Year Cashflow")
        cf_table = pd.DataFrame([
            {"Year": d["year"],
             "Net CF ($M)": round(sum(ad["net"] for ad in d["asset_details"]), 2),
             "Cumulative ($M)": round(d["cumulative"], 2)}
            for d in result["yearly_data"]
        ])
        st.dataframe(cf_table, use_container_width=True)
        st.download_button("Download CSV", cf_table.to_csv(index=False), "cashflow.csv")

# ============================================================
# TAB 5: MARKET PRICES
# ============================================================
with tabs[4]:
    st.header("Market Prices (ERCOT)")

    selected_zones = st.multiselect(
        "Select Load Zones",
        ERCOT_ZONES,
        default=["LZ_SOUTH (LCRA)"],
        help="LZ_SOUTH corresponds to the LCRA service territory"
    )

    @st.cache_data(ttl=3600)
    def load_price_data(zones):
        return get_ercot_lmp(days=90, zones=zones)

    if not selected_zones:
        st.warning("Select at least one zone.")
    else:
        df_prices = load_price_data(tuple(selected_zones))

        # Debug: show raw columns and source
        with st.expander("Debug: Data Info"):
            st.write("Columns:", list(df_prices.columns))
            st.write("Shape:", df_prices.shape)
            st.write("First rows:", df_prices.head(3))

        # Data source indicator
        data_source = df_prices["_source"].iloc[0] if "_source" in df_prices.columns else "unknown"
        if "live" in data_source:
            st.success(f"Data Source: {data_source}")
        elif "error" in data_source:
            st.error(f"Data Source: {data_source}")
        else:
            st.warning(f"Data Source: {data_source}")

        df_prices["hour"] = pd.to_datetime(df_prices["timestamp"]).dt.hour
        df_prices["month"] = pd.to_datetime(df_prices["timestamp"]).dt.month
        df_prices["date"] = pd.to_datetime(df_prices["timestamp"]).dt.date

        # Time series by zone
        if "zone" in df_prices.columns and len(selected_zones) > 1:
            fig_ts = px.line(df_prices, x="timestamp", y="lmp", color="zone",
                             title="LMP by Zone ($/MWh)")
            st.plotly_chart(fig_ts, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            pdc = calc_price_duration_curve(df_prices)
            fig_pdc = px.line(y=pdc.values, title="Price Duration Curve ($/MWh)",
                              labels={"y": "LMP ($/MWh)", "x": "Hours"})
            st.plotly_chart(fig_pdc, use_container_width=True)

        with col2:
            hourly = calc_hourly_profile(df_prices)
            fig_hourly = px.bar(x=hourly.index, y=hourly.values,
                                title="Average Price by Hour", labels={"x": "Hour", "y": "$/MWh"})
            st.plotly_chart(fig_hourly, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            spikes = calc_spike_analysis(df_prices)
            fig_spikes = px.bar(x=list(spikes.keys()), y=list(spikes.values()),
                                title="Price Spike Frequency", labels={"x": "Threshold", "y": "Hours"})
            st.plotly_chart(fig_spikes, use_container_width=True)

        with col4:
            arb = calc_bess_arbitrage(df_prices)
            fig_arb = px.line(y=arb.values, title="BESS Implied Daily Arbitrage ($/MW-day)",
                              labels={"y": "$/MW-day"})
            st.plotly_chart(fig_arb, use_container_width=True)

        heatmap = calc_price_heatmap(df_prices)
        fig_heat = px.imshow(heatmap, title="Price Heatmap (Hour x Month)",
                             labels={"x": "Month", "y": "Hour", "color": "$/MWh"},
                             aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)

        st.subheader("PPA Benchmark Prices vs Spot Market")
        benchmarks = get_ppa_benchmark_prices()
        avg_spot = df_prices["lmp"].mean()
        st.metric("Average Spot Price (90 days)", f"${avg_spot:.1f}/MWh")
        bench_df = pd.DataFrame([
            {"Technology": k, "Low": v["low"], "Mid": v["mid"], "High": v["high"]}
            for k, v in benchmarks.items()
        ])
        st.dataframe(bench_df, use_container_width=True)

# ============================================================
# TAB 6: LOAD VS CAPACITY
# ============================================================
with tabs[5]:
    st.header("Load vs Capacity Forecast")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        # Zone selection for demand context
        zone_peaks = {
            "LZ_SOUTH (LCRA)": 12000,
            "LZ_HOUSTON": 22000,
            "LZ_NORTH": 20000,
            "LZ_WEST": 8000,
            "All ERCOT": 75000,
        }
        demand_zone = st.selectbox("Demand Zone", list(zone_peaks.keys()),
                                    help="Select the zone your portfolio is serving. LZ_SOUTH = LCRA territory.")
        current_peak = zone_peaks[demand_zone]

        # Scale growth proportionally to zone size
        zone_fraction = current_peak / 75000
        zone_organic = int(organic_growth * zone_fraction)
        zone_dc = int(dc_announcements * zone_fraction)

        st.caption(f"Zone base peak: {current_peak:,} MW | Organic growth: ~{zone_organic} MW/yr | DC growth: ~{zone_dc} MW announced")

        years_fwd = projection_years
        load_proj = []
        cap = get_total_mw(st.session_state.portfolio)

        peak = current_peak
        for y in range(years_fwd):
            growth = zone_organic + zone_dc * (dc_conversion / 100) * (0.1 if y < 3 else 0.05)
            peak += growth
            load_proj.append({"Year": y + 1, "Peak Demand (MW)": peak,
                              "Portfolio Capacity (MW)": cap})

        load_df = pd.DataFrame(load_proj)
        fig_load = go.Figure()
        fig_load.add_trace(go.Scatter(x=load_df["Year"], y=load_df["Peak Demand (MW)"],
                                       name=f"Projected Demand ({demand_zone})", line=dict(color="red")))
        fig_load.add_trace(go.Scatter(x=load_df["Year"], y=load_df["Portfolio Capacity (MW)"],
                                       name="Portfolio Capacity", line=dict(color="green")))
        fig_load.update_layout(title=f"Absolute Demand vs Portfolio — {demand_zone}", yaxis_title="MW")
        st.plotly_chart(fig_load, use_container_width=True)

        # Second chart: Portfolio vs NEW demand growth only
        st.subheader("Portfolio vs New Demand Growth")
        st.caption("Shows only the incremental load added to the zone — not the existing baseline.")
        cumulative_growth = []
        cum = 0
        for y in range(years_fwd):
            growth = zone_organic + zone_dc * (dc_conversion / 100) * (0.1 if y < 3 else 0.05)
            cum += growth
            cumulative_growth.append({"Year": y + 1, "Cumulative New Demand (MW)": cum,
                                       "Portfolio Capacity (MW)": cap})

        growth_df = pd.DataFrame(cumulative_growth)
        fig_growth = go.Figure()
        fig_growth.add_trace(go.Scatter(x=growth_df["Year"], y=growth_df["Cumulative New Demand (MW)"],
                                         name="Cumulative New Demand", line=dict(color="orange"),
                                         fill="tozeroy", fillcolor="rgba(255,165,0,0.1)"))
        fig_growth.add_trace(go.Scatter(x=growth_df["Year"], y=growth_df["Portfolio Capacity (MW)"],
                                         name="Portfolio Capacity", line=dict(color="green", width=3)))
        fig_growth.update_layout(title=f"Portfolio vs Incremental Load Growth — {demand_zone}",
                                  yaxis_title="MW")
        st.plotly_chart(fig_growth, use_container_width=True)

        # When does new demand exceed portfolio?
        crossover_year = next((row["Year"] for _, row in growth_df.iterrows()
                               if row["Cumulative New Demand (MW)"] > cap), None)

        # Portfolio as % of zone demand
        pct_of_zone = cap / current_peak * 100
        reserve_margin = (cap - load_proj[0]["Peak Demand (MW)"]) / load_proj[0]["Peak Demand (MW)"] * 100
        pct_of_new = cap / cumulative_growth[-1]["Cumulative New Demand (MW)"] * 100 if cumulative_growth else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Portfolio as % of Zone Peak", f"{pct_of_zone:.1f}%")
        c2.metric("Portfolio vs 20yr New Demand", f"{pct_of_new:.0f}%")
        c3.metric("Demand Exceeds Portfolio", f"Year {crossover_year}" if crossover_year else "Never (within horizon)")
        c4.metric(f"Zone Peak ({demand_zone})", f"{current_peak:,} MW")

# ============================================================
# TAB 7: FREQUENCY & RELIABILITY
# ============================================================
with tabs[6]:
    st.header("Frequency & Grid Stability")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        inertia = calc_portfolio_inertia(st.session_state.portfolio)
        c1, c2, c3 = st.columns(3)
        c1.metric("Physical Inertia (MW-s)", f"{inertia['physical_mw_s']:,.0f}")
        c2.metric("Synthetic Inertia (MW-s)", f"{inertia['synthetic_mw_s']:,.0f}")
        c3.metric("Total Inertia (MW-s)", f"{inertia['total_mw_s']:,.0f}")

        st.subheader("Frequency Event Simulation")
        trip_mw = st.slider("Trip Size (MW)", 500, 2000, 1000)
        sim = simulate_frequency_event(st.session_state.portfolio, trip_mw)

        fig_freq = go.Figure()
        fig_freq.add_trace(go.Scatter(x=sim["times"], y=sim["frequency"], name="Frequency"))
        fig_freq.add_hline(y=59.95, line_dash="dash", line_color="orange", annotation_text="Alert (59.95)")
        fig_freq.add_hline(y=59.30, line_dash="dash", line_color="red", annotation_text="UFLS (59.30)")
        fig_freq.update_layout(title=f"Frequency Response (Trip: {trip_mw} MW, RoCoF: {sim['rocof']:.3f} Hz/s)",
                               xaxis_title="Time (s)", yaxis_title="Frequency (Hz)")
        st.plotly_chart(fig_freq, use_container_width=True)
        st.metric("Frequency Nadir", f"{sim['nadir']:.3f} Hz at t={sim['nadir_time']:.1f}s")

        st.subheader("Ancillary Services Revenue")
        as_data = calc_as_revenue(st.session_state.portfolio)
        as_df = pd.DataFrame(as_data)
        fig_as = px.bar(as_df, x="name", y="revenue_M", title="Annual AS Revenue by Asset ($M)")
        st.plotly_chart(fig_as, use_container_width=True)
        st.dataframe(as_df[["name", "services", "revenue_M", "mw"]], use_container_width=True)

# ============================================================
# TAB 8: TRANSMISSION
# ============================================================
with tabs[7]:
    st.header("Transmission & Interconnection")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        bus_diff = st.slider("Bus-Zone Price Differential ($/MWh)", 0.0, 10.0, 2.5)
        congestion = calc_congestion_cost(st.session_state.portfolio, bus_diff)
        cong_df = pd.DataFrame(congestion)
        fig_cong = px.bar(cong_df, x="name", y="congestion_cost_M",
                          title="Annual Congestion Cost by Asset ($M)")
        st.plotly_chart(fig_cong, use_container_width=True)

        st.subheader("Interconnection Cost Estimates")
        network_pct = st.slider("Network Upgrade Severity (%)", 0, 100, 50)
        ic_costs = calc_interconnection_costs(st.session_state.portfolio, network_pct)
        ic_df = pd.DataFrame(ic_costs)
        st.dataframe(ic_df, use_container_width=True)
        total_ic = sum(c["total"] for c in ic_costs)
        st.metric("Total Interconnection Cost", f"${total_ic:.1f}M")

        basis = calc_basis_risk(st.session_state.portfolio)
        if basis:
            st.subheader("VPPA Basis Risk")
            st.dataframe(pd.DataFrame(basis), use_container_width=True)

# ============================================================
# TAB 9: ENGINEERING RISKS
# ============================================================
with tabs[8]:
    st.header("Engineering Risks")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        risk_tabs = st.tabs(["Thermal Derating", "Gas Supply", "Emissions",
                              "Supply Chain", "Reliability", "Degradation"])

        with risk_tabs[0]:
            peak_temp = st.slider("Peak Temperature (F)", 90, 120, 105)
            derating = calc_thermal_derating(st.session_state.portfolio, peak_temp)
            dr_df = pd.DataFrame(derating)
            fig_dr = px.bar(dr_df, x="name", y=["rated_mw", "available_mw"],
                            barmode="group", title=f"Rated vs Available MW at {peak_temp}F")
            st.plotly_chart(fig_dr, use_container_width=True)

        with risk_tabs[1]:
            curtail_days = st.slider("Curtailment Days", 1, 14, 5)
            gas_risk = calc_gas_supply_risk(st.session_state.portfolio, curtail_days)
            if gas_risk:
                st.dataframe(pd.DataFrame(gas_risk), use_container_width=True)
            else:
                st.info("No gas-dependent assets in portfolio.")

        with risk_tabs[2]:
            emissions_data, total_co2 = calc_emissions(st.session_state.portfolio)
            em_df = pd.DataFrame(emissions_data)
            st.metric("Total CO2 (tons/yr)", f"{total_co2:,.0f}")
            if total_co2 > 0:
                fig_em = px.pie(em_df[em_df["co2_tons_yr"] > 0], values="co2_tons_yr",
                                names="name", title="CO2 Emissions by Asset")
                st.plotly_chart(fig_em, use_container_width=True)

            carbon_range = np.arange(0, 80, 5)
            carbon_impact = []
            for cp in carbon_range:
                p = params.copy()
                p["carbon_price"] = cp
                r = run_financial_model(st.session_state.portfolio, p)
                carbon_impact.append({"Carbon Price": cp, "NPV ($M)": r["npv"]})
            fig_carbon = px.line(pd.DataFrame(carbon_impact), x="Carbon Price", y="NPV ($M)",
                                 title="NPV vs Carbon Price")
            st.plotly_chart(fig_carbon, use_container_width=True)

        with risk_tabs[3]:
            delay = st.slider("Delay (months)", 0, 24, 0)
            tariff = st.slider("BESS Tariff Surcharge (%)", 0, 50, 0)
            sc_data = calc_supply_chain_delays(st.session_state.portfolio, delay, tariff)
            st.dataframe(pd.DataFrame(sc_data), use_container_width=True)

        with risk_tabs[4]:
            outage_data = calc_forced_outage(st.session_state.portfolio)
            st.dataframe(pd.DataFrame(outage_data), use_container_width=True)

        with risk_tabs[5]:
            storage_assets = [a for a in st.session_state.portfolio if a["type"] == "storage"]
            if storage_assets:
                for asset in storage_assets:
                    deg = calc_battery_degradation(asset)
                    if deg:
                        fig_deg = px.line(y=deg["curve"], title=f"{asset['name']} Capacity Fade",
                                          labels={"x": "Year", "y": "Remaining Capacity %"})
                        fig_deg.add_hline(y=0.80, line_dash="dash", line_color="red",
                                          annotation_text="Augmentation Trigger (80%)")
                        st.plotly_chart(fig_deg, use_container_width=True)
            else:
                st.info("No storage assets in portfolio.")

# ============================================================
# TAB 10: SCENARIO PLAYGROUND
# ============================================================
with tabs[9]:
    st.header("Scenario Comparison")

    if not st.session_state.portfolio:
        st.warning("Add assets to your portfolio first.")
    else:
        selected_scenarios = st.multiselect("Select Scenarios",
                                             list(SCENARIOS.keys()),
                                             default=list(SCENARIOS.keys())[:3])

        if selected_scenarios:
            scenario_results = []
            for name in selected_scenarios:
                sp = get_scenario_params(name, params)
                r = run_financial_model(st.session_state.portfolio, sp)
                ppa_m = calc_ppa_risk_metrics(st.session_state.portfolio,
                                              {"avg": sp["base_energy_price"]}, sp["projection_years"])
                scores = score_portfolio(st.session_state.portfolio, r, ppa_m)
                scenario_results.append({
                    "Scenario": name,
                    "NPV ($M)": round(r["npv"], 1),
                    "IRR (%)": round(r["irr"], 1) if r["irr"] else None,
                    "Payback (yr)": r["payback"],
                    "CAPEX ($M)": round(r["total_capex"], 1),
                    "Score": round(scores["Overall"], 1),
                    "Description": SCENARIOS[name]["description"],
                })

            sc_df = pd.DataFrame(scenario_results)
            st.dataframe(sc_df, use_container_width=True)

            fig_sc = px.bar(sc_df, x="Scenario", y="NPV ($M)",
                            color="NPV ($M)", color_continuous_scale=["red", "gray", "green"],
                            title="NPV by Scenario")
            st.plotly_chart(fig_sc, use_container_width=True)

        with st.expander("How Portfolio Scoring Works"):
            st.markdown(SCORING_METHODOLOGY)
