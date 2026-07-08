# Market price analysis and visualizations
# Co-authored with CoCo
import numpy as np
import pandas as pd


def generate_synthetic_prices(days=90):
    """Generate synthetic ERCOT-like price data for development/fallback."""
    np.random.seed(42)
    hours = days * 24
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=hours, freq="h")

    base = 35 + 15 * np.sin(np.arange(hours) * 2 * np.pi / 24)  # diurnal
    seasonal = 10 * np.sin(np.arange(hours) * 2 * np.pi / (24 * 365))
    noise = np.random.normal(0, 8, hours)
    spikes = np.random.choice([0, 1], size=hours, p=[0.995, 0.005])
    spike_vals = spikes * np.random.uniform(100, 2000, hours)

    prices = np.maximum(base + seasonal + noise + spike_vals, -10)

    df = pd.DataFrame({"timestamp": timestamps, "lmp": prices})
    df["hour"] = df["timestamp"].dt.hour
    df["month"] = df["timestamp"].dt.month
    df["date"] = df["timestamp"].dt.date
    return df


def calc_price_duration_curve(df):
    """Sort prices highest to lowest."""
    return df["lmp"].sort_values(ascending=False).reset_index(drop=True)


def calc_hourly_profile(df):
    """Average price by hour of day."""
    return df.groupby("hour")["lmp"].mean()


def calc_spike_analysis(df):
    """Count intervals above various thresholds."""
    thresholds = [50, 100, 200, 500, 1000]
    return {f">${t}": (df["lmp"] > t).sum() for t in thresholds}


def calc_bess_arbitrage(df, duration_hrs=4, rte=0.87):
    """Implied daily BESS arbitrage revenue per MW."""
    daily = df.groupby("date")["lmp"].agg(["max", "min"])
    daily["spread"] = daily["max"] - daily["min"]
    daily["rev_per_mw"] = daily["spread"] * duration_hrs * rte
    return daily["rev_per_mw"]


def calc_price_heatmap(df):
    """Price heatmap by hour × month."""
    return df.pivot_table(values="lmp", index="hour", columns="month", aggfunc="mean")


def get_ppa_benchmark_prices():
    """Current market PPA benchmark prices by technology."""
    return {
        "Solar": {"low": 25, "mid": 32, "high": 40},
        "Wind": {"low": 20, "mid": 28, "high": 35},
        "CC (Baseload)": {"low": 45, "mid": 55, "high": 75},
        "RICE (Capacity $/kW-mo)": {"low": 8, "mid": 10, "high": 15},
        "BESS Tolling ($/kW-mo)": {"low": 6, "mid": 8, "high": 12},
    }