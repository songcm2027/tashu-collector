import sqlite3, pandas as pd

THRESH = 10   # |change| >= 10 bikes in one ~15-min step => likely an operator truck, not organic demand

con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()
df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])

g = df.groupby("station_id")
df["delta"]   = g["available_bikes"].diff()
df["gap_min"] = g["t"].diff().dt.total_seconds() / 60

normal = df["gap_min"].between(1, 40)                       # ignore big collection gaps
df["is_operator"] = normal & (df["delta"].abs() >= THRESH)  # implausible organic change

df["pickup_raw"]   = (-df["delta"]).clip(lower=0)                  # drops = rentals
df["pickup_clean"] = df["pickup_raw"].where(~df["is_operator"])    # remove flagged jumps

flagged = int(df["is_operator"].sum())
raw_total = df["pickup_raw"].sum()
share = df.loc[df["is_operator"], "pickup_raw"].sum() / raw_total * 100
print(f"Normal-cadence intervals : {int(normal.sum())}")
print(f"Flagged as operator/anomaly (|delta|>={THRESH}): {flagged}  ({flagged/normal.sum()*100:.1f}% of intervals)")
print(f"Raw 'demand' total       : {raw_total:.0f}")
print(f"Clean demand total       : {df['pickup_clean'].sum():.0f}")
print(f"=> {share:.1f}% of your raw demand was actually big jumps (operator/anomaly), now removed\n")

print("Largest flagged changes (sanity check):")
big = df[df["is_operator"]].assign(absd=df["delta"].abs()).sort_values("absd", ascending=False)
print(big[["t", "station_id", "available_bikes", "delta"]].head(8).to_string(index=False))
