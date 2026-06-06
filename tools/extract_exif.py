import json, os, glob
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def to_deg(v, ref):
    d = float(v[0]); m = float(v[1]); s = float(v[2])
    deg = d + m/60 + s/3600
    if ref in ('S','W'): deg = -deg
    return round(deg, 6)

out = []
files = sorted(glob.glob('/home/khkim/Travel/2026.06_자전거_국토종주/*.jpg'))
for f in files:
    try:
        img = Image.open(f)
        exif = img._getexif() or {}
        tags = {TAGS.get(k,k): v for k,v in exif.items()}
        dt = tags.get('DateTimeOriginal') or tags.get('DateTime')
        gps_raw = tags.get('GPSInfo')
        lat = lon = None
        if gps_raw:
            gps = {GPSTAGS.get(k,k): v for k,v in gps_raw.items()}
            if 'GPSLatitude' in gps and 'GPSLongitude' in gps:
                lat = to_deg(gps['GPSLatitude'], gps.get('GPSLatitudeRef','N'))
                lon = to_deg(gps['GPSLongitude'], gps.get('GPSLongitudeRef','E'))
        out.append({'file': os.path.basename(f), 'dt': dt, 'lat': lat, 'lon': lon,
                    'w': img.width, 'h': img.height})
    except Exception as e:
        out.append({'file': os.path.basename(f), 'error': str(e)})

print(json.dumps(out, ensure_ascii=False, indent=1))
nogps = [o['file'] for o in out if not o.get('lat')]
print('NO_GPS:', len(nogps), nogps, file=__import__('sys').stderr)
