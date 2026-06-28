import sqlite3, pandas as pd
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "AppleGothic"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()

df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
df["date"] = df["t"].dt.date
df["hour"] = df["t"].dt.hour
df["is_weekend"] = pd.to_datetime(df["date"]).dt.dayofweek >= 5

hourly = df.groupby(["station_id", "date", "is_weekend", "hour"], as_index=False)["pickups"].sum()

# A) weekday vs weekend demand curve (system-wide, per-day average)
sysd = hourly.groupby(["date", "is_weekend", "hour"], as_index=False)["pickups"].sum()
wd = sysd[~sysd["is_weekend"]].groupby("hour")["pickups"].mean()
we = sysd[sysd["is_weekend"]].groupby("hour")["pickups"].mean()
plt.figure(figsize=(10, 5))
plt.plot(wd.index, wd.values, marker="o", label="평일")
plt.plot(we.index, we.values, marker="o", label="주말")
plt.xlabel("시(hour)"); plt.ylabel("하루 평균 대여 수요(전체 대여소)")
plt.title("평일 vs 주말 시간대별 수요"); plt.legend()
plt.tight_layout(); plt.savefig("forecast_weekday_weekend.png", dpi=120)

# B) accuracy test: predict the last COMPLETE day (today is still in progress, so skip it)
dates = sorted(hourly["date"].unique())
test_day = dates[-2]
train = hourly[hourly["date"] != test_day]
test  = hourly[hourly["date"] == test_day]
m1 = train.groupby(["station_id", "hour"], as_index=False)["pickups"].mean().rename(columns={"pickups": "pred_basic"})
m2 = train.groupby(["station_id", "is_weekend", "hour"], as_index=False)["pickups"].mean().rename(columns={"pickups": "pred_wkwe"})
ev = (test.merge(m1, on=["station_id", "hour"], how="left")
          .merge(m2, on=["station_id", "is_weekend", "hour"], how="left"))
ev[["pred_basic", "pred_wkwe"]] = ev[["pred_basic", "pred_wkwe"]].fillna(0)
mae_basic = (ev["pickups"] - ev["pred_basic"]).abs().mean()
mae_wkwe  = (ev["pickups"] - ev["pred_wkwe"]).abs().mean()
kind = "주말" if pd.Timestamp(test_day).dayofweek >= 5 else "평일"
print(f"검증 날짜: {test_day} ({kind})")
print(f"MAE  시간만 모델: {mae_basic:.3f}   평일/주말 구분 모델: {mae_wkwe:.3f}")
print("Saved forecast_weekday_weekend.png")
