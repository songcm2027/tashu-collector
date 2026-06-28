import sqlite3, pandas as pd
con = sqlite3.connect("tashu.db")
snap = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
st = pd.read_sql("SELECT station_id, name, district FROM stations", con)
con.close()
snap["t"] = pd.to_datetime(snap["collected_at"])

span_days = (snap["t"].max() - snap["t"].min()).days
print(f"기간: {snap['t'].min():%Y-%m-%d %H:%M} -> {snap['t'].max():%Y-%m-%d %H:%M}  (약 {span_days}일)")
print(f"수집 시각: {snap['collected_at'].nunique()}회 | 정류소: {st.shape[0]}개")

per = snap.groupby("collected_at")["available_bikes"]
emptypct = per.apply(lambda x: (x == 0).mean() * 100)
total = per.sum()
print(f"빈 정류소 비율: 평균 {emptypct.mean():.0f}% / 최대 {emptypct.max():.0f}%")
print(f"대여가능 자전거: 평균 {total.mean():.0f}대 (최소 {total.min():.0f} ~ 최대 {total.max():.0f})")

m = (snap.groupby("station_id")["available_bikes"]
     .agg(avg="mean", emptyrate=lambda x: (x == 0).mean() * 100)
     .reset_index().merge(st, on="station_id"))
print("\n[만성적으로 비는 정류소 TOP 6]")
print(m.sort_values(["emptyrate", "avg"], ascending=[False, True])
      .head(6)[["name", "district", "emptyrate"]].round(0).to_string(index=False))
print("\n[자전거가 쌓이는 정류소 TOP 6]")
print(m.sort_values("avg", ascending=False).head(6)[["name", "district", "avg"]].round(1).to_string(index=False))

print("\n[자치구별 빈 정류소 비율 %]")
dd = (snap.merge(st, on="station_id").groupby("district")["available_bikes"]
      .apply(lambda x: (x == 0).mean() * 100).round(0).sort_values(ascending=False))
print(dd.to_string())

snap = snap.sort_values(["station_id", "t"])
snap["pickups"] = (-snap.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
snap["hour"] = snap["t"].dt.hour
byhour = snap.groupby("hour")["pickups"].sum().sort_values(ascending=False)
print("\n[대여 수요 피크 시간 TOP 4 (시 : 총대여)]")
print(byhour.head(4).to_string())
