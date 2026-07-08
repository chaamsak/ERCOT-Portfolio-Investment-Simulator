# Data loader with gridstatus integration and synthetic fallback
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
    import gridstatus
    HAS_GRIDSTATUS = True
except ImportError:
    HAS_GRIDSTATUS = False

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ercot_cache.duckdb")


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

    if HAS_GRIDSTATUS:
        try:
            ercot = gridstatus.ERCOT()
            end = pd.Timestamp.now(tz="US/Central")
            start = end - pd.Timedelta(days=days)
            all_dfs = []
            for zone_id in zone_ids:
                zone_df = ercot.get_lmp(start=start, end=end, location_type="Zone", location=zone_id)
                zone_df = zone_df.rename(columns={"LMP": "lmp", "Time": "timestamp"})
                zone_df["zone"] = zone_id
                all_dfs.append(zone_df[["timestamp", "lmp", "zone"]])
            df = pd.concat(all_dfs, ignore_index=True)
            _cache_data(df)
            df["_source"] = "live (ERCOT)"
            return df
        except Exception:
            pass

    df = _generate_synthetic(days, zone_ids)
    df["_source"] = "synthetic (gridstatus not available)"
    return df


def get_ercot_load(days=365):
    if HAS_GRIDSTATUS:
        try:
            ercot = gridstatus.ERCOT()
            end = pd.Timestamp.now(tz="US/Central")
            start = end - pd.Timedelta(days=days)
            df = ercot.get_load(start=start, end=end)
            return df
        except Exception:
            pass
    return _generate_synthetic_load(days)


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
