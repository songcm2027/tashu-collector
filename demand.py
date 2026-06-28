import sqlite3, pandas as pd

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
names = pd.read_sql("SELECT station_id, name FROM stations", con).set_index("station_id")["name"]
con.close()

df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])

# change in bikes since this station's previous snapshot
df["delta"] = df.groupby("station_id")["available_bikes"].diff()
df["pickups"] = (-df["delta"]).clip(lower=0)   # a drop  = bikes rented
df["returns"] = df["delta"].clip(lower=0)      # a rise  = bikes returned

print("=== Demand per 15-min interval (system-wide) ===")
per = df.groupby("t").agg(pickups=("pickups", "sum"), returns=("returns", "sum"))
print(per.to_string())

print(f"\nAfternoon totals — rentals: {int(df['pickups'].sum())}, returns: {int(df['returns'].sum())}")

print("\n=== Busiest stations (most rentals) ===")
busy = df.groupby("station_id")["pickups"].sum().sort_values(ascending=False).head(10)
for sid, p in busy.items():
    print(f"  {names.get(sid, sid)}: {int(p)}")
