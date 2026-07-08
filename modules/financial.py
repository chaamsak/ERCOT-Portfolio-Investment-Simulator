# Financial forecast engine: NPV, IRR, Monte Carlo
# Co-authored with CoCo
import numpy as np
from scipy.optimize import brentq


def build_energy_prices(base_price, escalation, peak_ratio, volatility, gas_price, gas_escalation, years):
    """Build year-by-year energy price model."""
    prices = {}
    for y in range(1, years + 1):
        avg = base_price * (1 + escalation / 100) ** y
        peak = avg * peak_ratio
        offpeak = avg * 2 / peak_ratio
        spread = peak - offpeak
        spike_premium = avg * volatility * 0.3
        gas = gas_price * (1 + gas_escalation / 100) ** y
        prices[y] = {
            "avg": avg, "peak": peak, "offpeak": offpeak,
            "spread": spread, "spike_premium": spike_premium,
            "gas": gas,
        }
    return prices


def calc_asset_cashflow(asset, year, prices, carbon_price=0):
    """Calculate net cashflow for one asset in one year."""
    mw = asset["mw"]
    cf = asset["capacity_factor"]
    degradation = (1 - asset["degradation_pct_yr"] / 100) ** year
    fixed_om = mw * asset["fixed_om_per_kw_yr"] * 1000 / 1e6  # $M
    yr_prices = prices[year]
    mode = asset["revenue_mode"]

    if asset["type"] == "storage":
        if mode == "tolling":
            revenue = mw * asset["tolling_rate_kw_month"] * 12 * 1000 / 1e6 * degradation
        else:
            duration = asset["duration_hrs"]
            arbitrage = mw * duration * 365 * yr_prices["spread"] * asset["rte"] * 0.70 / 1e6
            spike_rev = 50 * mw * yr_prices["spike_premium"] * 0.70 / 1e6  # ~50 spike hours
            as_rev = mw * (asset["as_participation_pct"] / 100) * 15 * 8760 / 1e6  # $15/MW avg AS
            revenue = (arbitrage + spike_rev + as_rev) * degradation
        augmentation = 0
        if asset["augmentation_year"] > 0 and year == asset["augmentation_year"]:
            augmentation = mw * asset["duration_hrs"] * 1000 * asset["augmentation_cost_kwh"] / 1e6
        net = revenue - fixed_om - augmentation

    elif asset["type"] == "peaker":
        heat_rate = asset["heat_rate"]
        gas = yr_prices["gas"]
        marginal_cost = heat_rate * gas / 1e6 * 1000 + asset["var_om"]  # $/MWh
        dispatch_hours = cf * 8760
        energy_margin = max(0, yr_prices["avg"] * 1.3 - marginal_cost)
        if mode in ("physical_ppa", "hybrid"):
            ppa_pct = asset["ppa_pct_contracted"] / 100
            ppa_rev = mw * dispatch_hours * asset["ppa_price"] * ppa_pct / 1e6
            merch_rev = mw * dispatch_hours * energy_margin * (1 - ppa_pct) / 1e6
            revenue = ppa_rev + merch_rev
        elif mode == "tolling":
            revenue = mw * asset["tolling_rate_kw_month"] * 12 * 1000 / 1e6
        else:
            revenue = mw * dispatch_hours * energy_margin / 1e6
        # AS revenue for offline hours
        offline_frac = 1 - cf
        as_rev = mw * offline_frac * (asset["as_participation_pct"] / 100) * 5 * 8760 / 1e6
        carbon_cost = mw * dispatch_hours * asset["co2_per_mwh"] * carbon_price / 1e6
        net = revenue + as_rev - fixed_om - carbon_cost

    elif asset["type"] == "baseload":
        generation = mw * cf * 8760 * degradation
        heat_rate = asset["heat_rate"]
        gas = yr_prices["gas"]
        fuel_cost = generation * heat_rate * gas / 1e6 / 1e6
        var_om_cost = generation * asset["var_om"] / 1e6
        carbon_cost = generation * asset["co2_per_mwh"] * carbon_price / 1e6

        if mode == "physical_ppa":
            ppa_pct = asset["ppa_pct_contracted"] / 100
            curtail = asset["ppa_curtailment_allowance"] / 100
            ppa_rev = generation * ppa_pct * (1 - curtail) * asset["ppa_price"] * (1 + asset["ppa_escalation"] / 100) ** (year - 1) / 1e6
            merch_rev = generation * (1 - ppa_pct) * yr_prices["avg"] / 1e6
            revenue = ppa_rev + merch_rev
        elif mode == "vppa":
            revenue = generation * asset["ppa_price"] * (1 + asset["ppa_escalation"] / 100) ** (year - 1) / 1e6
            revenue -= generation * 2.0 * 0.5 / 1e6
        else:
            revenue = generation * yr_prices["avg"] / 1e6

        net = revenue - fuel_cost - var_om_cost - fixed_om - carbon_cost

    elif asset["type"] == "renewable":
        generation = mw * cf * 8760 * degradation
        if mode == "physical_ppa":
            ppa_pct = asset["ppa_pct_contracted"] / 100
            ppa_rev = generation * ppa_pct * asset["ppa_price"] * (1 + asset["ppa_escalation"] / 100) ** (year - 1) / 1e6
            merch_rev = generation * (1 - ppa_pct) * yr_prices["avg"] * 0.85 / 1e6
            revenue = ppa_rev + merch_rev
        elif mode == "vppa":
            revenue = generation * asset["ppa_price"] * (1 + asset["ppa_escalation"] / 100) ** (year - 1) / 1e6
            revenue -= generation * 2.0 * 0.3 / 1e6
        else:
            revenue = generation * yr_prices["avg"] * 0.85 / 1e6
        net = revenue - fixed_om

    elif asset["type"] == "flex":
        service_fee = mw * 50 * 1000 / 1e6  # $50/kW-yr
        events = 20
        event_rev = events * mw * yr_prices["peak"] * 4 / 1e6  # 4hr events
        net = service_fee + event_rev - fixed_om

    else:
        net = 0

    return net


def run_financial_model(portfolio, params):
    """Run full financial model for portfolio. Returns yearly cashflows and metrics."""
    years = params["projection_years"]
    discount_rate = params["discount_rate"] / 100
    carbon_price = params["carbon_price"]

    prices = build_energy_prices(
        params["base_energy_price"], params["energy_escalation"],
        params["peak_offpeak_ratio"], params["volatility_multiplier"],
        params["gas_price"], params["gas_escalation"], years
    )

    total_capex = sum(a["mw"] * a["capex_per_kw"] * 1000 / 1e6 for a in portfolio)

    yearly_data = []
    cumulative = -total_capex

    for y in range(1, years + 1):
        year_revenue = 0
        year_costs = 0
        asset_details = []
        for asset in portfolio:
            net = calc_asset_cashflow(asset, y, prices, carbon_price)
            year_revenue += max(0, net)
            year_costs += abs(min(0, net))
            asset_details.append({"name": asset["name"], "net": net})

        net_cf = sum(d["net"] for d in asset_details)
        if y == 1:
            net_cf -= total_capex

        cumulative += net_cf + (total_capex if y == 1 else 0)  # re-calc properly
        cumulative_actual = sum(
            sum(calc_asset_cashflow(a, yr, prices, carbon_price) for a in portfolio)
            for yr in range(1, y + 1)
        ) - total_capex

        yearly_data.append({
            "year": y, "net_cashflow": net_cf,
            "cumulative": cumulative_actual,
            "asset_details": asset_details,
            "prices": prices[y],
        })

    # NPV
    cashflows = [-total_capex] + [
        sum(calc_asset_cashflow(a, y, prices, carbon_price) for a in portfolio)
        for y in range(1, years + 1)
    ]
    npv = sum(cf / (1 + discount_rate) ** t for t, cf in enumerate(cashflows))

    # IRR
    try:
        irr = brentq(lambda r: sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows)), -0.5, 5.0) * 100
    except (ValueError, RuntimeError):
        irr = None

    # Payback
    cum = 0
    payback = None
    for i, cf in enumerate(cashflows):
        cum += cf
        if cum > 0:
            payback = i
            break

    return {
        "yearly_data": yearly_data,
        "npv": npv,
        "irr": irr,
        "payback": payback,
        "total_capex": total_capex,
        "cashflows": cashflows,
        "prices": prices,
    }


def run_monte_carlo(portfolio, params, n_simulations=1000):
    """Run Monte Carlo with random energy price variations."""
    results = []
    base_npv_params = params.copy()

    for _ in range(n_simulations):
        mc_params = params.copy()
        mc_params["base_energy_price"] = params["base_energy_price"] * np.random.lognormal(0, 0.15)
        mc_params["gas_price"] = params["gas_price"] * np.random.lognormal(0, 0.1)
        mc_params["volatility_multiplier"] = params["volatility_multiplier"] * np.random.uniform(0.5, 1.5)
        result = run_financial_model(portfolio, mc_params)
        results.append(result["npv"])

    results = sorted(results)
    return {
        "p10": np.percentile(results, 10),
        "p50": np.percentile(results, 50),
        "p90": np.percentile(results, 90),
        "mean": np.mean(results),
        "std": np.std(results),
        "all_npvs": results,
    }