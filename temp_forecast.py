import sqlite3, pandas as pd, numpy as np

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()
df["t"] = pd.to_datetime(df["collected_at"]); df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
df["hour_ts"] = df["t"].dt.floor("h")
h = df.groupby("hour_ts", as_index=False)["pickups"].sum().rename(columns={"pickups": "actual"})
h["hour"] = h["hour_ts"].dt.hour
h["is_weekend"] = h["hour_ts"].dt.dayofweek >= 5

w = pd.read_csv("weather.csv")
w["hour_ts"] = pd.to_datetime(w["datetime"])
w["precip"] = pd.to_numeric(w["precip"], errors="coerce").fillna(0)
w["temp"]   = pd.to_numeric(w["temp"], errors="coerce")
w["rain"]   = w["precip"] > 0
h = h.merge(w[["hour_ts", "rain", "temp"]], on="hour_ts", how="inner")
h = h[h.hour.between(6, 22)].copy()

base = h[~h.rain].groupby(["is_weekend", "hour"])["actual"].mean().rename("base")
h = h.join(base, on=["is_weekend", "hour"]).dropna(subset=["base"])
factor = h.loc[h.rain, "actual"].mean() / h.loc[~h.rain, "actual"].mean()
h["pred_rain"] = h["base"] * np.where(h.rain, factor, 1.0)

# temperature multiplier, fit on dry hours
dry = h[~h.rain]
tmean = dry["temp"].mean()
beta = np.polyfit(dry["temp"] - tmean, dry["actual"] / dry["base"], 1)[0]
print(f"Temperature effect: {beta*100:+.1f}% demand per +1°C (centered at {tmean:.0f}°C)\n")
h["pred_both"] = h["pred_rain"] * (1 + beta * (h["temp"] - tmean))

mae = lambda c: (h["actual"] - h[c]).abs().mean()
print(f"MAE rain only   : {mae('pred_rain'):.0f}")
print(f"MAE rain + temp : {mae('pred_both'):.0f}")
