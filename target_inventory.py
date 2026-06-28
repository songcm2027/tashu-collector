import sqlite3, pandas as pd

SERVICE = 0.90   # cover 90% of demand scenarios (higher = fewer empties, more handling)

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
names = pd.read_sql("SELECT station_id, name FROM stations", con).set_index("station_id")["name"]
con.close()

df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
df["date"] = df["t"].dt.date
df["hour"] = df["t"].dt.hour
df["is_weekend"] = pd.to_datetime(df["date"]).dt.dayofweek >= 5

# demand realizations: rentals per station per (date, hour)
hourly = df.groupby(["station_id", "date", "is_weekend", "hour"], as_index=False)["pickups"].sum()

# TARGET = service-level quantile of hourly rentals, per (station, weekday/weekend, hour)
target = (hourly.groupby(["station_id", "is_weekend", "hour"])["pickups"]
          .quantile(SERVICE).round().astype(int).rename("target_bikes").reset_index())

# can't exceed capacity -> proxy = max bikes ever seen at the station
cap = df.groupby("station_id")["available_bikes"].max().rename("capacity")
target = target.merge(cap, on="station_id")
target["target_bikes"] = target[["target_bikes", "capacity"]].min(axis=1)

# example: weekday morning peak (8 AM) — stations needing the most bikes
ex = target[(~target["is_weekend"]) & (target["hour"] == 8)].copy()
ex["name"] = ex["station_id"].map(names)
print("=== Weekday 8 AM target inventory (top 10 stations) ===")
print(ex.sort_values("target_bikes", ascending=False)
        .head(10)[["name", "target_bikes", "capacity"]].to_string(index=False))

target.to_csv("target_inventory.csv", index=False)
print(f"\nSaved target_inventory.csv  (target bikes per station x weekday/weekend x hour, service={SERVICE})")
