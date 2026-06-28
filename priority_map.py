import sqlite3, pandas as pd
import folium

con = sqlite3.connect("tashu.db")
df = pd.read_sql("""
    SELECT s.station_id, s.name, s.lat, s.lon, sn.available_bikes AS bikes
    FROM stations s JOIN snapshots sn ON s.station_id = sn.station_id
""", con)
con.close()

g = df.groupby(["station_id", "name", "lat", "lon"]).agg(
    empty_pct=("bikes", lambda x: (x == 0).mean() * 100),
    avg_bikes=("bikes", "mean")).reset_index().dropna(subset=["lat", "lon"])

def color(p):
    if p >= 80: return "darkred"
    if p >= 40: return "red"
    if p >= 10: return "orange"
    return "blue"

m = folium.Map(location=[g["lat"].mean(), g["lon"].mean()], zoom_start=12)
for _, r in g.iterrows():
    folium.CircleMarker(
        location=[r["lat"], r["lon"]], radius=3,
        color=color(r["empty_pct"]), fill=True, fill_opacity=0.8,
        popup=f'{r["name"]}: {r["empty_pct"]:.0f}% 빈시간, 평균 {r["avg_bikes"]:.1f}대',
    ).add_to(m)

title_html = '''
<div style="position:fixed; top:10px; left:60px; z-index:9999; background:white;
 padding:8px 12px; border:2px solid #555; border-radius:6px; font-size:15px;">
<b>대전 타슈 대여소 불균형 우선순위</b><br>
<span style="font-size:12px;">색 = 관측기간 중 '자전거 0대'였던 시간 비율 (빨강 = 재배치 필요)</span>
</div>'''
legend_html = '''
<div style="position:fixed; bottom:30px; left:30px; z-index:9999; background:white;
 padding:8px 12px; border:2px solid #555; border-radius:6px; font-size:13px;">
<b>빈 시간 비율</b><br>
<span style="color:darkred;">&#9679;</span> 80%+ (거의 항상 빔)<br>
<span style="color:red;">&#9679;</span> 40–80%<br>
<span style="color:orange;">&#9679;</span> 10–40%<br>
<span style="color:blue;">&#9679;</span> 10% 미만 (충분)
</div>'''
m.get_root().html.add_child(folium.Element(title_html))
m.get_root().html.add_child(folium.Element(legend_html))
m.save("priority_map.html")
print("Saved priority_map.html (제목+범례 포함)")
