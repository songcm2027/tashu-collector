import os, requests

key = os.environ["TASHU_SERVICE_KEY"]
params = {"serviceKey": key, "pageNo": 1, "numOfRows": 5, "type": "json"}

urls = [
    "https://apis.data.go.kr/6300000/openapi2022/tasuInfo",
    "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/getList",
    "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/tasuInfo",
    "https://apis.data.go.kr/6300000/openapi2022/getTasuInfo",
    "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/getTasuInfo",
    "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/list",
]

for u in urls:
    try:
        r = requests.get(u, params=params, timeout=20)
        snippet = " ".join(r.text.split())[:100]
        print(f"[{r.status_code}] {u}")
        print(f"      {snippet}")
    except Exception as e:
        print(f"[ERR] {u} -> {e}")
