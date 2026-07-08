# Portfolio asset definitions and templates
# Co-authored with CoCo

ASSET_TEMPLATES = {
    "BESS (4hr)": {
        "type": "storage", "mw": 200, "duration_hrs": 4,
        "capex_per_kw": 1450, "fixed_om_per_kw_yr": 25,
        "rte": 0.87, "degradation_pct_yr": 2.5, "augmentation_year": 10,
        "augmentation_cost_kwh": 40, "deploy_months": 18,
        "response_time_s": 0.1, "inertia_constant_s": 0,
        "synthetic_inertia": True, "as_participation_pct": 50,
        "heat_rate": 0, "var_om": 0, "co2_per_mwh": 0,
        "capacity_factor": 0.85,
        "revenue_mode": "merchant", "ppa_price": 0, "ppa_escalation": 1.5,
        "ppa_tenor": 15, "ppa_pct_contracted": 100, "ppa_start_year": 1,
        "ppa_buyer_type": "Data Center", "ppa_credit_quality": "Investment Grade (IG)",
        "ppa_curtailment_allowance": 5, "ppa_shape_requirement": "Flat (24x7)",
        "tolling_rate_kw_month": 8,
    },
    "BESS (2hr)": {
        "type": "storage", "mw": 100, "duration_hrs": 2,
        "capex_per_kw": 1100, "fixed_om_per_kw_yr": 22,
        "rte": 0.89, "degradation_pct_yr": 2.0, "augmentation_year": 12,
        "augmentation_cost_kwh": 35, "deploy_months": 14,
        "response_time_s": 0.1, "inertia_constant_s": 0,
        "synthetic_inertia": True, "as_participation_pct": 60,
        "heat_rate": 0, "var_om": 0, "co2_per_mwh": 0,
        "capacity_factor": 0.90,
        "revenue_mode": "merchant", "ppa_price": 0, "ppa_escalation": 1.5,
        "ppa_tenor": 15, "ppa_pct_contracted": 100, "ppa_start_year": 1,
        "ppa_buyer_type": "Data Center", "ppa_credit_quality": "Investment Grade (IG)",
        "ppa_curtailment_allowance": 5, "ppa_shape_requirement": "Flat (24x7)",
        "tolling_rate_kw_month": 6,
    },
    "Combined Cycle (CC)": {
        "type": "baseload", "mw": 500, "duration_hrs": 0,
        "capex_per_kw": 1200, "fixed_om_per_kw_yr": 35,
        "rte": 1.0, "degradation_pct_yr": 0.3, "augmentation_year": 0,
        "augmentation_cost_kwh": 0, "deploy_months": 36,
        "response_time_s": 600, "inertia_constant_s": 5.0,
        "synthetic_inertia": False, "as_participation_pct": 10,
        "heat_rate": 6800, "var_om": 3.5, "co2_per_mwh": 0.37,
        "capacity_factor": 0.85,
        "revenue_mode": "physical_ppa", "ppa_price": 55, "ppa_escalation": 2.0,
        "ppa_tenor": 20, "ppa_pct_contracted": 80, "ppa_start_year": 1,
        "ppa_buyer_type": "Data Center", "ppa_credit_quality": "Investment Grade (IG)",
        "ppa_curtailment_allowance": 3, "ppa_shape_requirement": "Baseload",
        "tolling_rate_kw_month": 0,
    },
    "RICE Peaker": {
        "type": "peaker", "mw": 200, "duration_hrs": 0,
        "capex_per_kw": 950, "fixed_om_per_kw_yr": 20,
        "rte": 1.0, "degradation_pct_yr": 0.5, "augmentation_year": 0,
        "augmentation_cost_kwh": 0, "deploy_months": 22,
        "response_time_s": 5, "inertia_constant_s": 1.5,
        "synthetic_inertia": False, "as_participation_pct": 30,
        "heat_rate": 8200, "var_om": 5.0, "co2_per_mwh": 0.45,
        "capacity_factor": 0.20,
        "revenue_mode": "merchant", "ppa_price": 10, "ppa_escalation": 1.5,
        "ppa_tenor": 10, "ppa_pct_contracted": 100, "ppa_start_year": 1,
        "ppa_buyer_type": "Municipal Utility", "ppa_credit_quality": "Investment Grade (IG)",
        "ppa_curtailment_allowance": 5, "ppa_shape_requirement": "On-Peak only",
        "tolling_rate_kw_month": 10,
    },
    "Solar": {
        "type": "renewable", "mw": 300, "duration_hrs": 0,
        "capex_per_kw": 1050, "fixed_om_per_kw_yr": 12,
        "rte": 1.0, "degradation_pct_yr": 0.5, "augmentation_year": 0,
        "augmentation_cost_kwh": 0, "deploy_months": 14,
        "response_time_s": 999, "inertia_constant_s": 0,
        "synthetic_inertia": False, "as_participation_pct": 0,
        "heat_rate": 0, "var_om": 0, "co2_per_mwh": 0,
        "capacity_factor": 0.26,
        "revenue_mode": "physical_ppa", "ppa_price": 32, "ppa_escalation": 1.0,
        "ppa_tenor": 15, "ppa_pct_contracted": 100, "ppa_start_year": 1,
        "ppa_buyer_type": "Corporate (ESG)", "ppa_credit_quality": "Investment Grade (IG)",
        "ppa_curtailment_allowance": 5, "ppa_shape_requirement": "Solar-shaped",
        "tolling_rate_kw_month": 0,
    },
    "Wind": {
        "type": "renewable", "mw": 250, "duration_hrs": 0,
        "capex_per_kw": 1350, "fixed_om_per_kw_yr": 15,
        "rte": 1.0, "degradation_pct_yr": 0.4, "augmentation_year": 0,
        "augmentation_cost_kwh": 0, "deploy_months": 24,
        "response_time_s": 999, "inertia_constant_s": 0,
        "synthetic_inertia": False, "as_participation_pct": 0,
        "heat_rate": 0, "var_om": 0, "co2_per_mwh": 0,
        "capacity_factor": 0.35,
        "revenue_mode": "vppa", "ppa_price": 28, "ppa_escalation": 1.5,
        "ppa_tenor": 15, "ppa_pct_contracted": 100, "ppa_start_year": 1,
        "ppa_buyer_type": "Corporate (ESG)", "ppa_credit_quality": "Investment Grade (IG)",
        "ppa_curtailment_allowance": 5, "ppa_shape_requirement": "Wind-shaped",
        "tolling_rate_kw_month": 0,
    },
    "Flex/DR": {
        "type": "flex", "mw": 50, "duration_hrs": 0,
        "capex_per_kw": 200, "fixed_om_per_kw_yr": 10,
        "rte": 1.0, "degradation_pct_yr": 0, "augmentation_year": 0,
        "augmentation_cost_kwh": 0, "deploy_months": 6,
        "response_time_s": 30, "inertia_constant_s": 0,
        "synthetic_inertia": False, "as_participation_pct": 80,
        "heat_rate": 0, "var_om": 0, "co2_per_mwh": 0,
        "capacity_factor": 0.10,
        "revenue_mode": "merchant", "ppa_price": 50, "ppa_escalation": 2.0,
        "ppa_tenor": 5, "ppa_pct_contracted": 100, "ppa_start_year": 1,
        "ppa_buyer_type": "Industrial", "ppa_credit_quality": "Sub-IG",
        "ppa_curtailment_allowance": 10, "ppa_shape_requirement": "On-Peak only",
        "tolling_rate_kw_month": 0,
    },
}

PORTFOLIO_TEMPLATES = {
    "Balanced 2GW": [
        {"template": "BESS (4hr)", "mw": 400},
        {"template": "Combined Cycle (CC)", "mw": 700},
        {"template": "RICE Peaker", "mw": 300},
        {"template": "Solar", "mw": 400},
        {"template": "Wind", "mw": 200},
    ],
    "Storage Heavy": [
        {"template": "BESS (4hr)", "mw": 800},
        {"template": "BESS (2hr)", "mw": 400},
        {"template": "Solar", "mw": 500},
        {"template": "RICE Peaker", "mw": 200},
    ],
    "Thermal Dominant": [
        {"template": "Combined Cycle (CC)", "mw": 1200},
        {"template": "RICE Peaker", "mw": 500},
        {"template": "BESS (4hr)", "mw": 200},
    ],
    "Renewables + Storage": [
        {"template": "Solar", "mw": 600},
        {"template": "Wind", "mw": 400},
        {"template": "BESS (4hr)", "mw": 500},
        {"template": "Flex/DR", "mw": 100},
    ],
}


def create_asset(template_name, overrides=None):
    asset = ASSET_TEMPLATES[template_name].copy()
    asset["name"] = template_name
    if overrides:
        asset.update(overrides)
    return asset


def load_portfolio_template(template_name):
    portfolio = []
    for item in PORTFOLIO_TEMPLATES[template_name]:
        asset = create_asset(item["template"], {"mw": item["mw"]})
        portfolio.append(asset)
    return portfolio


def get_total_mw(portfolio):
    return sum(a["mw"] for a in portfolio)


def get_total_capex(portfolio):
    return sum(a["mw"] * a["capex_per_kw"] * 1000 / 1e6 for a in portfolio)