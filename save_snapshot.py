import os, csv, requests
from datetime import datetime, timezone, timedelta

URL = "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/gettasuInfo"
key = os.environ["TASHU_SERVICE_KEY"]
params = {"serviceKey": key, "pageNo": 1, "numOfRows": 9999}

KST = timezone(timedelta(hours=9))      # 한국 시간
now = datetime.now(KST)
ts = now.strftime("%Y-%m-%d %H:%M:%S")

r = requests.get(URL, params=params, timeout=20)
items = r.json()["response"]["body"]["items"]
print(f"받은 정류장 수: {len(items)}")

os.makedirs("data", exist_ok=True)
path = f"data/tashu_{now.strftime('%Y-%m-%d')}.csv"
new_file = not os.path.exists(path)

cols = ["collected_at_kst","kiosk_no","kiosk_id","name","district","address","lat","lon","count"]
with open(path, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if new_file:
        w.writerow(cols)                # 첫 줄에 제목
    for it in items:
        w.writerow([ts, it.get("kioskNo"), it.get("kioskId"), it.get("lcNm"),
                    it.get("signgu"), it.get("adres"),
                    it.get("laCrdnt"), it.get("loCrdnt"), it.get("dfrCo")])

print(f"저장 완료 -> {path}")
