import sqlite3, pandas as pd
import folium
con = sqlite3.connect("tashu.db")
df = pd.read_sql("""SELECT s.station_id, s.name, s.lat, s.lon, sn.available_bikes AS bikes
    FROM stations s JOIN snapshots sn ON s.station_id=sn.station_id""", con)
con.close()
g = df.groupby(["station_id","name","lat","lon"]).agg(
    empty_pct=("bikes", lambda x:(x==0).mean()*100), avg_bikes=("bikes","mean")
    ).reset_index().dropna(subset=["lat","lon"])
def color(p):
    if p>=80: return "darkred"
    if p>=40: return "red"
    if p>=10: return "orange"
    return "blue"
m = folium.Map(location=[g["lat"].mean(), g["lon"].mean()], zoom_start=12)
for _, r in g.iterrows():
    folium.CircleMarker(location=[r["lat"], r["lon"]], radius=3, color=color(r["empty_pct"]),
        fill=True, fill_opacity=0.8,
        popup=f'{r["name"]}: {r["empty_pct"]:.0f}% empty, avg {r["avg_bikes"]:.1f}').add_to(m)
title='''<div style="position:fixed;top:10px;left:60px;z-index:9999;background:white;padding:8px 12px;border:2px solid #555;border-radius:6px;font-size:15px;">
<b>Daejeon Tashu — station imbalance priority</b><br><span style="font-size:12px;">color = % of observed time a station had 0 bikes (red = needs rebalancing)</span></div>'''
legend='''<div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:white;padding:8px 12px;border:2px solid #555;border-radius:6px;font-size:13px;">
<b>% of time empty</b><br>
<span style="color:darkred;">&#9679;</span> 80%+ (almost always empty)<br>
<span style="color:red;">&#9679;</span> 40&ndash;80%<br>
<span style="color:orange;">&#9679;</span> 10&ndash;40%<br>
<span style="color:blue;">&#9679;</span> under 10% (well-stocked)</div>'''
m.get_root().html.add_child(folium.Element(title))
m.get_root().html.add_child(folium.Element(legend))
m.save("fig3_priority_map.html")
print("Saved fig3_priority_map.html")
