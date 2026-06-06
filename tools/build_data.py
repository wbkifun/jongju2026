# -*- coding: utf-8 -*-
import json, math, datetime
from collections import defaultdict

BASE = '/home/khkim/Travel/2026.06_자전거_국토종주/site'
photos = json.load(open('/tmp/exif_data.json'))
osm = json.load(open('/tmp/coords_osm.json'))

def hav(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))

# --- centers (OSM verified) ---
centers = [{'name': c['name'], 'lat': c['lat'], 'lon': c['lon']} for c in osm['centers']]

# --- hills (OSM + manual fixes) ---
HILLS = [
    {'name': '이화령',     'status': '통과', 'lat': 36.74851,  'lon': 128.04312},
    {'name': '매협재',     'status': '우회', 'lat': 36.4615,   'lon': 128.2425},   # 상주 경천대 직전
    {'name': '다람재',     'status': '우회', 'lat': 35.699407, 'lon': 128.37636},
    {'name': '무심사',     'status': '우회', 'lat': 35.608967, 'lon': 128.369258}, # 창녕 무심사 임도
    {'name': '박진재',     'status': '통과', 'lat': 35.454521, 'lon': 128.368193},
    {'name': '영아지고개', 'status': '통과', 'lat': 35.4239,   'lon': 128.4127},
    {'name': '모정고개',   'status': '우회', 'lat': 35.353987, 'lon': 128.812162},
]

# --- group photos by day ---
photos.sort(key=lambda p: p['dt'])
days_map = defaultdict(list)
for p in photos:
    days_map[p['dt'][:10]].append(p)
day_keys = sorted(days_map)

COLORS = ['#d62828', '#f77f00', '#2e9e44', '#0077e6', '#8338ec', '#e0218a']
wd = ['월','화','수','목','금','토','일']

# --- insert centers into global photo sequence by minimum detour ---
P = [(p['lat'], p['lon']) for p in photos]
events = [{'kind': 'photo', 'p': p} for p in photos]
for ci, c in enumerate(centers):
    cp = (c['lat'], c['lon'])
    best_i, best_cost = 0, hav(cp, P[0])           # before first
    for i in range(1, len(P)):
        cost = hav(P[i-1], cp) + hav(cp, P[i]) - hav(P[i-1], P[i])
        if cost < best_cost:
            best_i, best_cost = i, cost
    if hav(P[-1], cp) < best_cost:
        best_i = len(P)
    c['_ins'] = best_i + ci * 1e-6   # keep route order among ties

# build per-day event lists
day_of_photo_idx = {}
idx = 0
for dk in day_keys:
    for p in days_map[dk]:
        day_of_photo_idx[idx] = dk
        idx += 1

def day_for_insert(ins):
    i = int(ins)
    if i <= 0: return day_keys[0]
    if i >= len(P): return day_keys[-1]
    d_prev, d_next = day_of_photo_idx[i-1], day_of_photo_idx[i]
    if d_prev == d_next: return d_prev
    cp = next(c for c in centers if abs(c.get('_ins', -1) - ins) < 1e-9)
    cpt = (cp['lat'], cp['lon'])
    return d_prev if hav(P[i-1], cpt) <= hav(cpt, P[i]) else d_next

DAYS = []
for di, dk in enumerate(day_keys):
    ps = days_map[dk]
    y, m, d = map(int, dk.split(':'))
    label = f"{m}.{d}({wd[datetime.date(y,m,d).weekday()]})"
    # merge photos + centers assigned to this day, ordered along route
    evts = [(i + sum(len(days_map[k]) for k in day_keys[:di]), 'photo', p)
            for i, p in enumerate(ps)]
    for c in centers:
        if day_for_insert(c['_ins']) == dk:
            evts.append((c['_ins'] - 0.5, 'center', c))
    evts.sort(key=lambda e: e[0])
    path = [{'lat': e[2]['lat'], 'lng': e[2]['lon']} for e in evts]
    dist = sum(hav((path[i]['lat'], path[i]['lng']), (path[i+1]['lat'], path[i+1]['lng']))
               for i in range(len(path)-1))
    DAYS.append({
        'date': label, 'color': COLORS[di],
        'path': path, 'approxKm': round(dist, 1),
        'photos': [{'f': p['file'].replace('.jpg',''), 'lat': p['lat'], 'lng': p['lon'],
                    't': p['dt'][11:16]} for p in ps],
    })

for c in centers: c.pop('_ins', None)

data = {
    'CONFIG': {
        'title': '자전거 국토종주 2026',
        'period': '2026년 5.29(금), 6.1(월)~6.5(금)',
        'distanceKm': '?',   # <-- 자전거 앱의 실제 주행거리(km)를 적어 주세요
        'bike': '커넥티드랩 듄드라이브 플러스 모션 (+ 자동변속)',
        'kakaoAppKey': '',   # <-- 카카오 JavaScript 키를 넣으면 카카오지도로 표시됩니다
    },
    'DAYS': DAYS,
    'CENTERS': [{'name': c['name'], 'lat': c['lat'], 'lng': c['lon'], 'no': i+1}
                for i, c in enumerate(centers)],
    'HILLS': [{'name': h['name'], 'status': h['status'], 'lat': h['lat'], 'lng': h['lon']}
              for h in HILLS],
}

with open(BASE + '/data.js', 'w') as f:
    f.write('// 자전거 국토종주 2026 — 자동 생성 데이터 (build_data.py)\n')
    for k in ['CONFIG', 'DAYS', 'CENTERS', 'HILLS']:
        f.write(f'const {k} = ' + json.dumps(data[k], ensure_ascii=False,
                separators=(',', ':') if k == 'DAYS' else (',', ': '), indent=None if k=='DAYS' else 1) + ';\n')

for d in DAYS:
    print(d['date'], 'photos:', len(d['photos']), 'path pts:', len(d['path']), f"~{d['approxKm']} km")
print('total approx', round(sum(d['approxKm'] for d in DAYS), 1), 'km (직선 합, 실주행보다 짧음)')
