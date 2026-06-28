import sqlite3, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()
df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
df["date"] = df["t"].dt.date
df["hour"] = df["t"].dt.hour
df["is_weekend"] = pd.to_datetime(df["date"]).dt.dayofweek >= 5
hourly = df.groupby(["station_id", "date", "is_weekend", "hour"], as_index=False)["pickups"].sum()

dates = sorted(hourly["date"].unique())
test_day = dates[-2]                       # last complete day (today is partial)
train = hourly[hourly["date"] != test_day]
test  = hourly[hourly["date"] == test_day]

model = train.groupby(["station_id", "is_weekend", "hour"], as_index=False)["pickups"].mean().rename(columns={"pickups": "pred"})
ev = test.merge(model, on=["station_id", "is_weekend", "hour"], how="left")
ev["pred"] = ev["pred"].fillna(0)

actual = ev.groupby("hour")["pickups"].sum()
pred   = ev.groupby("hour")["pred"].sum()
mae = (ev["pickups"] - ev["pred"]).abs().mean()

plt.figure(figsize=(10, 5))
plt.plot(actual.index, actual.values, marker="o", label="Actual")
plt.plot(pred.index, pred.values, marker="o", linestyle="--", label="Predicted")
plt.xlabel("Hour of day"); plt.ylabel("Total rentals (all stations)")
plt.title(f"Forecast vs. actual on a held-out day ({test_day})")
plt.legend(); plt.tight_layout()
plt.savefig("fig4_forecast_validation.png", dpi=150)
print(f"Saved fig4_forecast_validation.png | test day {test_day}, MAE {mae:.3f}")
