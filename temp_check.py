import sqlite3, pandas as pd

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()
df["t"] = pd.to_datetime(df["collected_at"]); df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
df["hour_ts"] = df["t"].dt.floor("h")
h = df.groupby("hour_ts", as_index=False)["pickups"].sum().rename(columns={"pickups": "demand"})
h["hour"] = h["hour_ts"].dt.hour

w = pd.read_csv("weather.csv")
w["hour_ts"] = pd.to_datetime(w["datetime"])
w["precip"] = pd.to_numeric(w["precip"], errors="coerce").fillna(0)
w["temp"]   = pd.to_numeric(w["temp"], errors="coerce")
h = h.merge(w[["hour_ts", "precip", "temp"]], on="hour_ts", how="inner")

dry = h[(h.precip == 0) & h.hour.between(6, 22)].copy()
raw = dry["demand"].corr(dry["temp"])
dry["d_res"] = dry["demand"] - dry.groupby("hour")["demand"].transform("mean")
dry["t_res"] = dry["temp"]   - dry.groupby("hour")["temp"].transform("mean")
partial = dry["d_res"].corr(dry["t_res"])

print(f"Dry daytime hours: {len(dry)}")
print(f"corr(demand, temp)                          = {raw:+.2f}")
print(f"corr(demand, temp), controlling for hour    = {partial:+.2f}")
print("-> if the controlled number is near 0, temperature is mostly a time-of-day proxy")
