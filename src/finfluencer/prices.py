"""Daily adjusted closes and volumes from Yahoo for every labelled stock and the benchmarks."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from functools import cache

import pandas as pd
import yfinance as yf

from .config import DATA, MARKETS, ROOT, STUDY_END, STUDY_START, market_of

PRICES = DATA / "prices"
MENTIONS = DATA / "mentions"
# Hand-checked corrections for symbols the labeller got wrong: {"WRONG": "RIGHT"}, or "" to drop.
SYMBOL_FIXES = ROOT / "symbol_fixes.json"
# Enough history before the window for a 250-day beta, and room after it for +5 days.
HISTORY_BEFORE = timedelta(days=420)


@cache
def _fixes() -> dict[str, str]:
    if not SYMBOL_FIXES.exists():
        return {}
    return {k.upper(): v.upper() for k, v in json.loads(SYMBOL_FIXES.read_text(encoding="utf-8")).items()}


def fix_symbol(raw: str) -> str:
    symbol = raw.strip().upper()
    return _fixes().get(symbol, symbol)


def labelled_names() -> dict[str, set[str]]:
    """Every stock symbol in scope, with the company names the labeller gave it."""
    names: dict[str, set[str]] = {}
    for path in MENTIONS.glob("*.json"):
        for stock in json.loads(path.read_text(encoding="utf-8"))["stocks"]:
            symbol = fix_symbol(stock["yahoo_symbol"])
            if stock["asset_type"] == "stock" and symbol and market_of(symbol):
                names.setdefault(symbol, set()).add(stock["company"])
    return names


def download_all() -> None:
    PRICES.mkdir(parents=True, exist_ok=True)
    names = labelled_names()
    symbols = sorted(set(names) | {m.benchmark for m in MARKETS.values()})
    start = STUDY_START - HISTORY_BEFORE
    end = min(date.today(), STUDY_END + timedelta(days=20))
    print(f"downloading {len(symbols)} symbols, {start} to {end}", flush=True)

    frames = []
    for i in range(0, len(symbols), 100):
        chunk = symbols[i:i + 100]
        frames.append(yf.download(chunk, start=start, end=end, auto_adjust=True,
                                  group_by="column", threads=True, progress=False))
    data = pd.concat(frames, axis=1)
    close = data["Close"].dropna(axis=1, how="all")
    volume = data["Volume"][close.columns]
    close.to_parquet(PRICES / "close.parquet")
    volume.to_parquet(PRICES / "volume.parquet")

    missing = sorted(set(symbols) - set(close.columns))
    (PRICES / "missing.json").write_text(json.dumps(missing, indent=1), encoding="utf-8")
    print(f"saved {close.shape[1]} symbols, {len(missing)} without data: {missing[:40]}", flush=True)
    verify_names({s: names[s] for s in close.columns if s in names})


STOPWORDS = {"inc", "corp", "corporation", "co", "company", "sa", "s", "a", "plc", "ltd", "limited", "nv",
             "holdings", "holding", "group", "the", "class", "ag", "se", "spolka", "akcyjna", "and", "of",
             "technologies", "technology", "international", "platforms", "systems", "com"}


def _tokens(name: str) -> set[str]:
    plain = name.lower().translate(str.maketrans("ąćęłńóśźż", "acelnoszz"))
    return {t for t in re.split(r"[^a-z0-9]+", plain) if len(t) >= 2 and t not in STOPWORDS}


def _yahoo_name(symbol: str) -> str:
    try:
        info = yf.Ticker(symbol).info
        return info.get("longName") or info.get("shortName") or ""
    except Exception:  # noqa: BLE001 - Yahoo's quote endpoint fails in many ways; an empty name is flagged
        return ""


def verify_names(names: dict[str, set[str]]) -> None:
    """Flags symbols whose Yahoo company name shares no word with the labeller's name for review."""
    cache_path = PRICES / "yahoo_names.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    missing = sorted(s for s in names if not cache.get(s))
    with ThreadPoolExecutor(max_workers=2) as pool:
        cache.update(zip(missing, pool.map(_yahoo_name, missing)))
    cache_path.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")

    rows = []
    for s in sorted(names):
        yahoo = cache.get(s, "")
        ours = set().union(*(_tokens(n) for n in names[s]))
        # Short tickers often double as the brand (e.g. "XTB"), so the symbol's root counts too.
        theirs = _tokens(yahoo) | {s.split(".")[0].lower()}
        status = "unknown" if not yahoo else ("ok" if ours & theirs else "review")
        rows.append({"symbol": s, "yahoo_name": yahoo, "labeller_names": " | ".join(sorted(names[s])),
                     "status": status})
    table = pd.DataFrame(rows)
    table.to_csv(PRICES / "symbol_check.csv", index=False)
    counts = table["status"].value_counts().to_dict()
    print(f"name check: {counts.get('review', 0)} to review, {counts.get('unknown', 0)} without a Yahoo name "
          f"(rerun to retry), in {PRICES / 'symbol_check.csv'}", flush=True)


EARNINGS = PRICES / "earnings.json"


def download_earnings() -> None:
    """Earnings announcement times per stock, cached; Yahoo throttles, so this goes slowly."""
    import time

    cache = json.loads(EARNINGS.read_text(encoding="utf-8")) if EARNINGS.exists() else {}
    close = pd.read_parquet(PRICES / "close.parquet")
    benchmarks = {m.benchmark for m in MARKETS.values()}
    todo = [s for s in close.columns if s not in cache and s not in benchmarks]
    print(f"earnings dates: {len(todo)} symbols to fetch", flush=True)
    for i, symbol in enumerate(todo):
        try:
            frame = yf.Ticker(symbol).get_earnings_dates(limit=16)
            cache[symbol] = [] if frame is None else [ts.isoformat() for ts in frame.index]
        except Exception as e:  # noqa: BLE001 - leave it out of the cache so a rerun retries it
            print(f"  {symbol}: {str(e)[:80]}", flush=True)
            time.sleep(10)
            continue
        if i % 25 == 0:
            EARNINGS.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            print(f"  {i}/{len(todo)}", flush=True)
        time.sleep(1.5)
    EARNINGS.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    with_dates = sum(1 for v in cache.values() if v)
    print(f"earnings dates cached for {len(cache)} symbols, {with_dates} with at least one date", flush=True)
