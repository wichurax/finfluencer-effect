"""Lists each channel's uploads in the study window and saves metadata plus transcript.

One JSON file per video in data/videos/<channel>/, so a rerun only fetches what is missing.
"""

import json
import os
import time
from collections.abc import Iterator
from datetime import datetime, timezone

from yt_dlp import YoutubeDL
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import DownloadError

from .config import CHANNELS, DATA, STUDY_END, STUDY_START, Channel

VIDEOS = DATA / "videos"
# Stop scanning a channel after this many uploads in a row older than the window.
OLDER_IN_A_ROW = 3
# Seconds between requests, and the pauses after YouTube's "confirm you're not a bot" wall.
PAUSE = 5
BOT_WALL_FIRST_WAIT = 300
BOT_WALL_MAX_WAIT = 1800
# Optional: read YouTube cookies from this browser ("firefox", "edge", ...). It gets past the bot
# check, but ties the downloads to that browser's Google account, which YouTube may flag.
COOKIES_BROWSER = os.environ.get("YT_COOKIES_BROWSER")


def _flat_list(channel: Channel, limit: int) -> list[dict]:
    opts = {"extract_flat": "in_playlist", "quiet": True, "playlistend": limit, "no_warnings": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/@{channel.handle}/videos", download=False)
    return [e for e in info.get("entries") or [] if e.get("id")]


def _transcript_from_json3(raw: bytes) -> str:
    data = json.loads(raw)
    words = (seg.get("utf8", "") for ev in data.get("events", []) for seg in ev.get("segs") or [])
    return " ".join(" ".join(words).split())


def _download_with_backoff(ydl: YoutubeDL, url: str) -> bytes:
    for wait in (30, 90, 240, None):
        try:
            return ydl.urlopen(url).read()
        except HTTPError as e:
            if e.status != 429 or wait is None:
                raise
            print(f"  429 from YouTube, waiting {wait}s", flush=True)
            time.sleep(wait)
    raise AssertionError("unreachable")


def _pick_captions(info: dict, lang: str) -> tuple[str | None, str | None]:
    """URL of the json3 track: manual captions first, then the untranslated speech recognition."""
    candidates = [
        ("manual", (info.get("subtitles") or {}).get(lang)),
        ("auto", (info.get("automatic_captions") or {}).get(f"{lang}-orig")),
        ("auto", (info.get("automatic_captions") or {}).get(lang)),
    ]
    for source, formats in candidates:
        for f in formats or []:
            if f.get("ext") == "json3":
                return f["url"], source
    return None, None


def _fetch_one(video_id: str, channel: Channel) -> dict:
    lang = channel.lang
    opts = {
        "quiet": True,
        "no_warnings": True,
        # Original-language titles; YouTube otherwise machine-translates them for the client.
        "extractor_args": {"youtube": {"lang": [lang]}},
        # Bun runs YouTube's player JavaScript, so yt-dlp can use the regular web client.
        "js_runtimes": {"bun": {}},
    }
    if COOKIES_BROWSER:
        opts["cookiesfrombrowser"] = (COOKIES_BROWSER,)
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        url, source = _pick_captions(info, lang)
        transcript = _transcript_from_json3(_download_with_backoff(ydl, url)) if url else None

    published = info.get("release_timestamp") or info.get("timestamp")
    return {
        "id": video_id,
        "channel": channel.key,
        "title": info.get("title"),
        "published_ts": published,
        "published_utc": datetime.fromtimestamp(published, timezone.utc).isoformat() if published else None,
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "live_status": info.get("live_status"),
        "transcript_source": source,
        "transcript": transcript,
    }


def fetch_channel(channel: Channel, limit: int = 2000) -> Iterator[bool]:
    """Fetches one upload per step and yields whether that step called YouTube."""
    out_dir = VIDEOS / channel.key
    out_dir.mkdir(parents=True, exist_ok=True)
    start_ts = datetime.combine(STUDY_START, datetime.min.time(), timezone.utc).timestamp()
    end_ts = datetime.combine(STUDY_END, datetime.min.time(), timezone.utc).timestamp()

    entries = _flat_list(channel, limit)
    print(f"[{channel.key}] {len(entries)} uploads listed", flush=True)
    yield True
    older, saved, skipped = 0, 0, 0
    for i, entry in enumerate(entries):
        path = out_dir / f"{entry['id']}.json"
        if path.exists():
            video = json.loads(path.read_text(encoding="utf-8"))
        else:
            video = _fetch_with_backoff(entry["id"], channel)
            yield True
            if video is None:
                skipped += 1
                continue
        ts = video.get("published_ts")
        if ts and ts < start_ts:
            older += 1
            if older >= OLDER_IN_A_ROW:
                break
            continue
        older = 0
        if not path.exists() and ts and ts < end_ts:
            path.write_text(json.dumps(video, ensure_ascii=False), encoding="utf-8")
            saved += 1
        if i % 25 == 0:
            print(f"[{channel.key}] {i}/{len(entries)} at {video.get('published_utc')}", flush=True)
    print(f"[{channel.key}] done, {saved} new videos saved, {skipped} skipped (rerun to retry)", flush=True)


def _fetch_with_backoff(video_id: str, channel: Channel) -> dict | None:
    """Waits out YouTube's bot check on the same video, however long it lasts."""
    wait = BOT_WALL_FIRST_WAIT
    while True:
        try:
            return _fetch_one(video_id, channel)
        except (DownloadError, HTTPError) as e:
            message = str(e)
            if "not a bot" in message or "botem" in message or "429" in message:
                print(f"[{channel.key}] blocked by YouTube, pausing {wait}s", flush=True)
                time.sleep(wait)
                wait = min(wait * 2, BOT_WALL_MAX_WAIT)
                continue
            # Members-only, removed or age-gated uploads.
            print(f"[{channel.key}] {video_id} skipped: {message[:120]}", flush=True)
            return None


def load_videos() -> list[dict]:
    videos = []
    for path in sorted(VIDEOS.glob("*/*.json")):
        videos.append(json.loads(path.read_text(encoding="utf-8")))
    return videos


def fetch_all(only: list[str] | None = None) -> None:
    """Channels take turns, one upload each, so a partial run covers every channel evenly."""
    turns = {c.key: fetch_channel(c) for c in CHANNELS if not only or c.key in only}
    while turns:
        for key in list(turns):
            try:
                used_network = next(turns[key])
            except StopIteration:
                del turns[key]
                continue
            if used_network:
                time.sleep(PAUSE)
