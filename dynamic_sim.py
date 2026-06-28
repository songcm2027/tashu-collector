import sqlite3, pandas as pd, numpy as np
CU, CO = 2, 1
con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con); con.close()
df["t"] = pd.to_datetime(df["collected_at"]); df = df.sort_values(["station_id", "t"])
d = df.groupby("station_id")["available_bikes"].diff()
df["pick"] = (-d).clip(lower=0); df["ret"] = d.clip(lower=0)
df["date"] = df["t"].dt.date; df["hour"] = df["t"].dt.hour
df["wknd"] = pd.to_datetime(df["date"]).dt.dayofweek >= 5
wd = df[~df["wknd"]].copy()
stations = sorted(df["station_id"].unique()); n = len(stations)
cap = df.groupby("station_id")["available_bikes"].max().reindex(stations).fillna(1); capv = cap.values.astype(float)

def grid(data, col):
    g = data.groupby(["station_id", "date", "hour"])[col].sum().groupby(["station_id", "hour"]).mean()
    return g.unstack(fill_value=0).reindex(stations).reindex(columns=range(24), fill_value=0).fillna(0).values
Pa, Ra = grid(wd, "pick"), grid(wd, "ret")
target = np.zeros(n)

def run(P, R, start, resets=()):
    avail = np.minimum(start, capv).astype(float).copy()
    up = np.zeros(n); ur = np.zeros(n)
    for h in range(24):
        if h in resets: avail = np.minimum(target, capv).astype(float).copy()
        r, p = R[:, h], P[:, h]
        acc = np.minimum(r, capv - avail); ur += r - acc; avail = avail + acc
        srv = np.minimum(p, avail);        up += p - srv; avail = avail - srv
    return up.sum(), ur.sum()

best = np.full(n, np.inf)
for S in range(int(capv.max()) + 1):
    up, ur = run(Pa, Ra, np.full(n, float(S)))
    cost = CU * up + CO * ur; take = cost < best
    target = np.where(take, np.minimum(S, capv), target); best = np.where(take, cost, best)

schemes = {"Overnight only (static)": (), "+ 1 midday rebalance": (14,),
           "+ every 6h": (6, 12, 18), "+ every 3h": (6, 9, 12, 15, 18, 21)}
res = {k: [0.0, 0.0] for k in schemes}
for dt in sorted(wd["date"].unique()):
    dd = wd[wd["date"] == dt]
    P = dd.groupby(["station_id", "hour"])["pick"].sum().unstack(fill_value=0).reindex(stations).reindex(columns=range(24), fill_value=0).fillna(0).values
    R = dd.groupby(["station_id", "hour"])["ret"].sum().unstack(fill_value=0).reindex(stations).reindex(columns=range(24), fill_value=0).fillna(0).values
    for k, rs in schemes.items():
        up, ur = run(P, R, target, rs); res[k][0] += up; res[k][1] += ur

print(f"Same targets, different rebalancing frequency:\n\n{'Rebalancing':<26}{'Stockouts':>11}{'Dock-outs':>11}")
base = None
for k, (up, ur) in res.items():
    base = up if base is None else base
    print(f"{k:<26}{up:>11.0f}{ur:>11.0f}   ({(1-up/base)*100:+.0f}% vs static)")
