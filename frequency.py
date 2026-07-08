# Frequency response and grid stability simulation
# Co-authored with CoCo
import numpy as np


def calc_portfolio_inertia(portfolio):
    physical = sum(a["mw"] * a["inertia_constant_s"] for a in portfolio if a["inertia_constant_s"] > 0)
    synthetic = sum(a["mw"] * 2.0 for a in portfolio if a.get("synthetic_inertia", False))
    return {"physical_mw_s": physical, "synthetic_mw_s": synthetic, "total_mw_s": physical + synthetic}


def simulate_frequency_event(portfolio, trip_mw, system_inertia_gw_s=150):
    total_inertia = system_inertia_gw_s * 1000
    portfolio_inertia = calc_portfolio_inertia(portfolio)["total_mw_s"]
    effective_inertia = total_inertia + portfolio_inertia
    rocof = trip_mw / (2 * effective_inertia) * 60

    dt = 0.1
    times = np.arange(0, 30, dt)
    freq = np.zeros_like(times)
    freq[0] = 60.0
    response_active = {i: False for i in range(len(portfolio))}

    for t_idx in range(1, len(times)):
        t = times[t_idx]
        decline = rocof * dt
        response_mw = 0

        for i, asset in enumerate(portfolio):
            if t >= asset["response_time_s"] and not response_active[i]:
                response_active[i] = True
            if response_active[i]:
                response_mw += asset["mw"] * min(1.0, (t - asset["response_time_s"]) / 5.0)

        arrest_effect = response_mw / effective_inertia * 60 * dt * 0.5
        freq[t_idx] = freq[t_idx - 1] - decline + arrest_effect
        freq[t_idx] = max(freq[t_idx], 57.0)

    nadir = freq.min()
    nadir_time = times[freq.argmin()]

    return {
        "times": times.tolist(),
        "frequency": freq.tolist(),
        "rocof": rocof,
        "nadir": nadir,
        "nadir_time": nadir_time,
        "portfolio_inertia": portfolio_inertia,
    }


def calc_as_revenue(portfolio, prices=None):
    if prices is None:
        prices = {"reg_up": 20, "rrs": 12, "ffr": 25, "nonspin": 5, "ecrs": 15}

    results = []
    for asset in portfolio:
        participation = asset["as_participation_pct"] / 100
        mw = asset["mw"]
        if asset["response_time_s"] <= 0.5:
            rev = mw * participation * (prices["ffr"] * 4000 + prices["reg_up"] * 2000 + prices["rrs"] * 2000) / 1e6
            services = "FFR, RegUp, RRS"
        elif asset["response_time_s"] <= 5:
            rev = mw * participation * (prices["reg_up"] * 3000 + prices["rrs"] * 3000 + prices["ecrs"] * 2000) / 1e6
            services = "RegUp, RRS, ECRS"
        elif asset["response_time_s"] <= 600:
            rev = mw * participation * (prices["nonspin"] * 6000 + prices["ecrs"] * 2000) / 1e6
            services = "NonSpin, ECRS"
        else:
            rev = 0
            services = "None"
        results.append({"name": asset["name"], "revenue_M": rev, "services": services, "mw": mw})
    return results
