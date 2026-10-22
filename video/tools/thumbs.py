"""Large thumbnails for the clip: the example video and each channel's most-viewed video.

Run with the project's Python (needs Pillow):  ../.venv/Scripts/python tools/thumbs.py
Writes public/thumbs/<id>.jpg and src/thumbs.json (each channel's top video).
"""

import io
import json
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT.parent / "data" / "videos"


def fetch(url: str) -> bytes | None:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except Exception:  # noqa: BLE001 - a missing thumbnail is reported below
            time.sleep(1 + attempt)
    return None


def main() -> None:
    videos = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(VIDEOS.glob("*/*.json"))]
    top = {}
    for v in videos:
        if v["channel"] not in top or (v.get("view_count") or 0) > (top[v["channel"]].get("view_count") or 0):
            top[v["channel"]] = v
    chosen = {"LGUewAMj5H8"} | {v["id"] for v in top.values()}
    out = ROOT / "public" / "thumbs"
    out.mkdir(parents=True, exist_ok=True)
    missing = []
    for vid in sorted(chosen):
        data = fetch(f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg") or fetch(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg")
        if not data:
            missing.append(vid)
            continue
        img = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = img.size
        if abs(w / h - 4 / 3) < 0.05:  # hqdefault is 4:3 with black bars; crop to 16:9
            band = int(w * 9 / 16)
            img = img.crop((0, (h - band) // 2, w, (h + band) // 2))
        img.save(out / f"{vid}.jpg", quality=88)

    meta = {"top": {ch: {"id": v["id"], "title": v["title"], "views": v.get("view_count")} for ch, v in top.items()}}
    (ROOT / "src" / "thumbs.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(chosen) - len(missing)} thumbnails" + (f", missing: {', '.join(missing)}" if missing else ""))


if __name__ == "__main__":
    main()
