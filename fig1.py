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
h = df.groupby(["date", "is_weekend", "hour"], as_index=False)["pickups"].sum()
wd = h[~h["is_weekend"]].groupby("hour")["pickups"].mean()
we = h[h["is_weekend"]].groupby("hour")["pickups"].mean()
plt.figure(figsize=(10, 5))
plt.plot(wd.index, wd.values, marker="o", label="Weekday")
plt.plot(we.index, we.values, marker="o", label="Weekend")
plt.xlabel("Hour of day"); plt.ylabel("Avg. rentals per day (all stations)")
plt.title("Tashu hourly rental demand: weekday vs. weekend")
plt.legend(); plt.tight_layout()
plt.savefig("fig1_weekday_weekend.png", dpi=150)
print("Saved fig1_weekday_weekend.png")
