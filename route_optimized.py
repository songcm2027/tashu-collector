import sqlite3, pandas as pd, numpy as np, folium
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

TRUCK_CAP = 20
N = 15      # most-short stations to serve
M = 40      # candidate surplus stations the solver may choose from

con = sqlite3.connect("tashu.db")
latest = pd.read_sql("SELECT MAX(collected_at) AS t FROM snapshots", con)["t"][0]
cur = pd.read_sql("SELECT station_id, available_bikes FROM snapshots WHERE collected_at=?", con, params=[latest])
st  = pd.read_sql("SELECT station_id, name, lat, lon FROM stations", con)
con.close()

ts = pd.to_datetime(latest); hour = ts.hour; is_weekend = ts.dayofweek >= 5
tgt = pd.read_csv("target_inventory.csv")
tgt = tgt[(tgt.is_weekend == is_weekend) & (tgt.hour == hour)][["station_id", "target_bikes"]]
df = cur.merge(tgt, on="station_id", how="left").merge(st, on="station_id")
df["target_bikes"] = df["target_bikes"].fillna(0)
df["need"] = df["target_bikes"] - df["available_bikes"]

receivers = df[df.need > 0].nlargest(N, "need").copy()
receivers["want"] = receivers["need"].astype(int)
T = int(receivers["want"].sum())
donors = df[df.need < 0].copy()
donors["surplus"] = (-donors["need"]).astype(int)
donors = donors.nlargest(M, "surplus")
donors["pickup"] = donors["surplus"].clip(upper=TRUCK_CAP)

nodes  = [("DEPOT", df.lat.mean(), df.lon.mean(), 0, "depot")]
nodes += [(r["name"], r.lat, r.lon, int(r.pickup), "donor") for _, r in donors.iterrows()]
nodes += [(r["name"], r.lat, r.lon, -int(r.want), "recv") for _, r in receivers.iterrows()]
names=[x[0] for x in nodes]; LAT=[x[1] for x in nodes]; LON=[x[2] for x in nodes]
demand=[x[3] for x in nodes]; kind=[x[4] for x in nodes]; n=len(nodes)

def km(i,j):
    R=6371.0; rad=np.radians
    dlat=rad(LAT[j]-LAT[i]); dlon=rad(LON[j]-LON[i])
    h=np.sin(dlat/2)**2+np.cos(rad(LAT[i]))*np.cos(rad(LAT[j]))*np.sin(dlon/2)**2
    return 2*R*np.arcsin(np.sqrt(h))
D=[[0 if (i==j or i==0 or j==0) else int(km(i,j)*1000) for j in range(n)] for i in range(n)]

mgr=pywrapcp.RoutingIndexManager(n,1,0); rt=pywrapcp.RoutingModel(mgr)
tc=rt.RegisterTransitCallback(lambda a,b: D[mgr.IndexToNode(a)][mgr.IndexToNode(b)])
rt.SetArcCostEvaluatorOfAllVehicles(tc)
dc=rt.RegisterUnaryTransitCallback(lambda a: demand[mgr.IndexToNode(a)])
rt.AddDimensionWithVehicleCapacity(dc,0,[TRUCK_CAP],True,"Load")

BIG=10_000_000
for node in range(1,n):
    if kind[node]=="donor": rt.AddDisjunction([mgr.NodeToIndex(node)], 0)     # free to skip
    else:                   rt.AddDisjunction([mgr.NodeToIndex(node)], BIG)   # serve all deliveries

prm=pywrapcp.DefaultRoutingSearchParameters()
prm.first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
prm.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
prm.time_limit.FromSeconds(8)
sol=rt.SolveWithParameters(prm)
if not sol: raise SystemExit("No feasible route found.")

order=[]; idx=rt.Start(0)
while not rt.IsEnd(idx):
    nd=mgr.IndexToNode(idx)
    if nd!=0: order.append(nd)
    idx=sol.Value(rt.NextVar(idx))
dist=sum(km(order[k],order[k+1]) for k in range(len(order)-1))
delivered=sum(-demand[nd] for nd in order if kind[nd]=="recv")

print(f"OPTIMIZED v2 (solver chooses donors) — {latest} ({'weekend' if is_weekend else 'weekday'} {hour}:00)")
print(f"stops {len(order)} | distance {dist:.1f} km | delivered {delivered}/{T}   (greedy 42.0, v1 53.9)\n")
load=0
for k,nd in enumerate(order,1):
    load+=demand[nd]
    act=f"+{demand[nd]} pick up" if demand[nd]>0 else f"{demand[nd]} drop off"
    print(f"{k:2d}. {names[nd]:<26} {act:<14} load={load}")

m=folium.Map(location=[df.lat.mean(),df.lon.mean()],zoom_start=12)
folium.PolyLine([(LAT[i],LON[i]) for i in order],color="blue",weight=3,opacity=0.7).add_to(m)
for k,nd in enumerate(order,1):
    folium.CircleMarker((LAT[nd],LON[nd]),radius=7,fill=True,fill_opacity=0.9,
        color="green" if demand[nd]>0 else "red",
        popup=f"{k}. {names[nd]} ({demand[nd]:+d})").add_to(m)
    folium.map.Marker((LAT[nd],LON[nd]),icon=folium.DivIcon(
        html=f'<div style="font-size:11px;font-weight:bold;color:black">{k}</div>')).add_to(m)
m.save("route_map_optimized.html")
print("\nSaved route_map_optimized.html")
