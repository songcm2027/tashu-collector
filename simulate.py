import sqlite3, pandas as pd, numpy as np

CU, CO = 2, 1   # stockout twice as costly as dock-out (matches the target model)

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()
df["t"] = pd.to_datetime(df["collected_at"]); df = df.sort_values(["station_id", "t"])
d = df.groupby("station_id")["available_bikes"].diff()
df["pick"] = (-d).clip(lower=0); df["ret"] = d.clip(lower=0)
df["date"] = df["t"].dt.date; df["hour"] = df["t"].dt.hour
df["wknd"] = pd.to_datetime(df["date"]).dt.dayofweek >= 5
wd = df[~df["wknd"]].copy()

stations = sorted(df["station_id"].unique())
cap = df.groupby("station_id")["available_bikes"].max().reindex(stations).fillna(1)
capv = cap.values.astype(float)

def grid(data, col):
    g = data.groupby(["station_id", "date", "hour"])[col].sum().groupby(["station_id", "hour"]).mean()
    return g.unstack(fill_value=0).reindex(stations).reindex(columns=range(24), fill_value=0).fillna(0).values

Pa, Ra = grid(wd, "pick"), grid(wd, "ret")   # station x 24 average weekday

def run(P, R, start):
    avail = np.minimum(start, capv).astype(float).copy()
    up = np.zeros(len(stations)); ur = np.zeros(len(stations))
    for h in range(24):
        r, p = R[:, h], P[:, h]
        acc = np.minimum(r, capv - avail); ur += r - acc; avail = avail + acc
        srv = np.minimum(p, avail);        up += p - srv; avail = avail - srv
    return up, ur

# OPTIMIZED start: per-station level minimizing CU*stockouts + CO*dockouts on the average weekday
best = np.full(len(stations), np.inf); opt = np.zeros(len(stations))
for S in range(int(capv.max()) + 1):
    up, ur = run(Pa, Ra, np.full(len(stations), float(S)))
    cost = CU * up + CO * ur
    take = cost < best
    opt = np.where(take, np.minimum(S, capv), opt); best = np.where(take, cost, best)

starts = {
    "No rebalancing":  df[df["hour"] == 5].groupby("station_id")["available_bikes"].mean().reindex(stations).fillna(cap * 0.3).values,
    "Naive (fill 50%)": capv * 0.5,
    "Optimized":        opt,
}

res = {k: [0.0, 0.0, 0.0, 0.0] for k in starts}
for dt in sorted(wd["date"].unique()):
    dd = wd[wd["date"] == dt]
    P = dd.groupby(["station_id", "hour"])["pick"].sum().unstack(fill_value=0).reindex(stations).reindex(columns=range(24), fill_value=0).fillna(0).values
    R = dd.groupby(["station_id", "hour"])["ret"].sum().unstack(fill_value=0).reindex(stations).reindex(columns=range(24), fill_value=0).fillna(0).values
    tp, tr = P.sum(), R.sum()
    for k, s in starts.items():
        up, ur = run(P, R, s.copy())
        res[k][0] += up.sum(); res[k][1] += ur.sum(); res[k][2] += tp; res[k][3] += tr

print(f"Simulated {len(set(wd['date']))} weekdays x {len(stations)} stations\n")
print(f"{'Policy':<18}{'Service':>9}{'Stockouts':>11}{'Dock-outs':>11}{'Weighted':>11}")
for k, (up, ur, tp, tr) in res.items():
    print(f"{k:<18}{(1-(up+ur)/(tp+tr))*100:>8.1f}%{up:>11.0f}{ur:>11.0f}{CU*up+CO*ur:>11.0f}")
b, o = res["No rebalancing"], res["Optimized"]
print(f"\n=> Optimized vs no rebalancing: stockouts {(1-o[0]/b[0])*100:+.0f}%, "
      f"weighted failures {(1-(CU*o[0]+CO*o[1])/(CU*b[0]+CO*b[1]))*100:+.0f}%")
