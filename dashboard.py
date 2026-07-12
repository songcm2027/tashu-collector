import sqlite3, pandas as pd, numpy as np, json, os, re, folium
from datetime import datetime, timezone
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

CAP = 20
WINDOWS = {False: [5, 10, 14], True: [5, 13]}
LAB = {(False,5):"before morning peak",(False,10):"midday reset",(False,14):"before evening peak",
       (True,5):"early morning",(True,13):"before evening peak"}

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
stn = pd.read_sql("SELECT station_id, name, lat, lon FROM stations", con)
con.close()
names = stn.set_index("station_id")["name"]; coord = stn.set_index("station_id")[["lat","lon"]]
df["t"] = pd.to_datetime(df["collected_at"]); latest = df["t"].max()
cur = df[df["t"] == latest][["station_id","available_bikes"]]

total=int(cur["available_bikes"].sum()); empty=int((cur["available_bikes"]==0).sum()); nst=len(cur)
hour=latest.hour; wknd=latest.dayofweek>=5
tgt=pd.read_csv("target_inventory.csv")
tg=tgt[(tgt.is_weekend==wknd)&(tgt.hour==hour)][["station_id","target_bikes"]]
m=cur.merge(tg,on="station_id",how="left"); m["target_bikes"]=m["target_bikes"].fillna(0)
m["need"]=m["target_bikes"]-m["available_bikes"]; m["name"]=m["station_id"].map(names)
to_add=int(m["need"].clip(lower=0).sum())
def rows(d): return [{"name":r["name"],"have":int(r.available_bikes),"target":int(r.target_bikes)} for _,r in d.iterrows()]
short=rows(m.sort_values("need",ascending=False).head(6)); surplus=rows(m.sort_values("need").head(6))

df["hour"]=df["t"].dt.hour; df["wknd"]=df["t"].dt.dayofweek>=5
lvl=df.groupby(["station_id","wknd","hour"])["available_bikes"].mean()
T=tgt[tgt.is_weekend==wknd].pivot_table(index="station_id",columns="hour",values="target_bikes",fill_value=0)
L=lvl.xs(wknd,level="wknd").unstack(fill_value=0)

def km(a,b):
    R=6371.0; rad=np.radians; dlat=rad(b[0]-a[0]); dlon=rad(b[1]-a[1])
    h=np.sin(dlat/2)**2+np.cos(rad(a[0]))*np.cos(rad(b[0]))*np.sin(dlon/2)**2
    return 2*R*np.arcsin(np.sqrt(h))

def route_and_map(recv, don, fname, title):
    if recv.empty or don.empty: return None
    lats=list(recv.lat)+list(don.lat); lons=list(recv.lon)+list(don.lon)
    nodes=[("DEPOT",float(np.mean(lats)),float(np.mean(lons)),0,"depot")]
    for _,r in don.iterrows():  nodes.append((r["name"],float(r.lat),float(r.lon),int(r.qty),"donor"))
    for _,r in recv.iterrows(): nodes.append((r["name"],float(r.lat),float(r.lon),-int(r.qty),"recv"))
    NM=[x[0] for x in nodes]; LA=[x[1] for x in nodes]; LO=[x[2] for x in nodes]; DM=[x[3] for x in nodes]; KD=[x[4] for x in nodes]; n=len(nodes)
    D=[[0 if(i==j or i==0 or j==0) else int(km((LA[i],LO[i]),(LA[j],LO[j]))*1000) for j in range(n)] for i in range(n)]
    mgr=pywrapcp.RoutingIndexManager(n,1,0); rt=pywrapcp.RoutingModel(mgr)
    tc=rt.RegisterTransitCallback(lambda a,b: D[mgr.IndexToNode(a)][mgr.IndexToNode(b)]); rt.SetArcCostEvaluatorOfAllVehicles(tc)
    dc=rt.RegisterUnaryTransitCallback(lambda a: DM[mgr.IndexToNode(a)]); rt.AddDimensionWithVehicleCapacity(dc,0,[CAP],True,"Load")
    for node in range(1,n): rt.AddDisjunction([mgr.NodeToIndex(node)], 0 if KD[node]=="donor" else 10_000_000)
    prm=pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    prm.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromSeconds(5)
    sol=rt.SolveWithParameters(prm)
    if not sol: return None
    order=[]; idx=rt.Start(0)
    while not rt.IsEnd(idx):
        node=mgr.IndexToNode(idx)
        if node!=0: order.append(node)
        idx=sol.Value(rt.NextVar(idx))
    dist=sum(km((LA[order[k]],LO[order[k]]),(LA[order[k+1]],LO[order[k+1]])) for k in range(len(order)-1))
    delivered=sum(-DM[nd] for nd in order if KD[nd]=="recv")
    mp=folium.Map(location=[float(np.mean(LA)),float(np.mean(LO))],zoom_start=12,tiles="cartodbpositron")
    folium.PolyLine([(LA[i],LO[i]) for i in order],color="#2b6cb0",weight=3,opacity=0.6).add_to(mp)
    for k,node in enumerate(order,1):
        pick=DM[node]>0; col="#1b9e77" if pick else "#e5564b"; q=f"+{DM[node]}" if pick else f"{DM[node]}"
        badge=(f'<div style="box-sizing:border-box;width:22px;height:22px;line-height:18px;text-align:center;'
               f'border-radius:5px;background:#fff;color:{col};border:2px solid {col};font-family:sans-serif;'
               f'font-weight:700;font-size:11px;box-shadow:0 1px 3px rgba(0,0,0,.3)">{k}</div>')
        folium.Marker((LA[node],LO[node]),tooltip=f"{k}. {NM[node]} ({q})",
            icon=folium.DivIcon(icon_size=(22,22),icon_anchor=(11,11),html=badge)).add_to(mp)
    ttl=(f'<div style="position:fixed;top:10px;left:55px;z-index:9999;background:#fff;padding:8px 14px;'
         f'border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.18);font-family:sans-serif;font-size:13px;color:#1a202c">'
         f'<b>{title}</b><br>{dist:.1f} km · {len(order)} stops · {delivered} bikes<br>'
         f'<span style="color:#1b9e77">■</span> pick up &nbsp;&nbsp;<span style="color:#e5564b">■</span> drop off</div>')
    mp.get_root().html.add_child(folium.Element(ttl)); os.makedirs("docs",exist_ok=True); mp.save(f"docs/{fname}")
    return {"km":round(dist,1),"stops":len(order),"delivered":int(delivered)}

sched=[]
for i,h in enumerate(WINDOWS[wknd]):
    end=WINDOWS[wknd][i+1] if i+1<len(WINDOWS[wknd]) else 24
    hrs=[x for x in range(h+1,end+1) if x in T.columns] or [h]
    peak=T.reindex(columns=hrs,fill_value=0).max(axis=1)
    c=(L[h] if h in L.columns else peak*0).reindex(peak.index).fillna(0)
    need=(peak-c).clip(lower=0); spare=(c-peak).clip(lower=0)
    recv=need[need>=1].sort_values(ascending=False).head(15).rename("qty").reset_index().merge(coord,left_on="station_id",right_index=True).dropna(subset=["lat","lon"])
    recv["name"]=recv["station_id"].map(names)
    don=spare[spare>=1].sort_values(ascending=False).head(40).rename("qty").reset_index().merge(coord,left_on="station_id",right_index=True).dropna(subset=["lat","lon"])
    don["qty"]=don["qty"].clip(upper=CAP); don["name"]=don["station_id"].map(names)
    fname=f"route_{h:02d}.html"
    info=route_and_map(recv,don,fname,f"{h:02d}:00 rebalancing — {LAB.get((wknd,h),'')}")
    sched.append({"time":f"{h:02d}:00","until":f"{end:02d}:00","label":LAB.get((wknd,h),""),
                  "bikes":int(need.round().sum()),"fill":[{"name":r["name"],"q":int(round(r.qty))} for _,r in recv.head(5).iterrows()],
                  "map":fname if info else None,"km":info["km"] if info else None,"stops":info["stops"] if info else None})

route=None
if os.path.exists("plan.txt"):
    mm=re.search(r"stops (\d+) \| distance ([\d.]+) km \| delivered (\d+)/(\d+)",open("plan.txt").read())
    if mm: route={"stops":int(mm.group(1)),"km":float(mm.group(2)),"delivered":int(mm.group(3)),"needed":int(mm.group(4))}

data={"updated":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),"snapshot":str(latest),
      "daytype":"weekend" if wknd else "weekday","stations":nst,"available":total,"empty":empty,
      "empty_pct":round(empty/nst*100,1),"to_add":to_add,"short":short,"surplus":surplus,"route":route,"schedule":sched}
os.makedirs("docs",exist_ok=True); json.dump(data,open("docs/data.json","w"),ensure_ascii=False,indent=2)
print("Wrote docs/data.json + maps:", [w["map"] for w in sched])
