import sqlite3
import pandas as pd

con = sqlite3.connect("tashu.db")

# Load the two tables into pandas "DataFrames" (= tables in code)
stations  = pd.read_sql("SELECT * FROM stations",  con)
snapshots = pd.read_sql("SELECT * FROM snapshots", con)
con.close()

print("=== First 5 stations ===")
print(stations.head())

print("\nNumber of stations :", len(stations))
print("Snapshot rows      :", len(snapshots))
print("Collection times   :", snapshots["collected_at"].nunique())
print("Time range         :", snapshots["collected_at"].min(), "->", snapshots["collected_at"].max())

print("\n=== Stations per district ===")
print(stations["district"].value_counts())
