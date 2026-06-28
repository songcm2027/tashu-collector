import sqlite3, pandas as pd, numpy as np

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()
df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
df["hour_ts"] = df["t"].dt.floor("h")
h = df.groupby("hour_ts", as_index=False)["pickups"].sum().rename(columns={"pickups": "actual"})
h["hour"] = h["hour_ts"].dt.hour
h["is_weekend"] = h["hour_ts"].dt.dayofweek >= 5

w = pd.read_csv("weather.csv")
w["hour_ts"] = pd.to_datetime(w["datetime"])
w["precip"] = pd.to_numeric(w["precip"], errors="coerce").fillna(0)
w["rain"] = w["precip"] > 0
h = h.merge(w[["hour_ts", "rain"]], on="hour_ts", how="inner")
h = h[(h["hour"] >= 6) & (h["hour"] <= 22)]

# "normal" demand from DRY hours, by weekday/weekend + hour
base = h[~h["rain"]].groupby(["is_weekend", "hour"])["actual"].mean().rename("pred")
h = h.join(base, on=["is_weekend", "hour"]).dropna(subset=["pred"])
factor = h.loc[h["rain"], "actual"].mean() / h.loc[~h["rain"], "actual"].mean()

h["pred_noweather"] = h["pred"]                                      # ignores rain
h["pred_weather"]   = h["pred"] * np.where(h["rain"], factor, 1.0)   # scales down in rain

mae = lambda d, c: (d["actual"] - d[c]).abs().mean()
print(f"Rain factor: {factor:.2f}  (rainy demand ≈ {factor:.0%} of dry)\n")
print(f"MAE, all daytime hours — no-weather {mae(h,'pred_noweather'):.0f} | weather-aware {mae(h,'pred_weather'):.0f}")
rr = h[h["rain"]]
print(f"MAE, rainy hours only  — no-weather {mae(rr,'pred_noweather'):.0f} | weather-aware {mae(rr,'pred_weather'):.0f}")
