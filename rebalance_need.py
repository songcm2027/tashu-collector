import sqlite3, pandas as pd

con = sqlite3.connect("tashu.db")
latest = pd.read_sql("SELECT MAX(collected_at) AS t FROM snapshots", con)["t"][0]
cur = pd.read_sql("SELECT station_id, available_bikes FROM snapshots WHERE collected_at = ?", con, params=[latest])
names = pd.read_sql("SELECT station_id, name FROM stations", con).set_index("station_id")["name"]
con.close()

ts = pd.to_datetime(latest)
hour, is_weekend = ts.hour, ts.dayofweek >= 5

tgt = pd.read_csv("target_inventory.csv")
tgt = tgt[(tgt["is_weekend"] == is_weekend) & (tgt["hour"] == hour)][["station_id", "target_bikes"]]

m = cur.merge(tgt, on="station_id", how="left")
m["target_bikes"] = m["target_bikes"].fillna(0)
m["need"] = m["target_bikes"] - m["available_bikes"]      # + = needs bikes, - = surplus
m["name"] = m["station_id"].map(names)

print(f"Snapshot: {latest}  ({'weekend' if is_weekend else 'weekday'} {hour}:00)")
print(f"Total bikes to ADD (deficit): {int(m['need'].clip(lower=0).sum())}")
print(f"Total bikes to REMOVE (surplus): {int((-m['need']).clip(lower=0).sum())}")
print("\n[Most short — needs bikes]")
print(m.sort_values("need", ascending=False).head(8)[["name", "available_bikes", "target_bikes", "need"]].to_string(index=False))
print("\n[Most over — has spare bikes]")
print(m.sort_values("need").head(8)[["name", "available_bikes", "target_bikes", "need"]].to_string(index=False))
