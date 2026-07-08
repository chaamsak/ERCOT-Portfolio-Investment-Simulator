# PPA structuring, revenue calculation, MTM, and optimization
# Co-authored with CoCo
import numpy as np


def calc_ppa_revenue_asset(asset, year, energy_prices):
    """Calculate revenue for a single asset in a single year based on its revenue mode."""
    mw = asset["mw"]
    cf = asset["capacity_factor"]
    mode = asset["revenue_mode"]
    ppa_price = asset["ppa_price"]
    escalation = asset["ppa_escalation"] / 100
    pct_contracted = asset["ppa_pct_contracted"] / 100
    curtailment = asset["ppa_curtailment_allowance"] / 100
    degradation = (1 - asset["degradation_pct_yr"] / 100) ** year

    avg_price = energy_prices.get("avg", 40)
    generation = mw * cf * 8760 * degradation  # MWh

    if mode == "physical_ppa":
        contracted_gen = generation * pct_contracted * (1 - curtailment)
        ppa_rev = contracted_gen * ppa_price * (1 + escalation) ** (year - 1) / 1e6
        merchant_gen = generation * (1 - pct_contracted)
        merchant_rev = merchant_gen * avg_price / 1e6
        return {"ppa_revenue": ppa_rev, "merchant_revenue": merchant_rev,
                "total_revenue": ppa_rev + merchant_rev, "generation_mwh": generation}

    elif mode == "vppa":
        vppa_rev = generation * ppa_price * (1 + escalation) ** (year - 1) / 1e6
        basis_cost = generation * 2.0 * 0.5 / 1e6  # $2/MWh basis differential
        return {"ppa_revenue": vppa_rev - basis_cost, "merchant_revenue": 0,
                "total_revenue": vppa_rev - basis_cost, "generation_mwh": generation}

    elif mode == "tolling":
        tolling_rev = mw * asset["tolling_rate_kw_month"] * 12 * 1000 / 1e6 * degradation
        return {"ppa_revenue": tolling_rev, "merchant_revenue": 0,
                "total_revenue": tolling_rev, "generation_mwh": generation}

    elif mode == "hybrid":
        contracted_gen = generation * pct_contracted * (1 - curtailment)
        ppa_rev = contracted_gen * ppa_price * (1 + escalation) ** (year - 1) / 1e6
        merchant_gen = generation * (1 - pct_contracted)
        merchant_rev = merchant_gen * avg_price / 1e6
        return {"ppa_revenue": ppa_rev, "merchant_revenue": merchant_rev,
                "total_revenue": ppa_rev + merchant_rev, "generation_mwh": generation}

    else:  # merchant
        total_rev = generation * avg_price / 1e6
        return {"ppa_revenue": 0, "merchant_revenue": total_rev,
                "total_revenue": total_rev, "generation_mwh": generation}


def calc_ppa_risk_metrics(portfolio, energy_prices, projection_years=20):
    """Calculate portfolio-level PPA risk metrics."""
    total_ppa_rev = 0
    total_rev = 0
    tenors = []
    buyer_revenue = {}

    for asset in portfolio:
        for y in range(1, projection_years + 1):
            rev = calc_ppa_revenue_asset(asset, y, energy_prices)
            total_ppa_rev += rev["ppa_revenue"]
            total_rev += rev["total_revenue"]

        if asset["revenue_mode"] != "merchant":
            tenors.append(asset["ppa_tenor"])
            buyer = asset["ppa_buyer_type"]
            buyer_revenue[buyer] = buyer_revenue.get(buyer, 0) + rev["total_revenue"]

    contracted_pct = (total_ppa_rev / total_rev * 100) if total_rev > 0 else 0
    avg_tenor = np.mean(tenors) if tenors else 0
    max_concentration = (max(buyer_revenue.values()) / total_rev * 100) if buyer_revenue and total_rev > 0 else 0

    # Credit-weighted revenue
    credit_weights = {"Investment Grade (IG)": 1.0, "Sub-IG": 0.8, "Unrated": 0.6}
    credit_weighted = sum(
        rev["total_revenue"] * credit_weights.get(a["ppa_credit_quality"], 0.6)
        for a in portfolio
        for rev in [calc_ppa_revenue_asset(a, 1, energy_prices)]
        if a["revenue_mode"] != "merchant"
    )

    return {
        "contracted_pct": contracted_pct,
        "avg_tenor": avg_tenor,
        "max_concentration": max_concentration,
        "credit_weighted_revenue": credit_weighted,
        "total_ppa_revenue": total_ppa_rev,
        "total_revenue": total_rev,
    }


def calc_mark_to_market(portfolio, current_market_price, remaining_years=15):
    """Calculate MTM for each PPA in the portfolio."""
    mtm_results = []
    for asset in portfolio:
        if asset["revenue_mode"] == "merchant":
            mtm_results.append({"name": asset["name"], "mtm": 0, "mw": asset["mw"]})
            continue
        gen_per_year = asset["mw"] * asset["capacity_factor"] * 8760
        remaining_gen = gen_per_year * min(asset["ppa_tenor"], remaining_years)
        mtm = (asset["ppa_price"] - current_market_price) * remaining_gen / 1e6
        mtm_results.append({"name": asset["name"], "mtm": mtm, "mw": asset["mw"]})
    return mtm_results


def optimize_ppa_mix(portfolio, energy_prices, max_volatility, projection_years=20, n_simulations=500):
    """Find optimal PPA % per asset to maximize NPV subject to volatility constraint."""
    best_config = {}
    # Simple heuristic optimization: try different contracted percentages
    for asset in portfolio:
        best_npv = -np.inf
        best_pct = 0
        for pct in range(0, 105, 5):
            test_asset = asset.copy()
            test_asset["ppa_pct_contracted"] = pct
            revenues = []
            for y in range(1, projection_years + 1):
                rev = calc_ppa_revenue_asset(test_asset, y, energy_prices)
                revenues.append(rev["total_revenue"])
            npv = sum(r / (1.08) ** i for i, r in enumerate(revenues, 1))
            vol = np.std(revenues)
            if vol <= max_volatility and npv > best_npv:
                best_npv = npv
                best_pct = pct
        best_config[asset["name"]] = best_pct
    return best_config