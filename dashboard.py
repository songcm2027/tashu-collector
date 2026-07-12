import sqlite3, pandas as pd, json, re, os
from datetime import datetime, timezone

con = sqlite3.connect("tashu.db")
latest = pd.read_sql("SELECT MAX(collected_at) t FROM snapshots", con)["t"][0]
cur = pd.read_sql("SELECT station_id, available_bikes FROM snapshots WHERE collected_at=?", con, params=[latest])
names = pd.read_sql("SELECT station_id, name FROM stations", con).set_index("station_id")["name"]
con.close()

ts = pd.to_datetime(latest); hour = ts.hour; wknd = ts.dayofweek >= 5
tgt = pd.read_csv("target_inventory.csv")
tgt = tgt[(tgt.is_weekend == wknd) & (tgt.hour == hour)][["station_id", "target_bikes"]]
m = cur.merge(tgt, on="station_id", how="left"); m["target_bikes"] = m["target_bikes"].fillna(0)
m["need"] = m["target_bikes"] - m["available_bikes"]; m["name"] = m["station_id"].map(names)

route = None
if os.path.exists("plan.txt"):
    mm = re.search(r"stops (\d+) \| distance ([\d.]+) km \| delivered (\d+)/(\d+)", open("plan.txt").read())
    if mm: route = {"stops": int(mm.group(1)), "km": float(mm.group(2)),
                    "delivered": int(mm.group(3)), "needed": int(mm.group(4))}

def rows(df):
    return [{"name": r["name"], "have": int(r.available_bikes), "target": int(r.target_bikes)} for _, r in df.iterrows()]

data = {
  "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
  "snapshot": latest, "stations": len(cur),
  "available": int(cur["available_bikes"].sum()),
  "empty": int((cur["available_bikes"] == 0).sum()),
  "empty_pct": round((cur["available_bikes"] == 0).mean() * 100, 1),
  "to_add": int(m["need"].clip(lower=0).sum()),
  "short": rows(m.sort_values("need", ascending=False).head(6)),
  "surplus": rows(m.sort_values("need").head(6)),
  "route": route,
}
os.makedirs("docs", exist_ok=True)
json.dump(data, open("docs/data.json", "w"), ensure_ascii=False, indent=2)
print("Wrote docs/data.json")
