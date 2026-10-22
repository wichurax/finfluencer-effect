"""How far the labels can be trusted: a sample of videos labelled again by the other model.

Videos labelled by Claude get a second label from GPT and the other way round, written to
data/mentions_check/ so the main labels stay untouched. Compared per (video, stock).
"""

import json
import random
from collections import Counter
from pathlib import Path

import pandas as pd

from .classify import MENTIONS, label_videos
from .config import CHANNELS, DATA, RESULTS, market_of
from .prices import fix_symbol
from .videos import load_videos

CHECK = DATA / "mentions_check"
COUNTRY = {c.key: c.country for c in CHANNELS}
STANCES = ["bullish", "neutral", "bearish"]


def _family(record: dict) -> str:
    return "gpt" if record["backend"] == "codex" else "claude"


def _stocks(record: dict) -> dict[str, str]:
    out = {}
    for s in record["stocks"]:
        sym = fix_symbol(s["yahoo_symbol"])
        if s["asset_type"] == "stock" and sym and market_of(sym):
            out.setdefault(sym, s["stance"])
    return out


def relabel(sample: int, claude_model: str, claude_effort: str, workers: int, seed: int,
            directions: tuple[str, ...] = ("claude", "gpt")) -> None:
    """Labels a sample from each family again with the other family, into data/mentions_check/."""
    videos = {v["id"]: v for v in load_videos()}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in MENTIONS.glob("*.json")]
    rng = random.Random(seed)
    # Codex takes its model and effort from ~/.codex/config.toml when the model is "default".
    plan = {"claude": ("codex", "default", "low"), "gpt": ("cli", claude_model, claude_effort)}
    for family in directions:
        backend, model, effort = plan[family]
        out_dir = CHECK / ("gpt" if backend == "codex" else "claude")
        pool = sorted(r["video_id"] for r in records if _family(r) == family and r["video_id"] in videos)
        chosen = rng.sample(pool, min(sample, len(pool)))
        todo = [videos[i] for i in chosen if not (out_dir / f"{i}.json").exists()]
        label_videos(todo, backend, model, effort, workers, out_dir)


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n**2
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def compare_dir(check_dir: Path, reference: str | None = None) -> dict:
    """Agreement of the labels in check_dir with the main labels of the same videos.

    reference: only compare against main labels whose model contains this text (e.g. "opus").
    """
    pairs = []
    for path in check_dir.glob("*.json"):
        main_path = MENTIONS / path.name
        if not main_path.exists():
            continue
        main = json.loads(main_path.read_text(encoding="utf-8"))
        if reference and reference not in main["model"]:
            continue
        second = json.loads(path.read_text(encoding="utf-8"))
        a, b = _stocks(main), _stocks(second)
        own = "US" if COUNTRY[main["channel"]] == "US" else "GPW"
        for sym in (x for x in set(a) | set(b) if market_of(x) == own):
            pairs.append({"video_id": main["video_id"], "symbol": sym, "country": COUNTRY[main["channel"]],
                          "first": a.get(sym, "absent"), "second": b.get(sym, "absent"),
                          "first_model": main["model"], "second_model": second["model"]})
    if not pairs:
        return {}
    df = pd.DataFrame(pairs)
    df.to_csv(RESULTS / f"agreement_{check_dir.name}.csv", index=False)
    return {"all": stats(df), **{c: stats(df[df["country"] == c]) for c in ("US", "PL")}}


def stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    both = df[(df["first"] != "absent") & (df["second"] != "absent")]
    directional = df[df["first"].isin(["bullish", "bearish"]) | df["second"].isin(["bullish", "bearish"])]
    opposite = ((directional["first"] == "bullish") & (directional["second"] == "bearish")) | (
        (directional["first"] == "bearish") & (directional["second"] == "bullish"))
    return {
        "videos": int(df["video_id"].nunique()),
        "stocks_named_by_either": len(df),
        "named_by_both_share": round(len(both) / len(df), 3),
        "stance_agreement_when_both_named": round(float((both["first"] == both["second"]).mean()), 3),
        "cohen_kappa_when_both_named": round(cohen_kappa(both["first"].tolist(), both["second"].tolist()), 3),
        "directional_calls": len(directional),
        "directional_same": round(float((directional["first"] == directional["second"]).mean()), 3),
        "directional_opposite": round(float(opposite.mean()), 3),
    }


def compare() -> dict:
    """Claude against GPT on every cross-labelled video, per country; results/agreement.json."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name in ("gpt", "claude"):
        if (CHECK / name).exists():
            compare_dir(CHECK / name)
    frames = [pd.read_csv(RESULTS / f"agreement_{n}.csv") for n in ("gpt", "claude")
              if (RESULTS / f"agreement_{n}.csv").exists()]
    if not frames:
        return {}
    df = pd.concat(frames)
    result = {c: stats(df[df["country"] == c]) for c in ("US", "PL")}
    (RESULTS / "agreement.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def effort_test(sample: int, model: str, efforts: list[str], workers: int, seed: int) -> dict:
    """Relabels a sample of Opus-labelled videos with a cheaper model at each effort, against Opus."""
    videos = {v["id"]: v for v in load_videos()}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in MENTIONS.glob("*.json")]
    pool = sorted(r["video_id"] for r in records if "opus" in r["model"] and r["video_id"] in videos)
    chosen = random.Random(seed).sample(pool, min(sample, len(pool)))
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = {}
    for effort in efforts:
        out_dir = CHECK / f"{model}-{effort}"
        todo = [videos[i] for i in chosen if not (out_dir / f"{i}.json").exists()]
        label_videos(todo, "cli", model, effort, workers, out_dir)
        out[effort] = compare_dir(out_dir, reference="opus")
    (RESULTS / f"effort_test_{model}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out
