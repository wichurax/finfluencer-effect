"""The public labels: what the models said about each video, without the transcripts.

`export` writes labels/ from data/ (the full pipeline's output). `load` does the reverse into an empty data/, so the
analysis runs from the published labels alone. Two CSV files:

- labels/videos.csv: every video in the study (metadata only) and which model labelled it, plus the second model
  that labelled it again for the agreement check, if any.
- labels/labels.csv: one row per stock named in a video, by the main model (`source` = main) or the second one
  (`source` = second).

The quote the model gave as evidence is left out: it is the YouTuber's words. The analysis does not use it.
"""

import json
from pathlib import Path

import pandas as pd

from .agreement import CHECK
from .classify import MENTIONS
from .videos import VIDEOS, load_videos

LABELS = Path(__file__).resolve().parents[2] / "labels"
VIDEO_COLUMNS = ["id", "channel", "title", "published_utc", "published_ts", "duration", "view_count", "like_count",
                 "live_status", "transcript_source"]
RUN_COLUMNS = ["model", "backend", "effort", "classified_at"]
STOCK_COLUMNS = ["company", "yahoo_symbol", "asset_type", "stance", "conviction", "focus"]
# The second opinions: GPT on videos Claude labelled, and Claude on videos GPT labelled.
SECOND_SETS = ("gpt", "claude")


def _records(directory: Path) -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in directory.glob("*.json")}


def export() -> None:
    main = _records(MENTIONS)
    second = {vid: (name, rec) for name in SECOND_SETS for vid, rec in _records(CHECK / name).items()}
    videos, stocks = [], []
    for v in sorted(load_videos(), key=lambda v: (v["channel"], v.get("published_ts") or 0)):
        row = {c: v.get(c) for c in VIDEO_COLUMNS}
        row["has_transcript"] = bool(v.get("transcript"))
        if v["id"] in main:
            row.update({c: main[v["id"]][c] for c in RUN_COLUMNS})
            stocks += [{"video_id": v["id"], "source": "main", **{c: s[c] for c in STOCK_COLUMNS}}
                       for s in main[v["id"]]["stocks"]]
        if v["id"] in second:
            name, rec = second[v["id"]]
            row.update({"second_set": name, **{f"second_{c}": rec[c] for c in RUN_COLUMNS}})
            stocks += [{"video_id": v["id"], "source": "second", **{c: s[c] for c in STOCK_COLUMNS}}
                       for s in rec["stocks"]]
        videos.append(row)
    LABELS.mkdir(exist_ok=True)
    pd.DataFrame(videos).to_csv(LABELS / "videos.csv", index=False)
    pd.DataFrame(stocks).to_csv(LABELS / "labels.csv", index=False)
    print(f"labels/: {len(videos)} videos, {len(stocks)} stock labels", flush=True)


def load() -> None:
    """Rebuilds data/videos, data/mentions and data/mentions_check from labels/. Never overwrites a file."""
    videos = pd.read_csv(LABELS / "videos.csv", dtype={"id": str}, keep_default_na=False)
    stocks = pd.read_csv(LABELS / "labels.csv", dtype={"video_id": str, "yahoo_symbol": str}, keep_default_na=False)
    by_video = {key: group for key, group in stocks.groupby(["video_id", "source"])}
    written = 0

    def write(path: Path, record: dict) -> None:
        nonlocal written
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
            written += 1

    def labels_of(vid: str, source: str, run: dict) -> dict:
        rows = by_video.get((vid, source))
        found = [] if rows is None else [{**{c: r[c] for c in STOCK_COLUMNS}, "conviction": int(float(r["conviction"]))}
                                         for _, r in rows.iterrows()]
        return {"video_id": vid, "channel": run["channel"], **{c: run[c] for c in RUN_COLUMNS}, "stocks": found}

    for _, v in videos.iterrows():
        meta = {c: v[c] for c in VIDEO_COLUMNS}
        for c in ("published_ts", "duration", "view_count", "like_count"):
            meta[c] = int(float(meta[c])) if meta[c] != "" else None  # a column with gaps is written as 123.0
        # No transcript in the public labels; has_transcript keeps the coverage table right.
        has_transcript = str(v["has_transcript"]) == "True"  # pandas may already have made it a bool
        write(VIDEOS / v["channel"] / f"{v['id']}.json", {**meta, "has_transcript": has_transcript, "transcript": None})
        if v["model"]:
            write(MENTIONS / f"{v['id']}.json", labels_of(v["id"], "main", v))
        if v["second_set"]:
            run = {"channel": v["channel"], **{c: v[f"second_{c}"] for c in RUN_COLUMNS}}
            write(CHECK / v["second_set"] / f"{v['id']}.json", labels_of(v["id"], "second", run))
    print(f"data/ rebuilt from labels/: {written} files written (existing files kept)", flush=True)
