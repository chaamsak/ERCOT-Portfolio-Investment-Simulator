# Scenario comparison engine
# Co-authored with CoCo


SCENARIOS = {
    "A: Conservative": {
        "gas_price": 3.50, "gas_escalation": 0, "base_energy_price": 35,
        "energy_escalation": 0, "carbon_price": 0, "volatility_multiplier": 0.8,
        "peak_offpeak_ratio": 1.5, "description": "Flat gas, low energy, no carbon",
    },
    "B: Base Case": {
        "gas_price": 3.50, "gas_escalation": 2, "base_energy_price": 40,
        "energy_escalation": 2, "carbon_price": 0, "volatility_multiplier": 1.0,
        "peak_offpeak_ratio": 1.8, "description": "Moderate growth, no carbon",
    },
    "C: High Energy": {
        "gas_price": 4.50, "gas_escalation": 3, "base_energy_price": 60,
        "energy_escalation": 3, "carbon_price": 0, "volatility_multiplier": 1.5,
        "peak_offpeak_ratio": 2.2, "description": "High gas, high energy, volatile",
    },
    "D: Low Energy": {
        "gas_price": 2.50, "gas_escalation": 1, "base_energy_price": 25,
        "energy_escalation": 1, "carbon_price": 0, "volatility_multiplier": 0.6,
        "peak_offpeak_ratio": 1.3, "description": "Low prices — PPAs very valuable",
    },
    "E: Carbon Tax": {
        "gas_price": 4.00, "gas_escalation": 2, "base_energy_price": 50,
        "energy_escalation": 2.5, "carbon_price": 50, "volatility_multiplier": 1.2,
        "peak_offpeak_ratio": 1.8, "description": "$50/ton CO2, renewables+storage win",
    },
    "F: Supply Stress": {
        "gas_price": 5.00, "gas_escalation": 4, "base_energy_price": 55,
        "energy_escalation": 3, "carbon_price": 0, "volatility_multiplier": 2.0,
        "peak_offpeak_ratio": 2.5, "description": "12-month delays, tariffs +30%",
    },
}


def get_scenario_params(scenario_name, base_params):
    """Merge scenario overrides into base parameters."""
    scenario = SCENARIOS[scenario_name]
    merged = base_params.copy()
    for key in ["gas_price", "gas_escalation", "base_energy_price",
                "energy_escalation", "carbon_price", "volatility_multiplier",
                "peak_offpeak_ratio"]:
        if key in scenario:
            merged[key] = scenario[key]
    return merged