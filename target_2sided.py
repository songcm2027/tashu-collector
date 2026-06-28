import sqlite3, pandas as pd, numpy as np

CU, CO = 2, 1            # stockout (empty) twice as costly as dock-out (full)
FRAC = CU / (CU + CO)    # critical fractile = 0.67

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
nm = pd.read_sql("SELECT station_id, name FROM stations", con).set_index("station_id")["name"]
con.close()
df["t"] = pd.to_datetime(df["collected_at"]); df = df.sort_values(["station_id", "t"])
d = df.groupby("station_id")["available_bikes"].diff()
df["pick"] = (-d).clip(lower=0)     # drops  = rentals out
df["ret"]  = d.clip(lower=0)        # rises  = returns in
df["date"] = df["t"].dt.date; df["hour"] = df["t"].dt.hour
df["wknd"] = pd.to_datetime(df["date"]).dt.dayofweek >= 5

g = df.groupby(["station_id", "date", "wknd", "hour"])
net = (g["pick"].sum() - g["ret"].sum()).rename("net").reset_index()   # net OUTFLOW per hour
cap = df.groupby("station_id")["available_bikes"].max().rename("cap")   # capacity proxy (max seen)

tgt = net.groupby(["station_id", "wknd", "hour"])["net"].quantile(FRAC).rename("target").reset_index()
tgt = tgt.merge(cap, on="station_id")
tgt["target"] = np.minimum(tgt["target"].clip(lower=0), tgt["cap"]).round().astype(int)
tgt.to_csv("target_inventory_2sided.csv", index=False)

mean_net = net.groupby("station_id")["net"].mean()
print(f"Critical fractile = {FRAC:.2f}  (stockout {CU}x vs dock-out {CO}x)\n")
print(f"Mostly LOSE bikes (stockout risk -> stock up)       : {(mean_net > 0.05).sum()}")
print(f"Mostly GAIN bikes (overflow risk -> keep docks free): {(mean_net < -0.05).sum()}")
print(f"Roughly balanced                                    : {(mean_net.abs() <= 0.05).sum()}")
print("\nYour one-sided model only saw the stockout side. Two-sided also protects returns.")
print("\nTop overflow-risk stations (returns > pickups) — keep these LOW:")
for sid, v in mean_net.sort_values().head(6).items():
    print(f"  {nm.get(sid, sid):<28} net {v:+.2f} bikes/hr")
print("\nSaved target_inventory_2sided.csv")
