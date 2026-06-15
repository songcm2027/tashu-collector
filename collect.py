import os, csv, sys, time, requests
from datetime import datetime, timezone, timedelta

URL = "https://bikeapp.tashu.or.kr:50041/v1/openapi/station"
KST = timezone(timedelta(hours=9))

def fetch_stations(token, retries=3):
    headers = {"api-token": token}
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(URL, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()["results"]
        except Exception as e:
            print(f"시도 {attempt}/{retries} 실패: {e}")
            if attempt < retries:
                time.sleep(3 * attempt)
    sys.exit("여러 번 시도했지만 실패했어요.")

def main():
    token = os.environ.get("TASHU_API_TOKEN")
    if not token:
        sys.exit("TASHU_API_TOKEN이 설정 안 됐어요.")
    now = datetime.now(KST)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    stations = fetch_stations(token)

    os.makedirs("data", exist_ok=True)
    path = f"data/avail_{now.strftime('%Y-%m-%d')}.csv"
    new_file = not os.path.exists(path)
    cols = ["collected_at_kst","station_id","name","lat","lon","address","available_bikes"]
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(cols)
        for s in stations:
            w.writerow([ts, s.get("id"), s.get("name"),
                        s.get("x_pos"), s.get("y_pos"), s.get("address"),
                        s.get("parking_count")])
    print(f"[{ts} KST] {len(stations)}개 저장 -> {path}")

if __name__ == "__main__":
    main()
