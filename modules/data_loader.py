# Data loader querying Grid Status ERCOT data from Snowflake marketplace share

import pandas as pd
import numpy as np
import os
import streamlit as st

try:
    import snowflake.connector
    HAS_SNOWFLAKE = True
except ImportError:
    HAS_SNOWFLAKE = False


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


def _get_snowflake_conn():
    """Create Snowflake connection from Streamlit secrets."""
    return snowflake.connector.connect(
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        warehouse=st.secrets.get("SNOWFLAKE_WAREHOUSE", "GENTEST"),
        database="GRID_STATUS__ERCOT_DATASETS",
        schema="SHARE",
    )


def get_ercot_lmp(days=90, zones=None):
    if zones is None:
        zones = ["LZ_SOUTH"]
    zone_ids = [_zone_label_to_id(z) for z in zones]

    if HAS_SNOWFLAKE:
        try:
            conn = _get_snowflake_conn()
            placeholders = ",".join([f"'{z}'" for z in zone_ids])
            query = f"""
                SELECT
                    INTERVAL_START_LOCAL AS timestamp,
                    LMP AS lmp,
                    LOCATION AS zone
                FROM ERCOT_LMP_BY_SETTLEMENT_POINT
                WHERE INTERVAL_START_LOCAL >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
                AND LOCATION IN ({placeholders})
                AND LOCATION_TYPE = 'Trading Hub'
                ORDER BY INTERVAL_START_LOCAL
            """
            df = pd.read_sql(query, conn)
            conn.close()
            df.columns = [c.lower() for c in df.columns]
            df["_source"] = "live (Snowflake - Grid Status)"
            return df
        except Exception as e:
            source = f"synthetic (Snowflake error: {type(e).__name__}: {e})"
    else:
        source = "synthetic (snowflake-connector not installed)"

    df = _generate_synthetic(days, zone_ids)
    df["_source"] = source
    return df


def get_ercot_load(days=365):
    if HAS_SNOWFLAKE:
        try:
            conn = _get_snowflake_conn()
            query = f"""
                SELECT
                    INTERVAL_START_LOCAL AS timestamp,
                    LOAD AS load_mw
                FROM ERCOT_LOAD
                WHERE INTERVAL_START_LOCAL >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
                ORDER BY INTERVAL_START_LOCAL
            """
            df = pd.read_sql(query, conn)
            conn.close()
            df.columns = [c.lower() for c in df.columns]
            df["_source"] = "live (Snowflake - Grid Status)"
            return df
        except Exception:
            pass
    df = _generate_synthetic_load(days)
    df["_source"] = "synthetic"
    return df


def get_ercot_as_prices(days=90):
    if HAS_SNOWFLAKE:
        try:
            conn = _get_snowflake_conn()
            query = f"""
                SELECT
                    INTERVAL_START_LOCAL AS timestamp,
                    AS_TYPE,
                    MCPC AS price
                FROM ERCOT_MCPC_DAM
                WHERE INTERVAL_START_LOCAL >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
                ORDER BY INTERVAL_START_LOCAL
            """
            df = pd.read_sql(query, conn)
            conn.close()
            df.columns = [c.lower() for c in df.columns]
            # Pivot AS types into columns
            if "as_type" in df.columns:
                pivot = df.pivot_table(index="timestamp", columns="as_type", values="price").reset_index()
                pivot.columns = [c.lower().replace(" ", "_") for c in pivot.columns]
                pivot["_source"] = "live (Snowflake - Grid Status)"
                return pivot
        except Exception:
            pass
    return _generate_synthetic_as_prices(days)


def get_ercot_fuel_mix(days=90):
    if HAS_SNOWFLAKE:
        try:
            conn = _get_snowflake_conn()
            query = f"""
                SELECT
                    INTERVAL_START_LOCAL AS timestamp,
                    NATURAL_GAS AS gas,
                    WIND,
                    SOLAR,
                    NUCLEAR,
                    COAL_AND_LIGNITE AS coal,
                    HYDRO,
                    OTHER,
                    POWER_STORAGE AS storage
                FROM ERCOT_FUEL_MIX
                WHERE INTERVAL_START_LOCAL >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
                ORDER BY INTERVAL_START_LOCAL
            """
            df = pd.read_sql(query, conn)
            conn.close()
            df.columns = [c.lower() for c in df.columns]
            df["_source"] = "live (Snowflake - Grid Status)"
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
        "storage": 500 + np.random.normal(0, 300, hours),
    })
    for col in ["gas", "wind", "solar", "coal", "hydro", "other", "storage"]:
        df[col] = np.maximum(df[col], 0)
    df["_source"] = "synthetic"
    return df
