import sqlite3, pandas as pd

# demand: total system rentals per hour
con = sqlite3.connect("tashu.db")
df = pd.read_sql("SELECT collected_at, station_id, available_bikes FROM snapshots", con)
con.close()
df["t"] = pd.to_datetime(df["collected_at"])
df = df.sort_values(["station_id", "t"])
df["pickups"] = (-df.groupby("station_id")["available_bikes"].diff()).clip(lower=0)
df["hour_ts"] = df["t"].dt.floor("h")
hourly = df.groupby("hour_ts", as_index=False)["pickups"].sum().rename(columns={"pickups": "rentals"})

# weather
w = pd.read_csv("weather.csv")
w["hour_ts"] = pd.to_datetime(w["datetime"])
w["precip"] = pd.to_numeric(w["precip"], errors="coerce").fillna(0)
w["temp"]   = pd.to_numeric(w["temp"], errors="coerce")
w["rain"]   = w["precip"] > 0

w["date"] = w["hour_ts"].dt.date
print("Rain by day (mm):")
print(w.groupby("date")["precip"].sum().to_string(), "\n")

# join + effect
m = hourly.merge(w[["hour_ts", "temp", "precip", "rain"]], on="hour_ts", how="inner")
day = m[(m["hour_ts"].dt.hour >= 6) & (m["hour_ts"].dt.hour <= 22)]

print(f"Matched hours: {len(m)} | rainy hours: {int(m['rain'].sum())} | total rain: {m['precip'].sum():.1f} mm\n")
print("Avg system rentals/hour (daytime 6-22):")
dry = day.loc[~day["rain"], "rentals"].mean()
print(f"  Dry  : {dry:.1f}")
if day["rain"].any():
    wet = day.loc[day["rain"], "rentals"].mean()
    print(f"  Rainy: {wet:.1f}   ({(wet/dry-1)*100:+.0f}% vs dry)")
else:
    print("  Rainy: (no rainy daytime hours in this window)")
print(f"\nRentals vs temperature correlation: {day['rentals'].corr(day['temp']):+.2f}")
