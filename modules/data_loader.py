# Data loader with gridstatusio API and synthetic fallback
# Co-authored with CoCo
import pandas as pd
import numpy as np
import os

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

try:
    from gridstatusio import GridStatusClient
    HAS_GRIDSTATUSIO = True
except ImportError:
    HAS_GRIDSTATUSIO = False

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ercot_cache.duckdb")
GRIDSTATUS_API_KEY = os.environ.get("GRIDSTATUS_API_KEY", "")


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
    source = "synthetic (gridstatus not available)"

    if HAS_DUCKDB and os.path.exists(CACHE_PATH):
        try:
            con = duckdb.connect(CACHE_PATH, read_only=True)
            df = con.execute(
                "SELECT * FROM lmp WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL ? DAY",
                [days]
            ).fetchdf()
            con.close()
            if len(df) > 100:
                if "zone" in df.columns:
                    df = df[df["zone"].isin(zone_ids)]
                df["_source"] = "live (cached)"
                return df
        except Exception:
            pass

    if HAS_GRIDSTATUSIO:
        try:
            client = GridStatusClient(GRIDSTATUS_API_KEY)
            end = pd.Timestamp.now(tz="US/Central")
            start = end - pd.Timedelta(days=days)
            df = client.get_dataset(
                dataset="ercot_lmp_by_settlement_point",
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                timezone="market",
            )
            # Filter to requested zones
            if "settlement_point" in df.columns:
                df = df[df["settlement_point"].isin(zone_ids)]
                df = df.rename(columns={"settlement_point": "zone", "interval_start": "timestamp"})
                # Find the LMP column
                lmp_col = next((c for c in df.columns if "lmp" in c.lower()), None)
                if lmp_col and lmp_col != "lmp":
                    df = df.rename(columns={lmp_col: "lmp"})
                df = df[["timestamp", "lmp", "zone"]].copy()
            elif "location" in df.columns:
                df = df[df["location"].isin(zone_ids)]
                df = df.rename(columns={"location": "zone"})
                lmp_col = next((c for c in df.columns if "lmp" in c.lower()), None)
                if lmp_col and lmp_col != "lmp":
                    df = df.rename(columns={lmp_col: "lmp"})
                if "interval_start" in df.columns:
                    df = df.rename(columns={"interval_start": "timestamp"})
                df = df[["timestamp", "lmp", "zone"]].copy()
            _cache_data(df)
            df["_source"] = "live (gridstatus.io API)"
            return df
        except Exception as e:
            source = f"synthetic (API error: {type(e).__name__}: {e})"

    df = _generate_synthetic(days, zone_ids)
    df["_source"] = source
    return df


def get_ercot_load(days=365):
    if HAS_GRIDSTATUSIO and GRIDSTATUS_API_KEY:
        try:
            client = GridStatusClient(GRIDSTATUS_API_KEY)
            end = pd.Timestamp.now(tz="US/Central")
            start = end - pd.Timedelta(days=days)
            df = client.get_dataset(
                dataset="ercot_load",
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                timezone="market",
            )
            if "interval_start" in df.columns:
                df = df.rename(columns={"interval_start": "timestamp"})
            load_col = next((c for c in df.columns if "load" in c.lower()), None)
            if load_col and load_col != "load_mw":
                df = df.rename(columns={load_col: "load_mw"})
            df["_source"] = "live (gridstatus.io API)"
            return df
        except Exception:
            pass
    df = _generate_synthetic_load(days)
    df["_source"] = "synthetic"
    return df


def get_ercot_as_prices(days=90):
    if HAS_GRIDSTATUSIO and GRIDSTATUS_API_KEY:
        try:
            client = GridStatusClient(GRIDSTATUS_API_KEY)
            end = pd.Timestamp.now(tz="US/Central")
            start = end - pd.Timedelta(days=days)
            df = client.get_dataset(
                dataset="ercot_mcpc_dam",
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                timezone="market",
            )
            if "interval_start" in df.columns:
                df = df.rename(columns={"interval_start": "timestamp"})
            df["_source"] = "live (gridstatus.io API)"
            return df
        except Exception:
            pass
    return _generate_synthetic_as_prices(days)


def get_ercot_fuel_mix(days=90):
    if HAS_GRIDSTATUSIO and GRIDSTATUS_API_KEY:
        try:
            client = GridStatusClient(GRIDSTATUS_API_KEY)
            end = pd.Timestamp.now(tz="US/Central")
            start = end - pd.Timedelta(days=days)
            df = client.get_dataset(
                dataset="ercot_fuel_mix",
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                timezone="market",
            )
            if "interval_start" in df.columns:
                df = df.rename(columns={"interval_start": "timestamp"})
            df["_source"] = "live (gridstatus.io API)"
            return df
        except Exception:
            pass
    return _generate_synthetic_fuel_mix(days)


def _cache_data(df):
    if not HAS_DUCKDB:
        return
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    try:
        con = duckdb.connect(CACHE_PATH)
        con.execute("CREATE TABLE IF NOT EXISTS lmp (timestamp TIMESTAMP, lmp DOUBLE)")
        con.execute("DELETE FROM lmp WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL 180 DAY")
        con.execute("INSERT INTO lmp SELECT * FROM df")
        con.close()
    except Exception:
        pass


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
        "reg_up": np.maximum(np.random.normal(20, 8, hours), 2),
        "reg_down": np.maximum(np.random.normal(12, 5, hours), 1),
        "rrs": np.maximum(np.random.normal(12, 6, hours), 1),
        "ecrs": np.maximum(np.random.normal(15, 7, hours), 1),
        "non_spin": np.maximum(np.random.normal(5, 3, hours), 0.5),
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
