import sqlite3, pandas as pd
import folium

con = sqlite3.connect("tashu.db")
df = pd.read_sql("""
    SELECT s.name, s.lat, s.lon, sn.available_bikes AS bikes
    FROM stations s
    JOIN snapshots sn ON s.station_id = sn.station_id
    WHERE sn.collected_at = (SELECT MAX(collected_at) FROM snapshots)
""", con)
ts = pd.read_sql("SELECT MAX(collected_at) AS t FROM snapshots", con)["t"][0]
con.close()

df = df.dropna(subset=["lat", "lon"])
df["bikes"] = df["bikes"].fillna(0).astype(int)

def color(b):
    if b == 0: return "red"        # empty
    if b <= 2: return "orange"     # low
    return "blue"                  # ok

m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], zoom_start=12)
for _, r in df.iterrows():
    folium.CircleMarker(
        location=[r["lat"], r["lon"]], radius=3,
        color=color(r["bikes"]), fill=True, fill_opacity=0.8,
        popup=f'{r["name"]}: {r["bikes"]}대',
    ).add_to(m)

m.save("empty_map.html")
print(f"{ts} 기준 — 빈 정류장 {(df['bikes']==0).sum()} / {len(df)} 곳")
print("Saved empty_map.html  (빨강=0대, 주황=1~2대, 파랑=3대+)")
