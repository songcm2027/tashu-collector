import csv, sqlite3, glob

DB = "tashu.db"

def to_int(x):
    try: return int(float(x))
    except (TypeError, ValueError): return None

def to_float(x):
    try: return float(x)
    except (TypeError, ValueError): return None

files = sorted(glob.glob("data/tashu_*.csv"))
if not files:
    raise SystemExit("data/ 에 CSV가 없어요. 먼저 collect.py를 실행하세요.")

con = sqlite3.connect(DB)
cur = con.cursor()
cur.executescript("""
DROP TABLE IF EXISTS snapshots;
DROP TABLE IF EXISTS stations;
CREATE TABLE stations (
    kiosk_id TEXT PRIMARY KEY,
    kiosk_no TEXT, name TEXT, district TEXT, address TEXT, lat REAL, lon REAL
);
CREATE TABLE snapshots (
    collected_at TEXT NOT NULL,
    kiosk_id TEXT NOT NULL,
    count INTEGER,
    PRIMARY KEY (kiosk_id, collected_at)
);
""")

stations = {}
for fp in files:
    with open(fp, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kid = (row.get("kiosk_id") or "").strip()
            if not kid:
                continue
            stations[kid] = (kid, row.get("kiosk_no"), row.get("name"),
                             row.get("district"), row.get("address"),
                             to_float(row.get("lat")), to_float(row.get("lon")))
            cur.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?)",
                        (row.get("collected_at_kst"), kid, to_int(row.get("count"))))

cur.executemany("INSERT OR REPLACE INTO stations VALUES (?,?,?,?,?,?,?)", list(stations.values()))
cur.execute("CREATE INDEX IF NOT EXISTS idx_snap ON snapshots(kiosk_id, collected_at)")
con.commit()

ns = cur.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
nr = cur.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
print(f"DB 생성 완료: 정류장 {ns}개, 스냅샷 {nr}행")

print("\n스냅샷별 전체 자전거 합계:")
for t, cnt, total in cur.execute(
        "SELECT collected_at, COUNT(*), SUM(count) FROM snapshots GROUP BY collected_at"):
    print(f"  {t} | 정류장 {cnt}개 | 자전거 합계 {total}")
con.close()
