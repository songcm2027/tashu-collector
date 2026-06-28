import sqlite3, pandas as pd
import matplotlib
matplotlib.use("Agg")            # save charts to file (no popup window)
import matplotlib.pyplot as plt

con = sqlite3.connect("tashu.db")
stations = pd.read_sql("SELECT * FROM stations", con)
caps = pd.read_sql("SELECT kiosk_id, MAX(count) AS docks FROM snapshots GROUP BY kiosk_id", con)
con.close()

stations["district"] = stations["district"].str.replace(r"\s+", "", regex=True)
df = stations.merge(caps, on="kiosk_id")

print("Total docks in the system:", int(df["docks"].sum()))
print("Average docks per station :", round(df["docks"].mean(), 1))

print("\n=== 8 biggest stations ===")
print(df.sort_values("docks", ascending=False)[["name","district","docks"]].head(8).to_string(index=False))

print("\n=== Capacity by district ===")
print(df.groupby("district")["docks"].agg(stations="count", total_docks="sum").sort_values("total_docks", ascending=False))

# chart: how big are the stations?
plt.figure(figsize=(8,5))
plt.hist(df["docks"], bins=range(0, int(df["docks"].max())+3, 2), edgecolor="black")
plt.xlabel("Docks per station"); plt.ylabel("Number of stations")
plt.title("Tashu station size distribution")
plt.tight_layout()
plt.savefig("dock_histogram.png", dpi=120)
print("\nSaved dock_histogram.png")
