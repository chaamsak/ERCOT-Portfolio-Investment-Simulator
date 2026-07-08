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


def get_ercot_lmp(days=90, node="HB_SOUTH"):
    """Fetch ERCOT LMP data. Falls back to synthetic if gridstatus unavailable."""
    # Try cache first
    if HAS_DUCKDB and os.path.exists(CACHE_PATH):
        try:
            con = duckdb.connect(CACHE_PATH, read_only=True)
            df = con.execute(
                "SELECT * FROM lmp WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL ? DAY",
                [days]
            ).fetchdf()
            con.close()
            if len(df) > 100:
                return df
        except Exception:
            pass

    # Try gridstatus live
    if HAS_GRIDSTATUS:
        try:
            ercot = gridstatus.ERCOT()
            end = pd.Timestamp.now(tz="US/Central")
            start = end - pd.Timedelta(days=days)
            df = ercot.get_lmp(start=start, end=end, location_type="Zone", location=node)
            df = df.rename(columns={"LMP": "lmp", "Time": "timestamp"})
            df = df[["timestamp", "lmp"]].copy()
            _cache_data(df)
            return df
        except Exception:
            pass

    # Fallback to synthetic
    return _generate_synthetic(days)


def get_ercot_load(days=365):
    """Fetch ERCOT load data. Falls back to synthetic."""
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
    """Cache data to DuckDB."""
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


def _generate_synthetic(days):
    """Generate synthetic ERCOT-like LMP data."""
    np.random.seed(42)
    hours = days * 24
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=hours, freq="h")
    base = 35 + 15 * np.sin(np.arange(hours) * 2 * np.pi / 24)
    seasonal = 10 * np.sin(np.arange(hours) * 2 * np.pi / (24 * 365))
    noise = np.random.normal(0, 8, hours)
    spikes = np.random.choice([0, 1], size=hours, p=[0.995, 0.005])
    spike_vals = spikes * np.random.uniform(100, 2000, hours)
    prices = np.maximum(base + seasonal + noise + spike_vals, -10)
    return pd.DataFrame({"timestamp": timestamps, "lmp": prices})


def _generate_synthetic_load(days):
    """Generate synthetic ERCOT load data."""
    np.random.seed(123)
    hours = days * 24
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=hours, freq="h")
    base_load = 45000  # MW average
    diurnal = 8000 * np.sin((np.arange(hours) - 6) * 2 * np.pi / 24)
    seasonal = 12000 * np.sin((np.arange(hours) / 24 - 30) * 2 * np.pi / 365)
    noise = np.random.normal(0, 2000, hours)
    load = base_load + diurnal + seasonal + noise
    return pd.DataFrame({"timestamp": timestamps, "load_mw": np.maximum(load, 20000)})