import csv, sqlite3, sys, requests
from datetime import datetime, timedelta, timezone

with open("kma_key.txt") as f:
    KEY = f.read().strip()
URL = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
con = sqlite3.connect("tashu.db")
lo, hi = con.execute("SELECT MIN(collected_at), MAX(collected_at) FROM snapshots").fetchone()
con.close()
start = lo[:10].replace("-", ""); end = hi[:10].replace("-", "")
yest = (datetime.now(timezone(timedelta(hours=9))) - timedelta(days=1)).strftime("%Y%m%d")
end = min(end, yest)
print(f"Fetching 대전 weather {start} ~ {end} ...")

def page(p):
    params = {"serviceKey": KEY, "pageNo": p, "numOfRows": 999, "dataType": "JSON",
              "dataCd": "ASOS", "dateCd": "HR", "startDt": start, "startHh": "00",
              "endDt": end, "endHh": "23", "stnIds": "133"}
    body = requests.get(URL, params=params, timeout=30).json()["response"]["body"]
    return body["items"]["item"], int(body["totalCount"])

items, p = [], 1
while True:
    chunk, total = page(p)
    items += chunk
    if len(items) >= total or not chunk: break
    p += 1

with open("weather.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["datetime", "temp", "precip"])
    for it in items:
        rn = it.get("rn"); rn = rn if rn not in (None, "", " ") else "0"
        w.writerow([it.get("tm"), it.get("ta") or "", rn])
print(f"Saved weather.csv ({len(items)} rows)")
