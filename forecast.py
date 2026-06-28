import sqlite3, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()

# 1) derive rentals per interval (a drop in bikes = a rental)
df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)

# 2) bucket into date + hour, then rentals per station per (date, hour)
df["date"] = df["t"].dt.date
df["hour"] = df["t"].dt.hour
hourly = df.groupby(["station_id", "date", "hour"])["pickups"].sum().reset_index()

# 3) THE MODEL: average rentals per (station, hour) across days
model = (hourly.groupby(["station_id", "hour"])["pickups"].mean()
         .reset_index().rename(columns={"pickups": "predicted_rentals"}))

# 4) system-wide "typical day": expected total rentals by hour
typical = model.groupby("hour")["predicted_rentals"].sum()

print("=== Predicted typical-day demand (total rentals by hour) ===")
for h, v in typical.items():
    print(f"  {h:02d}:00  {v:6.0f}  " + "#" * int(v / 40))

plt.figure(figsize=(10, 5))
plt.bar(typical.index, typical.values, color="tab:green")
plt.xlabel("Hour of day"); plt.ylabel("Predicted total rentals")
plt.title("Baseline forecast: typical-day demand by hour")
plt.tight_layout(); plt.savefig("forecast.png", dpi=120)
print("\nSaved forecast.png  |  per-station model rows:", len(model))
