import sqlite3, pandas as pd, numpy as np, folium

TRUCK_CAP = 20; N = 15
con = sqlite3.connect("tashu.db")
latest = pd.read_sql("SELECT MAX(collected_at) AS t FROM snapshots", con)["t"][0]
cur = pd.read_sql("SELECT station_id, available_bikes FROM snapshots WHERE collected_at=?", con, params=[latest])
st  = pd.read_sql("SELECT station_id, name, lat, lon FROM stations", con)
con.close()
ts = pd.to_datetime(latest); hour = ts.hour; is_weekend = ts.dayofweek >= 5
tgt = pd.read_csv("target_inventory.csv")
tgt = tgt[(tgt.is_weekend == is_weekend) & (tgt.hour == hour)][["station_id", "target_bikes"]]
df = cur.merge(tgt, on="station_id", how="left").merge(st, on="station_id")
df["target_bikes"] = df["target_bikes"].fillna(0); df["need"] = df["target_bikes"] - df["available_bikes"]
donors = df[df.need < 0].nsmallest(N, "need").copy(); receivers = df[df.need > 0].nlargest(N, "need").copy()
donors["have"] = (-donors["need"]).astype(int); receivers["want"] = receivers["need"].astype(int)
donors = donors.set_index("station_id"); receivers = receivers.set_index("station_id")

def km(a, b):
    R = 6371.0; rad = np.radians; dlat = rad(b[0]-a[0]); dlon = rad(b[1]-a[1])
    h = np.sin(dlat/2)**2 + np.cos(rad(a[0]))*np.cos(rad(b[0]))*np.sin(dlon/2)**2
    return 2*R*np.arcsin(np.sqrt(h))

pos = (donors.iloc[0].lat, donors.iloc[0].lon); load = 0; route = []
for _ in range(N*4):
    cand = []
    if load < TRUCK_CAP: cand += [("pickup", s, (r.lat, r.lon)) for s, r in donors.iterrows() if r.have > 0]
    if load > 0: cand += [("drop", s, (r.lat, r.lon)) for s, r in receivers.iterrows() if r.want > 0]
    if not cand: break
    act, s, p = min(cand, key=lambda c: km(pos, c[2])); pos = p
    if act == "pickup":
        q = min(int(donors.at[s, "have"]), TRUCK_CAP-load); load += q; donors.at[s, "have"] -= q
        route.append((donors.at[s, "name"], p, "pickup", q))
    else:
        q = min(int(receivers.at[s, "want"]), load); load -= q; receivers.at[s, "want"] -= q
        route.append((receivers.at[s, "name"], p, "drop", q))

m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=12)
folium.PolyLine([p for _, p, _, _ in route], color="blue", weight=3, opacity=0.7).add_to(m)
for i, (name, p, act, q) in enumerate(route, 1):
    color = "green" if act == "pickup" else "red"; sign = "+" if act == "pickup" else "-"
    folium.CircleMarker(p, radius=7, color=color, fill=True, fill_opacity=0.9,
                        popup=f"{i}. {name} ({sign}{q})").add_to(m)
    folium.map.Marker(p, icon=folium.DivIcon(
        html=f'<div style="font-size:11px;font-weight:bold;color:black">{i}</div>')).add_to(m)
m.save("route_map.html")
print("Saved route_map.html — open it. Green=pick up, Red=drop off, blue line=truck path.")
