import os, json, requests

URL = "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/gettasuInfo"
key = os.environ["TASHU_SERVICE_KEY"]
params = {"serviceKey": key, "pageNo": 1, "numOfRows": 5}

r = requests.get(URL, params=params, timeout=20)
print("상태코드:", r.status_code)

try:
    data = r.json()
    print("최상위 키:", list(data.keys()))
    print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])
except Exception:
    print(r.text[:1500])
