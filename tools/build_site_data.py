# -*- coding: utf-8 -*-
"""data.js 생성: jpg EXIF + gpx 트랙 + 인증센터/고개 좌표 → site/data.js

사용법: python3 build_site_data.py
입력:  ../../jpg/*.jpg  ../../gpx/*.gpx  coords_osm.json
"""
import re, glob, math, json, datetime, os
from collections import defaultdict
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # 2026.06_자전거_국토종주/
SITE = os.path.dirname(HERE)                           # site/

DIST_TOTAL = None         # None이면 GPX 보정 합계(집 왕복 포함)로 자동 계산
KAKAO_KEY = '875c4a314de2705aafb51d65a743dd49'
HOME_MASK_KM = 2.0        # 집 반경 마스킹
COLORS = ['#d62828', '#f77f00', '#2e9e44', '#0077e6', '#8338ec', '#e0218a']
WD = ['월', '화', '수', '목', '금', '토', '일']

def hav(a, b):
    R = 6371.0088
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))

# ---------- 1. EXIF ----------
def to_deg(v, ref):
    deg = float(v[0]) + float(v[1])/60 + float(v[2])/3600
    return -deg if ref in ('S', 'W') else deg

photos = []
for f in sorted(glob.glob(os.path.join(ROOT, 'jpg', '*.jpg'))):
    img = Image.open(f)
    tags = {TAGS.get(k, k): v for k, v in (img._getexif() or {}).items()}
    gps = {GPSTAGS.get(k, k): v for k, v in tags.get('GPSInfo', {}).items()}
    if 'GPSLatitude' not in gps:
        continue
    photos.append({
        'file': os.path.splitext(os.path.basename(f))[0],
        'dt': tags.get('DateTimeOriginal') or tags.get('DateTime'),
        'lat': round(to_deg(gps['GPSLatitude'], gps.get('GPSLatitudeRef', 'N')), 6),
        'lon': round(to_deg(gps['GPSLongitude'], gps.get('GPSLongitudeRef', 'E')), 6),
    })
photos.sort(key=lambda p: p['dt'])

# ---------- 2. GPX ----------
def parse_gpx(f):
    data = open(f).read()
    pts = re.findall(r'<trkpt lat="([\d.]+)" lon="([\d.]+)"><time>([^<]+)</time>', data)
    P = [(float(a), float(b)) for a, b, _ in pts]
    T = [datetime.datetime.fromisoformat(t.replace('Z', '+00:00')) for _, _, t in pts]
    valid = T and T[0].year > 2000
    if valid:
        start = (T[0] + datetime.timedelta(hours=9)).replace(tzinfo=None)
    else:  # 타임스탬프 깨진 파일: mtime - 80분으로 시각 추정
        start = datetime.datetime.fromtimestamp(os.path.getmtime(f)) - datetime.timedelta(minutes=80)
    # GPS 점프 처리: 거리는 쌍별로 점프 구간만 제외, 경로점은 진동(1km 미만 점프)만 버림
    clean, dist = [P[0]], 0
    for i in range(1, len(P)):
        d = hav(P[i-1], P[i])
        dt = (T[i] - T[i-1]).total_seconds() if valid else 1
        jump = d > 0.5 or (dt > 0 and d*1000/dt > 25 and d > 0.05)
        if not jump:
            dist += d
        if jump and hav(clean[-1], P[i]) < 1.0:
            continue   # 진동/노이즈 점 버림 (1km 이상 떨어진 진짜 갭은 유지 → 세그먼트 분리됨)
        clean.append(P[i])
    return {'file': os.path.basename(f), 'pts': clean, 'km': dist, 'start': start}

tracks = [parse_gpx(f) for f in sorted(glob.glob(os.path.join(ROOT, 'gpx', '*.gpx')))]
tracks.sort(key=lambda t: t['start'])

# 집 위치(집_여의도 트랙 시작점) 반경 마스킹
home = next(t for t in tracks if t['file'].startswith('집_'))['pts'][0]
for t in tracks:
    t['pts'] = [p for p in t['pts'] if hav(p, home) > HOME_MASK_KM]

# ---------- 3. Douglas-Peucker 단순화 ----------
def dp(pts, tol):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    imax, dmax = 0, -1
    for i in range(1, len(pts) - 1):
        d = abs(dy*(pts[i][0]-x1) - dx*(pts[i][1]-y1)) / norm
        if d > dmax:
            imax, dmax = i, d
    if dmax > tol:
        return dp(pts[:imax+1], tol)[:-1] + dp(pts[imax:], tol)
    return [pts[0], pts[-1]]

# ---------- 4. 날짜별 묶기 ----------
days_t = defaultdict(list)
for t in tracks:
    days_t[t['start'].strftime('%Y-%m-%d')].append(t)
days_p = defaultdict(list)
for p in photos:
    days_p[p['dt'][:10].replace(':', '-')].append(p)

DAYS = []
for di, dk in enumerate(sorted(days_t)):
    y, m, d = map(int, dk.split('-'))
    label = f"{m}.{d}({WD[datetime.date(y, m, d).weekday()]})"
    segs, km = [], 0
    for t in days_t[dk]:
        km += t['km']
        # 마스킹 등으로 생긴 1km 이상 갭에서 세그먼트 분리
        cur = []
        for p in t['pts']:
            if cur and hav(cur[-1], p) > 1.0:
                segs.append(cur); cur = []
            cur.append(p)
        if cur:
            segs.append(cur)
    segs = [dp(s, 0.00015) for s in segs if len(s) >= 2]
    # 날짜 라벨 위치: 그날 전체 거리의 중간 지점
    flat = [p for s in segs for p in s]
    acc, half, lab = 0, sum(hav(flat[i], flat[i+1]) for i in range(len(flat)-1))/2, flat[len(flat)//2]
    for i in range(1, len(flat)):
        acc += hav(flat[i-1], flat[i])
        if acc >= half:
            lab = flat[i]; break
    DAYS.append({
        'date': label, 'color': COLORS[di], 'km': round(km, 1),
        'labelAt': {'lat': round(lab[0], 5), 'lng': round(lab[1], 5)},
        'paths': [[{'lat': round(a, 5), 'lng': round(b, 5)} for a, b in s] for s in segs],
        'photos': [{'f': p['file'], 'lat': p['lat'], 'lng': p['lon'], 't': p['dt'][11:16]}
                   for p in days_p.get(dk, [])],
    })

# ---------- 5. 인증센터 / 고개 ----------
osm = json.load(open(os.path.join(HERE, 'coords_osm.json')))
CENTERS = [{'name': c['name'], 'lat': c['lat'], 'lng': c['lon'], 'no': i+1}
           for i, c in enumerate(osm['centers'])]
HILLS = [
    {'name': '이화령',     'status': '통과', 'lat': 36.74851,  'lng': 128.04312},
    {'name': '매협재',     'status': '우회', 'lat': 36.4615,   'lng': 128.2425},
    {'name': '다람재',     'status': '우회', 'lat': 35.699407, 'lng': 128.37636},
    {'name': '무심사',     'status': '우회', 'lat': 35.608967, 'lng': 128.369258},
    {'name': '박진재',     'status': '통과', 'lat': 35.454521, 'lng': 128.368193},
    {'name': '영아지고개', 'status': '통과', 'lat': 35.4239,   'lng': 128.4127},
    {'name': '모정고개',   'status': '우회', 'lat': 35.353987, 'lng': 128.812162},
]

CONFIG = {
    'title': '자전거 국토종주 2026',
    'period': '2026년 5.29(금), 6.1(월)~6.5(금)',
    'distanceKm': DIST_TOTAL or str(round(sum(d['km'] for d in DAYS))),
    'bike': '커넥티드랩 듄드라이브 플러스 모션 (+ 자동변속)',
    'kakaoAppKey': KAKAO_KEY,
}

with open(os.path.join(SITE, 'data.js'), 'w') as f:
    f.write('// 자전거 국토종주 2026 — 자동 생성 (tools/build_site_data.py)\n')
    f.write('const CONFIG = ' + json.dumps(CONFIG, ensure_ascii=False, indent=1) + ';\n')
    f.write('const DAYS = ' + json.dumps(DAYS, ensure_ascii=False, separators=(',', ':')) + ';\n')
    f.write('const CENTERS = ' + json.dumps(CENTERS, ensure_ascii=False, indent=1) + ';\n')
    f.write('const HILLS = ' + json.dumps(HILLS, ensure_ascii=False, indent=1) + ';\n')

for d in DAYS:
    print(d['date'], f"{d['km']:6.1f} km", 'segs:', len(d['paths']),
          'pts:', sum(len(s) for s in d['paths']), 'photos:', len(d['photos']))
print('TOTAL', round(sum(d['km'] for d in DAYS), 1), 'km')
print('data.js', os.path.getsize(os.path.join(SITE, 'data.js')) // 1024, 'KB')
