import sqlite3
import pandas as pd
import folium

con = sqlite3.connect("tashu.db")
stations = pd.read_sql("SELECT * FROM stations", con)
con.close()

# Clean: remove stray spaces so "서  구" becomes "서구"
stations["district"] = stations["district"].str.replace(r"\s+", "", regex=True)

# Center the map on the average of all station locations
center = [stations["lat"].mean(), stations["lon"].mean()]
m = folium.Map(location=center, zoom_start=12)

# One color per district
colors = {"유성구":"blue", "서구":"red", "중구":"green", "대덕구":"purple", "동구":"orange"}

for _, row in stations.iterrows():
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=4,
        color=colors.get(row["district"], "gray"),
        fill=True, fill_opacity=0.8,
        popup=f'{row["name"]} ({row["district"]})',
    ).add_to(m)

m.save("station_map.html")
print("Saved station_map.html —", len(stations), "stations mapped")
