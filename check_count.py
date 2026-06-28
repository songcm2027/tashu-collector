import sqlite3, pandas as pd
con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT kiosk_id, count FROM snapshots", con)
con.close()
changed = df.groupby("kiosk_id")["count"].nunique()
print(f"Stations whose count ever changed: {(changed > 1).sum()} out of {len(changed)}")
print(f"Most distinct values any one station had: {changed.max()}")
