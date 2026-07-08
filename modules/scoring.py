# 9-dimension portfolio scoring
# Co-authored with CoCo
import numpy as np


def clip(val, lo, hi):
    return max(lo, min(hi, val))


def score_portfolio(portfolio, financial_result, ppa_metrics):
    """Score portfolio on 9 dimensions (0-10 each)."""
    total_mw = sum(a["mw"] for a in portfolio)
    if total_mw == 0:
        return {dim: 0 for dim in ["financial", "speed", "reliability", "frequency",
                                    "emissions", "fuel_risk", "customer_fit",
                                    "regulatory", "revenue_certainty"]}

    # 1. Financial Return
    npv = financial_result["npv"]
    financial = clip(npv / 200 + 5, 0, 10)

    # 2. Speed to Deploy
    weighted_deploy = sum(a["mw"] * a["deploy_months"] for a in portfolio) / total_mw
    speed = clip(10 - weighted_deploy / 6, 0, 10)

    # 3. Reliability
    firm_mw = sum(a["mw"] for a in portfolio if a["type"] in ("storage", "peaker", "baseload"))
    reliability = firm_mw / total_mw * 10

    # 4. Frequency Support
    freq_mw = sum(a["mw"] for a in portfolio if a["response_time_s"] <= 2)
    frequency = min(10, freq_mw / total_mw * 12)

    # 5. Emissions
    total_co2 = sum(a["mw"] * a["capacity_factor"] * 8760 * a["co2_per_mwh"] for a in portfolio) / 1e6
    if total_co2 == 0:
        emissions = 10
    elif total_co2 < 0.5:
        emissions = 8
    elif total_co2 < 2:
        emissions = 6
    elif total_co2 < 5:
        emissions = 4
    elif total_co2 < 10:
        emissions = 2
    else:
        emissions = 0

    # 6. Fuel Risk
    gas_gen = sum(a["mw"] * a["capacity_factor"] for a in portfolio if a["heat_rate"] > 0)
    total_gen = sum(a["mw"] * a["capacity_factor"] for a in portfolio)
    fuel_risk = 10 - (gas_gen / total_gen * 10) if total_gen > 0 else 10

    # 7. Customer Fit
    freq_total = sum(a["mw"] for a in portfolio if a["response_time_s"] <= 2)
    customer_fit = min(10, (firm_mw + freq_total) / total_mw * 6)
    has_storage = any(a["type"] == "storage" for a in portfolio)
    if has_storage:
        customer_fit += 2
    if total_mw > 2000:
        customer_fit += 1
    customer_fit = min(10, customer_fit)

    # 8. Regulatory Compliance
    regulatory = 5.0
    if has_storage:
        regulatory += 3
    if firm_mw > 1000:
        regulatory += 2
    if total_co2 > 5:
        regulatory -= 2
    if weighted_deploy > 60:
        regulatory -= 1
    regulatory = clip(regulatory, 0, 10)

    # 9. Revenue Certainty
    contracted_pct = ppa_metrics.get("contracted_pct", 0)
    revenue_certainty = contracted_pct / 10
    if ppa_metrics.get("max_concentration", 0) > 40:
        revenue_certainty -= 1
    revenue_certainty = clip(revenue_certainty, 0, 10)

    scores = {
        "Financial Return": financial,
        "Speed to Deploy": speed,
        "Reliability": reliability,
        "Frequency Support": frequency,
        "Emissions": emissions,
        "Fuel Risk": fuel_risk,
        "Customer Fit": customer_fit,
        "Regulatory": regulatory,
        "Revenue Certainty": revenue_certainty,
    }
    scores["Overall"] = np.mean(list(scores.values()))
    return scores


SCORING_METHODOLOGY = """
**Portfolio Scoring Methodology (0-10 each dimension):**

1. **Financial Return**: CLIP(NPV_$M / 200 + 5, 0, 10)
2. **Speed to Deploy**: CLIP(10 - weighted_avg_deploy_months / 6, 0, 10)
3. **Reliability**: firm_MW / total_MW × 10
4. **Frequency Support**: MIN(10, freq_response_MW / total_MW × 12)
5. **Emissions**: 0 tons→10, <0.5M→8, <2M→6, <5M→4, <10M→2, >10M→0
6. **Fuel Risk**: 10 - (gas_gen / total_gen × 10)
7. **Customer Fit**: MIN(10, (firm+freq)/total × 6) + bonuses
8. **Regulatory**: Base 5, +3 storage, +2 firm>1GW, -2 high CO2
9. **Revenue Certainty**: contracted_revenue_% / 10, -1 for concentration risk
"""