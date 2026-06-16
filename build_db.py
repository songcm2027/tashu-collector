import csv, sqlite3, glob

DB = "tashu.db"

def to_int(x):
    try: return int(float(x))
    except (TypeError, ValueError): return None

def to_float(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def district_from_address(addr):
    for tok in (addr or "").split():
        if tok.endswith("구"):
            return tok
    return None

files = sorted(glob.glob("data/avail_*.csv"))
if not files:
    raise SystemExit("data/ 에 avail_*.csv가 없어요. 먼저 collect.py를 실행하세요.")

con = sqlite3.connect(DB)
cur = con.cursor()
cur.executescript("""
DROP TABLE IF EXISTS snapshots;
DROP TABLE IF EXISTS stations;
CREATE TABLE stations (
    station_id TEXT PRIMARY KEY,
    name TEXT, district TEXT, lat REAL, lon REAL, address TEXT
);
CREATE TABLE snapshots (
    collected_at TEXT NOT NULL,
    station_id TEXT NOT NULL,
    available_bikes INTEGER,
    PRIMARY KEY (station_id, collected_at)
);
""")

stations = {}
for fp in files:
    with open(fp, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = (row.get("station_id") or "").strip()
            if not sid:
                continue
            stations[sid] = (sid, row.get("name"),
                             district_from_address(row.get("address")),
                             to_float(row.get("lat")), to_float(row.get("lon")),
                             row.get("address"))
            cur.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?)",
                        (row.get("collected_at_kst"), sid, to_int(row.get("available_bikes"))))

cur.executemany("INSERT OR REPLACE INTO stations VALUES (?,?,?,?,?,?)", list(stations.values()))
cur.execute("CREATE INDEX IF NOT EXISTS idx_snap ON snapshots(station_id, collected_at)")
con.commit()

ns = cur.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
nr = cur.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
nt = cur.execute("SELECT COUNT(DISTINCT collected_at) FROM snapshots").fetchone()[0]
print(f"DB 생성: 정류장 {ns}개, 스냅샷 {nr}행, 수집시각 {nt}개")

print("\n스냅샷별: 전체 대여가능 / 빈 정류장(0대)")
for t, total, empty in cur.execute("""
    SELECT collected_at, SUM(available_bikes),
           SUM(CASE WHEN available_bikes=0 THEN 1 ELSE 0 END)
    FROM snapshots GROUP BY collected_at"""):
    print(f"  {t} | 대여가능 {total}대 | 빈 정류장 {empty}곳")
con.close()
