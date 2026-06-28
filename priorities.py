import sqlite3, pandas as pd

con = sqlite3.connect("tashu.db")
df = pd.read_sql("""
    SELECT s.station_id, s.name, s.district, sn.available_bikes AS bikes
    FROM stations s JOIN snapshots sn ON s.station_id = sn.station_id
""", con)
con.close()

stats = df.groupby(["station_id", "name", "district"]).agg(
    avg_bikes=("bikes", "mean"),
    empty_pct=("bikes", lambda x: (x == 0).mean() * 100),
).reset_index()
stats["avg_bikes"] = stats["avg_bikes"].round(1)
stats["empty_pct"] = stats["empty_pct"].round(0)

print("=== Most often EMPTY this afternoon (need bikes) ===")
print(stats.sort_values(["empty_pct", "avg_bikes"], ascending=[False, True])
      .head(12)[["name", "district", "empty_pct", "avg_bikes"]].to_string(index=False))

print("\n=== Most STOCKED (bikes pile up here) ===")
print(stats.sort_values("avg_bikes", ascending=False)
      .head(12)[["name", "district", "avg_bikes", "empty_pct"]].to_string(index=False))

print("\n=== Empty-station rate by district (%) ===")
dist = (df.groupby("district")["bikes"].apply(lambda x: (x == 0).mean() * 100)
        .round(1).sort_values(ascending=False))
print(dist.to_string())
