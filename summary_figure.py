import sqlite3, pandas as pd
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "AppleGothic"   # Korean font on macOS
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

con = sqlite3.connect("tashu.db")
snap = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
st = pd.read_sql("SELECT station_id, name, district, lat, lon FROM stations", con)
con.close()
snap["t"] = pd.to_datetime(snap["collected_at"])

emp = (snap.groupby("station_id")["available_bikes"]
       .apply(lambda x: (x == 0).mean() * 100).reset_index(name="emptyrate"))
geo = st.merge(emp, on="station_id").dropna(subset=["lat", "lon"])
per_empty = snap.groupby("collected_at")["available_bikes"].apply(lambda x: (x == 0).mean() * 100)
total = snap.groupby("collected_at")["available_bikes"].sum()
dist = (snap.merge(st, on="station_id").groupby("district")["available_bikes"]
        .apply(lambda x: (x == 0).mean() * 100).sort_values())

snap = snap.sort_values(["station_id", "t"])
snap["pickups"] = (-snap.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
snap["hour"] = snap["t"].dt.hour
ndays = max(snap["t"].dt.date.nunique(), 1)
byhour = snap.groupby("hour")["pickups"].sum() / ndays
span_days = (snap["t"].max() - snap["t"].min()).days

fig = plt.figure(figsize=(12, 8))
gs = gridspec.GridSpec(2, 2, width_ratios=[1.3, 1])
fig.suptitle("대전 공영자전거 '타슈' 불균형 — 데이터 요약", fontsize=18, fontweight="bold")

ax0 = fig.add_subplot(gs[:, 0])
sc = ax0.scatter(geo["lon"], geo["lat"], c=geo["emptyrate"], cmap="RdYlBu_r",
                 s=12, vmin=0, vmax=100, edgecolors="none")
ax0.set_title("정류소별 만성 결핍도 (빨강=자주 빔)")
ax0.set_aspect("equal"); ax0.set_xticks([]); ax0.set_yticks([])
plt.colorbar(sc, ax=ax0, fraction=0.045, pad=0.02, label="빈 시간 비율 (%)")

ax1 = fig.add_subplot(gs[0, 1])
ax1.bar(byhour.index, byhour.values, color="tab:green")
ax1.set_title("시간대별 하루 평균 대여 수요"); ax1.set_xlabel("시(hour)")

ax2 = fig.add_subplot(gs[1, 1])
ax2.barh(dist.index, dist.values, color="tab:red")
ax2.set_title("자치구별 빈 정류소 비율 (%)")
for i, v in enumerate(dist.values):
    ax2.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)

stats = (f"기간 {snap['t'].min():%m/%d}~{snap['t'].max():%m/%d} (약 {span_days}일)  ·  "
         f"전 정류소 {st.shape[0]:,}개  ·  15분 간격 {snap['collected_at'].nunique()}회 수집\n"
         f"빈 정류소 평균 {per_empty.mean():.0f}% / 최대 {per_empty.max():.0f}%   ·   "
         f"대여가능 자전거 평균 {total.mean():.0f}대   ·   수요 피크 오후 6시 전후")
fig.text(0.5, 0.01, stats, ha="center", fontsize=11)

plt.tight_layout(rect=[0, 0.06, 1, 0.95])
plt.savefig("tashu_summary.png", dpi=150)
print("Saved tashu_summary.png")
