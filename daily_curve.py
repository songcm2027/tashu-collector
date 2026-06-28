import sqlite3, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = sqlite3.connect("tashu.db")
snap = pd.read_sql("SELECT collected_at, available_bikes FROM snapshots", con)
con.close()

snap["t"] = pd.to_datetime(snap["collected_at"])
g = snap.groupby("t")
total = g["available_bikes"].sum()
empty = g["available_bikes"].apply(lambda s: (s == 0).sum())

fig, ax1 = plt.subplots(figsize=(11, 5))
ax1.plot(total.index, total.values, marker="o", ms=3, color="tab:blue")
ax1.set_xlabel("Time"); ax1.set_ylabel("Total available bikes", color="tab:blue")
ax2 = ax1.twinx()
ax2.plot(empty.index, empty.values, marker="o", ms=3, color="tab:red")
ax2.set_ylabel("Empty stations", color="tab:red")
plt.title("Tashu availability over time")
fig.tight_layout()
plt.savefig("daily_curve.png", dpi=120)
print(f"snapshots: {len(total)} | span: {total.index.min()} -> {total.index.max()}")
print("Saved daily_curve.png")
