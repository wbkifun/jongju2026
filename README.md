# 자전거 국토종주 2026 — 웹 지도 문서

인천 아라서해갑문 → 부산 낙동강하구둑 633km 국토종주 기록을 지도 위에 표시하는 정적 웹문서입니다.

## 구성

```
site/
├── index.html          # 웹문서 본체 (지도 + 모든 표시 로직)
├── data.js             # 자동 생성 데이터 (사진/일자/인증센터/고개) + 설정
├── photos/
│   ├── thumb/*.webp    # 썸네일 (긴 변 320px, 총 ~1.5MB)
│   └── web/*.webp      # 클릭 시 새 탭으로 열리는 웹용 사진 (긴 변 1920px, 총 ~50MB)
└── tools/              # 데이터 재생성 스크립트
    ├── extract_exif.py     # 원본 jpg에서 날짜·GPS 추출 → exif_data.json
    ├── make_web_images.py  # 원본 jpg → WebP 썸네일/웹용 변환
    ├── build_data.py       # exif + 좌표 → data.js 생성
    └── coords_osm.json     # 인증센터 26곳·고개 좌표 (OpenStreetMap 조회 결과)
```

## 표시 내용

- **날짜별 구간**: 6일(5.29, 6.1~6.5) 구간을 서로 다른 색의 굵은 선으로 표시, 구간 중간에 같은 색으로 날짜 라벨("6.2(화)" 형식). 상단 날짜 칩을 누르면 해당 구간 표시/숨김.
- **인증센터 26곳**: 빨간 원 + 이름 라벨.
- **고개 7곳**: 삼각형 + "이화령(통과)" 형식 라벨. 통과=녹색, 우회=갈색.
- **사진 101장**: 촬영 위치에 날짜 색 점. 지도를 확대하면 보조선으로 연결된 썸네일이 나타나고, 클릭하면 새 탭에 사진이 열립니다.
- **URL로 위치 공유**: `index.html?lat=36.66&lng=128.125&z=14` 형식으로 특정 위치·배율을 바로 열 수 있습니다.

## 사진 포맷 (WebP를 쓰는 이유)

스마트폰 원본 JPG는 장당 3~5MB로 101장 = 약 400MB라 웹에 부적합합니다.
**WebP**는 동일 화질에서 JPEG보다 25~35% 작고 모든 최신 브라우저가 지원합니다.

| 용도 | 크기 | 품질 | 장당 용량 |
|---|---|---|---|
| 썸네일 | 긴 변 320px | q75 | ~15KB |
| 새 탭 보기 | 긴 변 1920px | q82 | ~500KB |

원본 JPG는 웹에 올리지 않고 보관용으로만 둡니다. (꼭 원본을 링크하고 싶으면
`photos/orig/`에 복사하고 `index.html`의 `openPhoto` 경로를 바꾸면 됩니다.)

## 직접 입력해야 하는 두 가지 (data.js 맨 위 CONFIG)

1. **실제 주행거리**: `"distanceKm": "?"` ← 자전거 앱(커넥티드랩)에 기록된 실제 km를 입력.
   (사진 GPS 직선 합산은 약 424km로 실주행보다 짧아 표시하지 않았습니다.)
2. **카카오 지도 키**: `"kakaoAppKey": ""` ← 비워 두면 OpenStreetMap으로 표시되고,
   키를 넣으면 카카오(다음) 지도로 자동 전환됩니다.

### 카카오 지도 키 발급 (무료, 5분)

1. https://developers.kakao.com 로그인 → 내 애플리케이션 → 애플리케이션 추가
2. [앱 설정 > 플랫폼 > Web] 에서 사이트 도메인 등록
   (예: `http://localhost:8765`, `http://라즈베리파이IP:8765`, 실제 공개 도메인)
3. [제품 설정 > 카카오맵] 활성화 ON
4. [앱 키] 중 **JavaScript 키**를 복사해 `data.js`의 `kakaoAppKey`에 입력

무료 쿼터(지도 일 30만 호출)는 개인 여행기 용도로 사실상 무제한입니다.

## 로컬에서 보기

```bash
cd site && python3 -m http.server 8765
# 같은 네트워크에서: http://<라즈베리파이IP>:8765/
```

## 데이터 재생성 (사진 추가/변경 시)

```bash
python3 tools/extract_exif.py > tools/exif_data.json   # 경로는 스크립트 상단 참고
python3 tools/make_web_images.py
python3 tools/build_data.py
```

## 웹호스팅 검토

### 라즈베리파이 4B에 호스팅해도 되는가? → 됩니다

걱정하신 "지도와 사진 때문에 느려지는" 문제는 생각보다 작습니다:

- **지도 타일은 Pi를 거치지 않습니다.** 카카오/OSM 타일은 방문자 브라우저가
  카카오 CDN에서 직접 받아오므로 Pi 부담이 전혀 없습니다.
- **Pi가 서빙하는 것은 HTML+데이터+사진뿐**: 첫 화면 로딩 ≈ index.html + data.js +
  보이는 썸네일 일부 = **2MB 미만**. 사진 클릭 시에만 ~500KB씩 추가 전송.
- RPi4B + nginx는 정적 파일을 초당 수천 요청까지 처리합니다. 개인 여행기
  트래픽(동시 방문 수십 명)에는 성능이 남아돕니다.

**진짜 병목은 Pi가 아니라 집 인터넷의 업로드 속도입니다.**
업로드 100Mbps(대칭형)면 동시 방문 10명도 쾌적하고, 10~20Mbps(비대칭)면
사진 열람이 느릴 수 있습니다. 그 외 부담: 공유기 포트포워딩, DDNS, HTTPS 인증서, 24시간 가동.

### 추천 방안 (간단한 순)

| 방안 | 비용 | 속도 | 비고 |
|---|---|---|---|
| **① GitHub Pages** | 무료 | 빠름(CDN) | 사이트 51MB라 여유. `git push`로 끝. 추천 |
| ② Cloudflare Pages | 무료 | 매우 빠름(CDN) | ①과 비슷, 한국 엣지가 더 가까움 |
| ③ Pi + Cloudflare Tunnel | 무료 | 중간 | 포트포워딩·DDNS 불필요, 정적 파일 CDN 캐싱돼 Pi 부담↓ |
| ④ Pi + nginx + 포트포워딩 + DDNS | 무료 | 집 업로드 속도에 좌우 | 가장 손이 많이 감, 보안 관리 필요 |

개인적으로 **① GitHub Pages를 추천**합니다 — Pi는 빌드(사진 변환)용으로 쓰고,
완성된 `site/` 폴더만 올리면 전 세계 CDN으로 서빙됩니다. 카카오 개발자 콘솔에
`https://<계정>.github.io` 도메인만 등록하면 됩니다.

Pi에 직접 호스팅하려면 ③ Cloudflare Tunnel 방식이 포트 개방 없이 안전합니다:

```bash
sudo apt install nginx
sudo cp -r site /var/www/jongju
# /etc/nginx/sites-available/jongju 에서 root /var/www/jongju 지정
# 사진 캐시 헤더: location /photos/ { expires 30d; }
# cloudflared tunnel 로 외부 공개 (Cloudflare 계정 + 도메인 필요)
```
