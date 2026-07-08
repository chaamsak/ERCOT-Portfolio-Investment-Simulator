# Transmission, congestion, and interconnection costs
# Co-authored with CoCo


def calc_congestion_cost(portfolio, bus_zone_differential=2.5):
    """Estimate congestion costs based on bus vs zone price differential."""
    results = []
    for asset in portfolio:
        gen = asset["mw"] * asset["capacity_factor"] * 8760
        cost = gen * bus_zone_differential / 1e6  # $M/yr
        results.append({"name": asset["name"], "congestion_cost_M": cost, "mw": asset["mw"]})
    return results


def calc_interconnection_costs(portfolio, network_upgrade_pct=50):
    """Estimate interconnection costs per asset."""
    results = []
    for asset in portfolio:
        mw = asset["mw"]
        screening = 0.075  # $M
        fis = 0.350
        # Network upgrades scale with MW, with user-adjustable severity
        network = mw * 0.05 * (network_upgrade_pct / 100)  # $M, simplified
        facilities = mw * 0.025
        substation = 15 if mw > 100 else 5

        total = screening + fis + network + facilities + substation
        results.append({
            "name": asset["name"], "mw": mw,
            "screening": screening, "fis": fis,
            "network_upgrades": network, "facilities": facilities,
            "substation": substation, "total": total,
        })
    return results


def calc_basis_risk(portfolio, zone_differential=3.0):
    """Calculate basis risk for VPPAs (delivery vs settlement point difference)."""
    results = []
    for asset in portfolio:
        if asset["revenue_mode"] == "vppa":
            gen = asset["mw"] * asset["capacity_factor"] * 8760
            basis_cost = gen * zone_differential / 1e6
            results.append({"name": asset["name"], "basis_cost_M_yr": basis_cost})
    return results