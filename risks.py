# Engineering risk calculations for thermal derating, gas supply, emissions
# Co-authored with CoCo
import numpy as np


def calc_thermal_derating(portfolio, peak_temp_f=105):
    iso_temp = 59
    rates = {"baseload": 0.0015, "peaker": 0.0010, "storage": 0.005}
    temp_thresholds = {"baseload": iso_temp, "peaker": iso_temp, "storage": 85}

    results = []
    for asset in portfolio:
        rate = rates.get(asset["type"], 0)
        threshold = temp_thresholds.get(asset["type"], iso_temp)
        effective_delta = max(0, peak_temp_f - threshold)
        derate_pct = effective_delta * rate * 100
        available_mw = asset["mw"] * (1 - derate_pct / 100)
        results.append({
            "name": asset["name"], "rated_mw": asset["mw"],
            "derate_pct": derate_pct, "available_mw": available_mw,
            "type": asset["type"],
        })
    return results


def calc_gas_supply_risk(portfolio, curtailment_days=5, gas_fraction_at_risk=0.3):
    results = []
    for asset in portfolio:
        if asset["heat_rate"] > 0:
            daily_rev = asset["mw"] * asset["capacity_factor"] * 24 * 40 / 1e6
            at_risk = daily_rev * curtailment_days * gas_fraction_at_risk
            results.append({"name": asset["name"], "revenue_at_risk_M": at_risk})
    return results


def calc_emissions(portfolio):
    results = []
    total = 0
    for asset in portfolio:
        co2 = asset["mw"] * asset["capacity_factor"] * 8760 * asset["co2_per_mwh"]
        results.append({"name": asset["name"], "co2_tons_yr": co2, "type": asset["type"]})
        total += co2
    return results, total


def calc_supply_chain_delays(portfolio, delay_months=0, tariff_surcharge_pct=0):
    results = []
    for asset in portfolio:
        base_deploy = asset["deploy_months"]
        actual_deploy = base_deploy + delay_months
        annual_rev = asset["mw"] * asset["capacity_factor"] * 8760 * 40 / 1e6
        rev_lost = annual_rev * delay_months / 12
        tariff_cost = 0
        if asset["type"] == "storage" and tariff_surcharge_pct > 0:
            capex = asset["mw"] * asset["capex_per_kw"] * 1000 / 1e6
            tariff_cost = capex * tariff_surcharge_pct / 100
        results.append({
            "name": asset["name"], "base_months": base_deploy,
            "actual_months": actual_deploy, "revenue_lost_M": rev_lost,
            "tariff_cost_M": tariff_cost,
        })
    return results


def calc_battery_degradation(asset, years=20):
    if asset["type"] != "storage":
        return None
    annual_deg = asset["degradation_pct_yr"] / 100
    curve = [(1 - annual_deg) ** y for y in range(years + 1)]
    augmentation_trigger = 0.80
    augmentation_year = next((y for y, c in enumerate(curve) if c <= augmentation_trigger), None)
    return {"curve": curve, "augmentation_year": augmentation_year}


def calc_forced_outage(portfolio):
    for_rates = {"storage": 0.02, "peaker": 0.05, "baseload": 0.04, "renewable": 0.03, "flex": 0.01}
    results = []
    for asset in portfolio:
        for_rate = for_rates.get(asset["type"], 0.03)
        annual_rev = asset["mw"] * asset["capacity_factor"] * 8760 * 40 / 1e6
        at_risk = annual_rev * for_rate
        results.append({"name": asset["name"], "for_pct": for_rate * 100, "rev_at_risk_M": at_risk})
    return results
