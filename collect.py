import os, csv, sys, time, requests
from datetime import datetime, timezone, timedelta

URL = "https://bikeapp.tashu.or.kr:50041/v1/openapi/station"
KST = timezone(timedelta(hours=9))

def fetch_stations(token, retries=5):
    headers = {"api-token": token}
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(URL, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()["results"]
        except Exception as e:
            print(f"시도 {attempt}/{retries} 실패: {e}")
            if attempt < retries:
                time.sleep(10 * attempt)   # wait longer each try (10s,20s,30s,40s)
    return None

def main():
    token = os.environ.get("TASHU_API_TOKEN")
    if not token:
        sys.exit("TASHU_API_TOKEN이 설정 안 됐어요.")

    stations = fetch_stations(token)
    if not stations:
        print("타슈 서버 연결 실패 — 이번 회차 건너뜀 (다음 회차 자동 재시도).")
        return   # exit 0: a transient blip is a skip, not a red failure

    now = datetime.now(KST)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
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
