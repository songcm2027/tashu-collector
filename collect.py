import os, csv, sys, time, requests
from datetime import datetime, timezone, timedelta

URL = "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/gettasuInfo"
KST = timezone(timedelta(hours=9))

def fetch_items(key, retries=3):
    params = {"serviceKey": key, "pageNo": 1, "numOfRows": 9999}
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(URL, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            head = data["response"]["header"]
            if head["resultCode"] not in ("C00", "00", "0"):
                raise RuntimeError(f"API 오류: {head['resultCode']} {head.get('resultMsg')}")
            return data["response"]["body"]["items"]
        except Exception as e:
            print(f"시도 {attempt}/{retries} 실패: {e}")
            if attempt < retries:
                time.sleep(3 * attempt)
    sys.exit("여러 번 시도했지만 실패했어요.")

def main():
    key = os.environ.get("TASHU_SERVICE_KEY")
    if not key:
        sys.exit("TASHU_SERVICE_KEY가 설정 안 됐어요.")

    now = datetime.now(KST)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    items = fetch_items(key)

    os.makedirs("data", exist_ok=True)
    path = f"data/tashu_{now.strftime('%Y-%m-%d')}.csv"
    new_file = not os.path.exists(path)
    cols = ["collected_at_kst","kiosk_no","kiosk_id","name","district","address","lat","lon","count"]
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(cols)
        for it in items:
            w.writerow([ts, it.get("kioskNo"), it.get("kioskId"), it.get("lcNm"),
                        it.get("signgu"), it.get("adres"),
                        it.get("laCrdnt"), it.get("loCrdnt"), it.get("dfrCo")])
    print(f"[{ts} KST] {len(items)}개 저장 -> {path}")

if __name__ == "__main__":
    main()
