# Data loader reading ERCOT market data from CSV files exported from Snowflake
# Co-authored with CoCo
import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

ERCOT_ZONES = [
    "LZ_SOUTH (LCRA)",
    "LZ_WEST",
    "LZ_NORTH",
    "LZ_HOUSTON",
    "HB_SOUTH",
    "HB_NORTH",
    "HB_WEST",
    "HB_HOUSTON",
]


def _zone_label_to_id(label):
    return label.split(" (")[0]


def get_ercot_lmp(days=90, zones=None):
    if zones is None:
        zones = ["LZ_SOUTH"]
    zone_ids = [_zone_label_to_id(z) for z in zones]

    csv_path = os.path.join(DATA_DIR, "ercot_lmp.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            df = df[df["zone"].isin(zone_ids)]
            if days:
                cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
                df = df[df["timestamp"] >= cutoff]
            df["_source"] = "live (CSV export from Snowflake)"
            return df
        except Exception as e:
            source = f"synthetic (CSV read error: {e})"
    else:
        source = f"synthetic (CSV not found at: {os.path.abspath(csv_path)})"

    df = _generate_synthetic(days, zone_ids)
    df["_source"] = source
    return df


def get_ercot_load(days=365):
    csv_path = os.path.join(DATA_DIR, "ercot_load.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            if days:
                cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
                df = df[df["timestamp"] >= cutoff]
            df["_source"] = "live (CSV export from Snowflake)"
            return df
        except Exception:
            pass
    df = _generate_synthetic_load(days)
    df["_source"] = "synthetic"
    return df


def get_ercot_as_prices(days=90):
    csv_path = os.path.join(DATA_DIR, "ercot_as_prices.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            if days:
                cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
                df = df[df["timestamp"] >= cutoff]
            df["_source"] = "live (CSV export from Snowflake)"
            return df
        except Exception:
            pass
    return _generate_synthetic_as_prices(days)


def get_ercot_fuel_mix(days=90):
    csv_path = os.path.join(DATA_DIR, "ercot_fuel_mix.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            if days:
                cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
                df = df[df["timestamp"] >= cutoff]
            df["_source"] = "live (CSV export from Snowflake)"
            return df
        except Exception:
            pass
    return _generate_synthetic_fuel_mix(days)


# --- Synthetic fallbacks ---

def _generate_synthetic(days, zone_ids=None):
    if zone_ids is None:
        zone_ids = ["LZ_SOUTH"]
    np.random.seed(42)
    hours = days * 24
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=hours, freq="h")
    all_dfs = []
    zone_offsets = {"LZ_SOUTH": 0, "LZ_WEST": -3, "LZ_NORTH": 2, "LZ_HOUSTON": 4,
                    "HB_SOUTH": 1, "HB_NORTH": 3, "HB_WEST": -2, "HB_HOUSTON": 5}
    for zone_id in zone_ids:
        offset = zone_offsets.get(zone_id, 0)
        base = (35 + offset) + 15 * np.sin(np.arange(hours) * 2 * np.pi / 24)
        seasonal = 10 * np.sin(np.arange(hours) * 2 * np.pi / (24 * 365))
        noise = np.random.normal(0, 8, hours)
        spikes = np.random.choice([0, 1], size=hours, p=[0.995, 0.005])
        spike_vals = spikes * np.random.uniform(100, 2000, hours)
        prices = np.maximum(base + seasonal + noise + spike_vals, -10)
        zone_df = pd.DataFrame({"timestamp": timestamps, "lmp": prices, "zone": zone_id})
        all_dfs.append(zone_df)
    return pd.concat(all_dfs, ignore_index=True)


def _generate_synthetic_load(days):
    np.random.seed(123)
    hours = days * 24
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=hours, freq="h")
    base_load = 45000
    diurnal = 8000 * np.sin((np.arange(hours) - 6) * 2 * np.pi / 24)
    seasonal = 12000 * np.sin((np.arange(hours) / 24 - 30) * 2 * np.pi / 365)
    noise = np.random.normal(0, 2000, hours)
    load = base_load + diurnal + seasonal + noise
    return pd.DataFrame({"timestamp": timestamps, "load_mw": np.maximum(load, 20000)})


def _generate_synthetic_as_prices(days):
    np.random.seed(77)
    hours = days * 24
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=hours, freq="h")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "regup": np.maximum(np.random.normal(20, 8, hours), 2),
        "regdn": np.maximum(np.random.normal(12, 5, hours), 1),
        "rrs": np.maximum(np.random.normal(12, 6, hours), 1),
        "ecrs": np.maximum(np.random.normal(15, 7, hours), 1),
        "nspin": np.maximum(np.random.normal(5, 3, hours), 0.5),
    })
    df["_source"] = "synthetic"
    return df


def _generate_synthetic_fuel_mix(days):
    np.random.seed(99)
    hours = days * 24
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=hours, freq="h")
    solar_shape = np.maximum(np.sin((np.arange(hours) % 24 - 6) * np.pi / 12), 0)
    df = pd.DataFrame({
        "timestamp": timestamps,
        "gas": 25000 + np.random.normal(0, 3000, hours),
        "wind": 8000 + np.random.normal(0, 4000, hours),
        "solar": 12000 * solar_shape + np.random.normal(0, 500, hours),
        "nuclear": np.full(hours, 5100.0),
        "coal": 3000 + np.random.normal(0, 500, hours),
        "hydro": 500 + np.random.normal(0, 100, hours),
        "other": 1000 + np.random.normal(0, 200, hours),
    })
    for col in ["gas", "wind", "solar", "coal", "hydro", "other"]:
        df[col] = np.maximum(df[col], 0)
    df["_source"] = "synthetic"
    return df
