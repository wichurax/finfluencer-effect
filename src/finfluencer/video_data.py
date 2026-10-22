"""The numbers the Remotion clip shows, taken from results/: video/src/data.json."""

import json

import numpy as np
import pandas as pd

from .analyze import ALL, HIGH_LIQ, LOW_LIQ, NEAR_EARNINGS, NO_EARNINGS, QUIET_NO_NEWS
from .config import CHANNELS, RESULTS, ROOT

DAY0 = 5  # index of the first session after the video in the saved -5..+5 paths


def _effect(tests: pd.DataFrame, seg: str, group: str, measure: str = "car_d0") -> dict:
    r = tests.loc[(seg, group, measure)]
    return {
        "effect": round(float(r["excess"]) * 100, 2),
        "band": [round(float(r["placebo_lo"] - r["placebo_mean"]) * 100, 2),
                 round(float(r["placebo_hi"] - r["placebo_mean"]) * 100, 2)],
        "p": float(r["p_placebo"]),
        "n": int(r["n_events"]),
    }


def _cloud(paths: dict, tests: pd.DataFrame, seg: str, group: str) -> dict:
    """Random-day averages (first session after, in the call's direction), centred on their mean, and the real one."""
    null = paths[f"{seg}|{group}|car"][:, DAY0] * 100
    centre = float(null.mean())
    real = float(tests.loc[(seg, group, "car_d0")]["mean"]) * 100
    return {"random": np.round(null - centre, 3).tolist(), "real": round(real - centre, 3)}


def _path(close: pd.DataFrame, symbol: str, bench: str, day0: str) -> dict:
    px = close[[symbol, bench]].dropna()
    i = px.index.get_indexer([pd.Timestamp(day0)])[0]
    window = px.iloc[i - 3:i + 4]
    path = ((window / window.iloc[2] - 1) * 100).round(2)
    return {"stock": path[symbol].tolist(), "market": path[bench].tolist()}


def _excerpt(video_id: str, channel: str) -> dict:
    """About 60 words of the real transcript around the call, split at the call so the clip can highlight it."""
    video = json.loads((RESULTS.parent / "data" / "videos" / channel / f"{video_id}.json").read_text(encoding="utf-8"))
    text = video["transcript"]
    if not text:
        raise SystemExit("video-data needs the transcripts from the full pipeline; the public labels have none")
    call = "you buy it, you buy it, you hold it"
    i = text.lower().find(call)
    before = " ".join(text[:i].split()[-44:])
    after = " ".join(text[i + len(call):].split()[:10])
    return {"before": before, "call": text[i:i + len(call)], "after": after}


def export() -> None:
    tests = pd.read_csv(RESULTS / "tests.csv").set_index(["segment", "group", "measure"])
    cov = json.loads((RESULTS / "coverage.json").read_text(encoding="utf-8"))
    examples = json.loads((RESULTS / "examples.json").read_text(encoding="utf-8"))
    events = pd.read_csv(RESULTS / "events.csv", low_memory=False)
    called = events[(events["sign"] != 0) & ~events["repeat"]]
    npz = np.load(RESULTS / "placebo_paths.npz")
    paths = {k: npz[k] for k in npz.files}
    close = pd.read_parquet(RESULTS.parent / "data" / "prices" / "close.parquet")
    names = {c.key: c.name.split(" (")[0] for c in CHANNELS}

    us, pl = examples["US"], examples["PL-GPW"]
    data = {
        "videos": sum(c["videos"] for c in cov["per_channel"].values()),
        "opinions": {"US": int((called["segment"] == "US").sum()), "PL": int((called["segment"] == "PL-GPW").sum())},
        "channels": [{"key": c.key, "name": names[c.key], "country": c.country, "subscribers": c.subscribers}
                     for c in CHANNELS],
        "examples": {
            "US": {"video": us["video_id"], "channel": names[us["channel"]], "company": us["company"],
                   "quote": "you buy it, you hold it", "transcript": _excerpt(us["video_id"], us["channel"]),
                   **_path(close, us["symbol"], "SPY", us["day0"])},
            "PL": {"video": pl["video_id"], "channel": names[pl["channel"]], "company": pl["company"],
                   "quote": "kontynuuje swój ruch spadkowy",
                   **_path(close, pl["symbol"], "ETFBW20TR.WA", pl["day0"])},
        },
        "raw": {"US": _effect(tests, "US", ALL), "PL": _effect(tests, "PL-GPW", ALL)},
        "before": {"US": _effect(tests, "US", ALL, "car_pre"), "PL": _effect(tests, "PL-GPW", ALL, "car_pre")},
        "earnings": {"near": _effect(tests, "US", NEAR_EARNINGS), "away": _effect(tests, "US", NO_EARNINGS)},
        "clean": {"US": _effect(tests, "US", QUIET_NO_NEWS), "PL": _effect(tests, "PL-GPW", QUIET_NO_NEWS)},
        "liquidity": {"small": _effect(tests, "PL-GPW", LOW_LIQ), "large": _effect(tests, "PL-GPW", HIGH_LIQ)},
        "clouds": {"US": _cloud(paths, tests, "US", ALL), "USclean": _cloud(paths, tests, "US", QUIET_NO_NEWS),
                   "PLclean": _cloud(paths, tests, "PL-GPW", QUIET_NO_NEWS)},
        "draws": 2000,
        "period": "Oct 2024–Oct 2026",
    }
    out = ROOT / "video" / "src" / "data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"video data written to {out}", flush=True)
