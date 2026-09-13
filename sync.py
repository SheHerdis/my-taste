"""
Sync Pinterest boards -> data/pins.json + images/
Runs inside GitHub Actions. Token comes from the PINTEREST_TOKEN secret.
Boards/pins listed in config.json under exclude_* are skipped.
"""

import colorsys
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

from PIL import Image

API = "https://api.pinterest.com/v5"
TOKEN = os.environ.get("PINTEREST_TOKEN")
if not TOKEN:
    sys.exit("PINTEREST_TOKEN is not set")

CONFIG = json.load(open("config.json", encoding="utf-8"))
EXCL_BOARDS = {b.strip().lower() for b in CONFIG.get("exclude_boards", [])}
EXCL_PINS = set(CONFIG.get("exclude_pins", []))
IMG_W = int(CONFIG.get("image_width", 640))

os.makedirs("data", exist_ok=True)
os.makedirs("images", exist_ok=True)


def get(path, params=None):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code} on {path}: {e.read().decode(errors='ignore')}")


def paginate(path):
    params = {"page_size": 100}
    items = []
    while True:
        d = get(path, params)
        items.extend(d.get("items", []))
        if not d.get("bookmark"):
            return items
        params["bookmark"] = d["bookmark"]


def best_image(pin):
    imgs = ((pin.get("media") or {}).get("images") or {})
    for k in ("1200x", "600x", "400x300", "150x150"):
        if imgs.get(k, {}).get("url"):
            return imgs[k]["url"]
    for v in imgs.values():
        if v.get("url"):
            return v["url"]
    return None


def download(url, pin_id):
    path = f"images/{pin_id}.jpg"
    if os.path.exists(path):
        return path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            im = Image.open(io.BytesIO(r.read())).convert("RGB")
        if im.width > IMG_W:
            im = im.resize((IMG_W, int(im.height * IMG_W / im.width)), Image.LANCZOS)
        im.save(path, "JPEG", quality=82, optimize=True)
        return path
    except Exception as e:
        print(f"  image failed for {pin_id}: {e}")
        return None


def palette(path, n=4):
    """Top n colors of an image, skipping near-white and near-black."""
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((80, 80))
        q = im.quantize(colors=12, method=Image.Quantize.MEDIANCUT).convert("RGB")
        counts = Counter(q.getdata())
        out = []
        for (r, g, b), _ in counts.most_common():
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if v > 0.97 and s < 0.06:
                continue
            if v < 0.08:
                continue
            out.append("#%02x%02x%02x" % (r, g, b))
            if len(out) == n:
                break
        return out
    except Exception:
        return []


def hue_family(hexcol):
    h6 = hexcol.lstrip("#")
    r, g, b = (int(h6[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.12:
        return "neutral"
    d = h * 360
    if d < 15 or d >= 330:
        return "pink"
    if d < 45:
        return "cream"
    if d < 70:
        return "yellow"
    if d < 170:
        return "green"
    if d < 260:
        return "blue"
    return "purple"


def keywords(texts):
    stop = set("the a an and or of for to in on with your my by is it this that from at as be are "
               "free download printable pin pinterest instagram follow ig aesthetic cute not use amazon click "
               "click shop now find finds link etsy canva credit repost www com".split())
    c = Counter()
    for t in texts:
        for w in re.findall(r"[a-zA-Z]{3,}", t.lower()):
            if w not in stop:
                c[w] += 1
    return [w for w, _ in c.most_common(25)]


def main():
    me = get("/user_account")
    print("user:", me.get("username"))
    boards = paginate("/boards")
    out_boards, all_pins = [], []

    for b in boards:
        name = b.get("name", "")
        if name.strip().lower() in EXCL_BOARDS:
            print(f"skip board: {name}")
            continue
        pins = paginate(f"/boards/{b['id']}/pins")
        print(f"board: {name} ({len(pins)})")
        clean = []
        for p in pins:
            pid = p.get("id")
            if pid in EXCL_PINS:
                continue
            src = best_image(p)
            local = download(src, pid) if src else None
            entry = {
                "id": pid,
                "board": name,
                "title": (p.get("title") or "").strip(),
                "description": (p.get("description") or "").strip(),
                "pin_url": f"https://www.pinterest.com/pin/{pid}/",
                "image": local or src,
                "remote": src,
                "colors": palette(local) if local else [],
                "dominant": p.get("dominant_color"),
                "created_at": p.get("created_at"),
            }
            entry["family"] = hue_family(entry["colors"][0]) if entry["colors"] else (
                hue_family(entry["dominant"]) if entry["dominant"] else "neutral")
            clean.append(entry)
            all_pins.append(entry)
        out_boards.append({"id": b["id"], "name": name, "count": len(clean)})

    # overall taste profile
    fam = Counter(p["family"] for p in all_pins)
    swatches = Counter()
    for p in all_pins:
        for c in p["colors"][:2]:
            swatches[c] += 1
    profile = {
        "total": len(all_pins),
        "families": dict(fam.most_common()),
        "palette": [c for c, _ in swatches.most_common(24)],
        "keywords": keywords([p["title"] + " " + p["description"] for p in all_pins]),
    }

    json.dump({"owner": CONFIG.get("owner", ""), "title": CONFIG.get("site_title", "my taste"),
               "username": me.get("username"), "boards": out_boards, "pins": all_pins,
               "profile": profile},
              open("data/pins.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done: {len(all_pins)} pins, {len(out_boards)} boards")


if __name__ == "__main__":
    main()
