import sqlite3, pandas as pd, json, re, os
from datetime import datetime, timezone

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
names = pd.read_sql("SELECT station_id, name FROM stations", con).set_index("station_id")["name"]
con.close()
df["t"] = pd.to_datetime(df["collected_at"])
latest = df["t"].max()
cur = df[df["t"] == latest][["station_id", "available_bikes"]]

total = int(cur["available_bikes"].sum()); empty = int((cur["available_bikes"] == 0).sum()); nst = len(cur)
hour = latest.hour; wknd = latest.dayofweek >= 5
tgt = pd.read_csv("target_inventory.csv")
tg = tgt[(tgt.is_weekend == wknd) & (tgt.hour == hour)][["station_id", "target_bikes"]]
m = cur.merge(tg, on="station_id", how="left"); m["target_bikes"] = m["target_bikes"].fillna(0)
m["need"] = m["target_bikes"] - m["available_bikes"]; m["name"] = m["station_id"].map(names)
to_add = int(m["need"].clip(lower=0).sum())
def rows(d): return [{"name": r["name"], "have": int(r.available_bikes), "target": int(r.target_bikes)} for _, r in d.iterrows()]
short = rows(m.sort_values("need", ascending=False).head(6)); surplus = rows(m.sort_values("need").head(6))

route = None
if os.path.exists("plan.txt"):
    mm = re.search(r"stops (\d+) \| distance ([\d.]+) km \| delivered (\d+)/(\d+)", open("plan.txt").read())
    if mm: route = {"stops": int(mm.group(1)), "km": float(mm.group(2)), "delivered": int(mm.group(3)), "needed": int(mm.group(4))}

# ---- timetable for today's day type ----
df["hour"] = df["t"].dt.hour; df["wknd"] = df["t"].dt.dayofweek >= 5
lvl = df.groupby(["station_id", "wknd", "hour"])["available_bikes"].mean()
WINDOWS = {False: [5, 10, 14], True: [5, 13]}
LAB = {(False,5):"before morning peak",(False,10):"midday reset",(False,14):"before evening peak",
       (True,5):"early morning",(True,13):"before evening peak"}
T = tgt[tgt.is_weekend == wknd].pivot_table(index="station_id", columns="hour", values="target_bikes", fill_value=0)
L = lvl.xs(wknd, level="wknd").unstack(fill_value=0)
sched = []
wins = WINDOWS[wknd]
for i, h in enumerate(wins):
    end = wins[i + 1] if i + 1 < len(wins) else 24
    hrs = [x for x in range(h + 1, end + 1) if x in T.columns] or [h]
    peak = T.reindex(columns=hrs, fill_value=0).max(axis=1)
    c = (L[h] if h in L.columns else peak * 0).reindex(peak.index).fillna(0)
    need = (peak - c).clip(lower=0)
    fill = [{"name": names.get(s, s), "q": int(round(need[s]))} for s in need.sort_values(ascending=False).head(5).index if need[s] >= 1]
    sched.append({"time": f"{h:02d}:00", "until": f"{end:02d}:00", "label": LAB.get((wknd, h), ""),
                  "bikes": int(need.round().sum()), "fill": fill})

data = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "snapshot": str(latest),
        "daytype": "weekend" if wknd else "weekday", "stations": nst, "available": total, "empty": empty,
        "empty_pct": round(empty / nst * 100, 1), "to_add": to_add, "short": short, "surplus": surplus,
        "route": route, "schedule": sched}
os.makedirs("docs", exist_ok=True)
json.dump(data, open("docs/data.json", "w"), ensure_ascii=False, indent=2)
print("Wrote docs/data.json with timetable")
