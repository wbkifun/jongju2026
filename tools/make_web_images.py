import os, glob
from PIL import Image, ImageOps

SRC = '/home/khkim/Travel/2026.06_자전거_국토종주'
SITE = os.path.join(SRC, 'site', 'photos')
os.makedirs(os.path.join(SITE, 'thumb'), exist_ok=True)
os.makedirs(os.path.join(SITE, 'web'), exist_ok=True)

def resize_save(img, long_edge, path, q):
    w, h = img.size
    scale = long_edge / max(w, h)
    if scale < 1:
        img = img.resize((round(w*scale), round(h*scale)), Image.LANCZOS)
    img.save(path, 'WEBP', quality=q, method=4)

files = sorted(glob.glob(os.path.join(SRC, '*.jpg')))
for i, f in enumerate(files):
    name = os.path.splitext(os.path.basename(f))[0]
    tp = os.path.join(SITE, 'thumb', name + '.webp')
    wp = os.path.join(SITE, 'web', name + '.webp')
    if os.path.exists(tp) and os.path.exists(wp):
        continue
    img = Image.open(f)
    img = ImageOps.exif_transpose(img).convert('RGB')
    resize_save(img.copy(), 320, tp, 75)
    resize_save(img, 1920, wp, 82)
    print(f'{i+1}/{len(files)} {name}', flush=True)
print('DONE')
