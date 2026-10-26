"""Event study: abnormal returns after bullish and bearish calls, tested against random days.

Day 0 is the first session that closes after the video is published, so a video posted before
the close counts from that same session. The reference price is the close before day 0.
Abnormal return = stock return minus the benchmark return (market-adjusted); a beta-adjusted
version is kept as a robustness check.

The baseline moves every video to a random trading day (all its stocks together, same signs),
many times over. That keeps each stock's volatility and drift, the bull/bear mix, and the
correlation between stocks named in one video, so the comparison is like for like.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

from .config import CHANNELS, MARKETS, RESULTS, STUDY_END, STUDY_START, market_of
from .prices import MENTIONS, PRICES, fix_symbol
from .videos import load_videos

WINDOWS = {"d0": (0, 0), "d0-1": (0, 1), "d0-2": (0, 2), "d0-3": (0, 3), "d1-3": (1, 3)}
PRE = (-5, -1)
PATH = range(-5, 6)
REPEAT_GAP = 3  # same channel, same stock again within 3 sessions: an overlapping event
EARNINGS_GAP = 3  # results released within 3 sessions of day 0, either side: a news-driven event
MAX_DAILY_AR = 0.5  # guards against bad prints and missed split adjustments


@dataclass
class Series:
    dates: np.ndarray  # datetime64[D], sessions where both the stock and its benchmark traded
    ar: np.ndarray  # market-adjusted abnormal return per session
    cs: np.ndarray  # cumulative sum of ar with a leading 0, for O(1) window sums
    csb: np.ndarray  # same for the beta-adjusted abnormal return
    abvol: np.ndarray  # log(volume / median volume of sessions -60..-11)
    turnover: np.ndarray  # median close x volume of sessions -60..-11, a liquidity measure

    def window(self, i, a: int, b: int, beta: bool = False):
        cs = self.csb if beta else self.cs
        return cs[i + b + 1] - cs[i + a]


def build_series(close: pd.DataFrame, volume: pd.DataFrame) -> dict[str, Series]:
    series = {}
    for sym in close.columns:
        market = market_of(sym)
        if market is None or sym in {m.benchmark for m in MARKETS.values()}:
            continue
        bench = close[MARKETS[market].benchmark].dropna()
        px = close[sym].dropna()
        common = px.index.intersection(bench.index)
        if len(common) < 80:
            continue
        r = px.loc[common].pct_change()
        rm = bench.loc[common].pct_change()
        ar = (r - rm).clip(-MAX_DAILY_AR, MAX_DAILY_AR)
        # Beta from sessions -250..-21, so the estimate never sees the event itself.
        rs, rms = r.shift(21), rm.shift(21)
        beta = rs.rolling(230, min_periods=120).cov(rms) / rms.rolling(230, min_periods=120).var()
        arb = (r - beta * rm).clip(-MAX_DAILY_AR, MAX_DAILY_AR)
        vol = volume[sym].loc[common].astype(float).replace(0, np.nan)
        abvol = np.log(vol / vol.shift(11).rolling(50, min_periods=30).median())
        turnover = (px.loc[common] * vol).shift(11).rolling(50, min_periods=30).median()
        series[sym] = Series(
            dates=common.values.astype("datetime64[D]"),
            ar=ar.to_numpy(),
            cs=np.concatenate([[0.0], np.cumsum(np.nan_to_num(ar.to_numpy()))]),
            csb=np.concatenate([[0.0], np.cumsum(np.nan_to_num(arb.to_numpy()))]),
            abvol=abvol.to_numpy(),
            turnover=turnover.to_numpy(),
        )
    return series


def find_day0(dates: np.ndarray, published: datetime, market: str) -> tuple[int, str]:
    m = MARKETS[market]
    local = published.astimezone(ZoneInfo(m.tz))
    open_t, close_t = time.fromisoformat(m.open), time.fromisoformat(m.close)
    first = local.date() if local.time() < close_t else local.date() + timedelta(days=1)
    i = int(np.searchsorted(dates, np.datetime64(first)))
    if i >= len(dates):
        return -1, ""
    if dates[i].astype(date) != local.date():
        return i, "off_hours"
    return i, "in_session" if local.time() >= open_t else "before_open"


def labeller(record: dict) -> str:
    if record.get("backend") == "codex":
        return "gpt"
    return "haiku" if "haiku" in record["model"] else "opus"


def earnings_sessions(series: dict[str, Series]) -> dict[str, np.ndarray]:
    """Index of the session that first trades on each earnings release, per stock with known dates."""
    path = PRICES / "earnings.json"
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    out = {}
    for sym, stamps in raw.items():
        if sym not in series or not stamps:
            continue
        ser, market = series[sym], market_of(sym)
        idx = [find_day0(ser.dates, datetime.fromisoformat(t), market)[0] for t in stamps]
        out[sym] = np.array([i for i in idx if i >= 0])
    return out


def build_events(series: dict[str, Series], mentions_dir: Path = MENTIONS,
                 only_ids: set[str] | None = None) -> tuple[pd.DataFrame, dict]:
    videos = {v["id"]: v for v in load_videos()}
    earnings = earnings_sessions(series)
    channels = {c.key: c for c in CHANNELS}
    rows, dropped = [], {"not a stock": 0, "exchange out of scope": 0, "no price data": 0,
                         "outside price history": 0}
    for path in mentions_dir.glob("*.json"):
        if only_ids is not None and path.stem not in only_ids:
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        video = videos.get(rec["video_id"])
        if not video or rec["channel"] not in channels or not video.get("published_ts"):
            continue
        published = datetime.fromtimestamp(video["published_ts"], timezone.utc)
        seen = set()
        for s in rec["stocks"]:
            sym = fix_symbol(s["yahoo_symbol"])
            market = market_of(sym) if sym else None
            if s["asset_type"] != "stock":
                dropped["not a stock"] += 1
                continue
            if market is None:
                dropped["exchange out of scope"] += 1
                continue
            if sym not in series:
                dropped["no price data"] += 1
                continue
            if sym in seen:
                continue
            seen.add(sym)
            ser = series[sym]
            i, timing = find_day0(ser.dates, published, market)
            if i < 11 or i + 5 >= len(ser.dates):
                dropped["outside price history"] += 1
                continue
            row = {
                "video_id": video["id"],
                "channel": rec["channel"],
                "country": channels[rec["channel"]].country,
                "market": market,
                "symbol": sym,
                "company": s["company"],
                "stance": s["stance"],
                "sign": {"bullish": 1, "bearish": -1, "neutral": 0}[s["stance"]],
                "conviction": s["conviction"],
                "focus": s["focus"],
                "evidence": s.get("evidence", ""),  # absent in the public labels
                "labeller": labeller(rec),
                "title": video["title"],
                "views": video.get("view_count") or 0,
                "published_utc": published.isoformat(),
                "day0": str(ser.dates[i]),
                "idx": i,
                "timing": timing,
                "car_pre": ser.window(i, *PRE),
                "abvol_pre": np.nanmean(ser.abvol[i - 3:i]),
                "abvol_d0": ser.abvol[i],
                "abvol_d1": ser.abvol[i + 1],
                "absar_d0": abs(ser.ar[i]),
                "turnover": ser.turnover[i],
                # None when Yahoo has no dates for the stock; True when results land within 3 sessions.
                "near_earnings": (bool(np.any(np.abs(earnings[sym] - i) <= EARNINGS_GAP))
                                  if sym in earnings else None),
            }
            for name, (a, b) in WINDOWS.items():
                row[f"car_{name}"] = ser.window(i, a, b)
            row["carb_d0-3"] = ser.window(i, *WINDOWS["d0-3"], beta=True)
            for k in PATH:
                row[f"ar_{k}"] = ser.ar[i + k]
                row[f"vol_{k}"] = ser.abvol[i + k]
            rows.append(row)

    events = pd.DataFrame(rows).sort_values(["channel", "symbol", "idx"]).reset_index(drop=True)
    same = (events["channel"] == events["channel"].shift()) & (events["symbol"] == events["symbol"].shift())
    events["repeat"] = same & (events["idx"] - events["idx"].shift() <= REPEAT_GAP)
    local = ((events["country"] == "US") & (events["market"] == "US")) | (
        (events["country"] == "PL") & (events["market"] == "GPW"))
    dropped["stock outside the channel's own market"] = int((~local).sum())
    events = events[local].reset_index(drop=True)
    events["segment"] = np.where(events["country"] == "US", "US", "PL-GPW")
    # Views terciles within each channel, since channel sizes differ 50x. Views are counted at download
    # time, so older videos have had longer to collect them.
    video_views = events.drop_duplicates("video_id").set_index("video_id")
    # A channel with fewer than three videos (a partial run) has no terciles, rather than an error.
    tercile = video_views.groupby("channel")["views"].transform(
        lambda v: pd.qcut(v.rank(method="first"), 3, labels=["low", "mid", "high"]) if len(v) >= 3 else None)
    events["views_tercile"] = events["video_id"].map(tercile).astype(str)
    # Liquidity terciles within each market, since PLN and USD turnover are not comparable.
    events["liquidity"] = events.groupby("market")["turnover"].transform(
        lambda t: pd.qcut(t, 3, labels=["low", "mid", "high"]) if t.notna().sum() >= 30 else None)
    return events, dropped


VALUE_KEYS = [*(f"car_{w}" for w in WINDOWS), "carb_d0-3", "car_pre", "abvol_d0", "abvol_d1", "absar_d0"]


def placebo(events: pd.DataFrame, series: dict[str, Series], draws: int,
            rng: np.random.Generator) -> dict[str, np.ndarray]:
    """draws x events matrices of each measure, with every video moved to a random day."""
    days = np.arange(np.datetime64(STUDY_START), np.datetime64(STUDY_END), dtype="datetime64[D]")
    video_codes, video_of_event = np.unique(events["video_id"].to_numpy(), return_inverse=True)
    picks = days[rng.integers(0, len(days), size=(draws, len(video_codes)))][:, video_of_event]
    out = {k: np.full((draws, len(events)), np.nan, dtype=np.float32) for k in VALUE_KEYS}
    for sym, pos in events.groupby("symbol").indices.items():
        s = series[sym]
        cal = picks[:, pos]
        idx = np.searchsorted(s.dates, cal)
        valid = (cal >= s.dates[0]) & (idx >= 11) & (idx + 5 < len(s.dates))
        i = np.clip(idx, 11, len(s.dates) - 6)
        values = {f"car_{w}": s.window(i, a, b) for w, (a, b) in WINDOWS.items()}
        values["carb_d0-3"] = s.window(i, *WINDOWS["d0-3"], beta=True)
        values["car_pre"] = s.window(i, *PRE)
        values["abvol_d0"] = s.abvol[i]
        values["abvol_d1"] = s.abvol[i + 1]
        values["absar_d0"] = np.abs(s.ar[i])
        for k, v in values.items():
            out[k][:, pos] = np.where(valid, v, np.nan)
    return out


SEGMENTS = {
    "US": "USA: amerykańscy youtuberzy, spółki z USA",
    "PL-GPW": "Polska: polscy youtuberzy, spółki z GPW",
}
ALL = "Wszystkie opinie"
OFF_SESSION = "Film poza sesją"
IN_SESSION = "Film w trakcie sesji"
NO_EARNINGS = "Bez wyników kwartalnych (±3 sesje)"
NEAR_EARNINGS = "Przy wynikach kwartalnych (±3 sesje)"
NO_EARNINGS_DATES = "Brak dat wyników kwartalnych"
CLEANEST = "Film poza sesją, bez wyników kwartalnych"
QUIET = "Film poza sesją, spokojny tydzień przed"
QUIET_NO_NEWS = "Test bez newsów"
LOW_VIEWS = "Test bez newsów: najmniej oglądane filmy kanału (dolna 1/3)"
HIGH_VIEWS = "Test bez newsów: najczęściej oglądane filmy kanału (górna 1/3)"
LOW_LIQ = "Najmniej płynne spółki (dolna 1/3)"
HIGH_LIQ = "Najbardziej płynne spółki (górna 1/3)"
NEWS_WORDS = (r"wynik|raport|kwarta|espi|kontrakt|umow|dywidend|przejęc|przejmuj|emisj|prognoz|"
              r"earnings|results|quarter|guidance|report|deal|acqui|merger|split|ipo|buyback|skup")
QUIET_MOVE = 0.03
QUIET_VOLUME = 0.2


def groups(ev: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    """(segment, group name, mask) for every test; Poland and the USA are never pooled."""
    out = []
    for seg in SEGMENTS:
        base = (ev["segment"] == seg) & ~ev["repeat"]
        # No sign of news in the week before: a small move and normal volume. Works where Yahoo
        # has no earnings dates, and catches other company announcements too.
        quiet = (ev["car_pre"].abs() < QUIET_MOVE) & (ev["abvol_pre"] < QUIET_VOLUME)
        # Company news released after the close (earnings, ESPI reports) reaches prices the next
        # session; a title that names such news marks a video reacting to it.
        news_title = ev["title"].fillna("").str.lower().str.contains(NEWS_WORDS, regex=True)
        called = base & (ev["sign"] != 0)
        rows = [(ALL, called)]
        for c in CHANNELS:
            m = called & (ev["channel"] == c.key)
            if m.sum() >= 30:
                rows.append((f"Kanał: {c.name}", m))
        off = ev["timing"] != "in_session"
        no_news = off & quiet & ~news_title
        rows += [
            ("Tylko opinie pozytywne", called & (ev["sign"] == 1)),
            ("Tylko opinie negatywne", called & (ev["sign"] == -1)),
            ("Główny temat filmu, mocna opinia", called & (ev["focus"] == "main") & (ev["conviction"] >= 2)),
            (OFF_SESSION, called & off),
            (IN_SESSION, called & ~off),
            (NO_EARNINGS, called & (ev["near_earnings"] == False)),  # noqa: E712
            (NEAR_EARNINGS, called & (ev["near_earnings"] == True)),  # noqa: E712
            (NO_EARNINGS_DATES, called & ev["near_earnings"].isna()),
            (CLEANEST, called & off & (ev["near_earnings"] == False)),  # noqa: E712
            (QUIET, called & off & quiet),
            (QUIET_NO_NEWS, called & no_news),
            (LOW_VIEWS, called & no_news & (ev["views_tercile"] == "low")),
            (HIGH_VIEWS, called & no_news & (ev["views_tercile"] == "high")),
            (LOW_LIQ, called & (ev["liquidity"] == "low")),
            (HIGH_LIQ, called & (ev["liquidity"] == "high")),
            ("Oceny: Claude Opus 5.5", called & (ev["labeller"] == "opus")),
            ("Oceny: Claude Haiku 5.5", called & (ev["labeller"] == "haiku")),
            ("Oceny: GPT-6.1", called & (ev["labeller"] == "gpt")),
            ("Wzmianki bez opinii", base & (ev["sign"] == 0)),
        ]
        out += [(seg, name, mask) for name, mask in rows]
    return out


def test_group(ev: pd.DataFrame, mask: pd.Series, key: str, null: dict[str, np.ndarray]) -> dict:
    # Returns are scored in the direction of the opinion; neutral mentions and volume are not directional.
    sign = np.where(ev["sign"] == 0, 1, ev["sign"]).astype(float)
    if key.startswith(("abvol", "absar")):
        sign = np.ones(len(ev))
    m = mask.to_numpy() & ev[key].notna().to_numpy()
    y = ev.loc[m, key].to_numpy() * sign[m]
    n = len(y)
    res = {"n_events": n, "n_videos": ev.loc[m, "video_id"].nunique()}
    clusters = pd.factorize(ev.loc[m, "day0"])[0]
    if n < 5 or clusters.max() < 4:
        return res
    fit = sm.OLS(y, np.ones(n)).fit(cov_type="cluster", cov_kwds={"groups": clusters})
    se = float(fit.bse[0])
    null_means = np.nanmean(null[key][:, m] * sign[m], axis=1)
    null_hits = np.nanmean((null[key][:, m] * sign[m]) > 0, axis=1)
    # A draw with no value for this group (stocks with a short history) is no draw: kept, it makes
    # the centre NaN, every comparison false, and p the smallest there is.
    drawn = ~np.isnan(null_means)
    null_means, null_hits = null_means[drawn], null_hits[drawn]
    centre = null_means.mean()
    obs = float(y.mean())
    res.update({
        "mean": obs,
        "median": float(np.median(y)),
        "se_clustered": se,
        "t": obs / se if se > 0 else np.nan,
        "hit_rate": float((y > 0).mean()),
        "placebo_mean": float(centre),
        "placebo_hit_rate": float(null_hits.mean()),
        "excess": obs - float(centre),
        "p_placebo": float((1 + np.sum(np.abs(null_means - centre) >= abs(obs - centre))) / (1 + len(null_means))),
        "placebo_lo": float(np.quantile(null_means, 0.025)),
        "placebo_hi": float(np.quantile(null_means, 0.975)),
        # Smallest true effect this sample would catch 80% of the time at 5% (two-sided).
        "mde_80": 2.8 * float(np.std(null_means)),
    })
    return res


MOMENTUM_KEYS = ["car_d0", "car_d0-3"]


def test_momentum(ev: pd.DataFrame, mask: pd.Series, key: str, null: dict[str, np.ndarray]) -> dict:
    """Like test_group, but against random days with a similar move in the 5 sessions before.

    On random days the window's return is regressed on the pre-video return (both in the direction
    of the opinion); the test compares what is left over. A video that only rides a move already
    under way, as after news, scores zero here.
    """
    sign = np.where(ev["sign"] == 0, 1, ev["sign"]).astype(float)
    m = mask.to_numpy() & ev[key].notna().to_numpy() & ev["car_pre"].notna().to_numpy()
    n = int(m.sum())
    res = {"n_events": n, "n_videos": ev.loc[m, "video_id"].nunique()}
    if n < 30:
        return res
    y_null, x_null = null[key][:, m] * sign[m], null["car_pre"][:, m] * sign[m]
    ok = ~np.isnan(y_null) & ~np.isnan(x_null)
    xv, yv = x_null[ok].astype(float), y_null[ok].astype(float)
    slope = float(np.cov(xv, yv)[0, 1] / np.var(xv, ddof=1))
    null_means = np.nanmean(np.where(ok, y_null - slope * x_null, np.nan), axis=1)
    null_means = null_means[~np.isnan(null_means)]  # as in test_group: an empty draw is no draw
    y_obs = ev.loc[m, key].to_numpy() * sign[m]
    x_obs = ev.loc[m, "car_pre"].to_numpy() * sign[m]
    obs = float(np.mean(y_obs - slope * x_obs))
    centre = float(null_means.mean())
    res.update({
        "mean": obs,
        "placebo_mean": centre,
        "excess": obs - centre,
        "p_placebo": float((1 + np.sum(np.abs(null_means - centre) >= abs(obs - centre))) / (1 + len(null_means))),
        "placebo_lo": float(np.quantile(null_means, 0.025)),
        "placebo_hi": float(np.quantile(null_means, 0.975)),
        "mde_80": 2.8 * float(np.std(null_means)),
        "momentum_slope": slope,
    })
    return res


def regression(ev: pd.DataFrame, segment: str) -> pd.DataFrame:
    d = ev[(ev["segment"] == segment) & (ev["sign"] != 0) & ~ev["repeat"]].copy()
    d["y"] = d["car_d0-3"] * d["sign"]
    X = pd.DataFrame({
        "stała": 1.0,
        "ruch przed filmem (dni -5..-1, w kierunku opinii)": d["car_pre"] * d["sign"],
        "log(wyświetlenia)": np.log1p(d["views"]),
        "przekonanie (1-3)": d["conviction"],
        "główny temat filmu": (d["focus"] == "main").astype(float),
        "spółka mało płynna (dolna 1/3)": (d["liquidity"] == "low").astype(float),
        "wyniki kwartalne ±3 sesje": (d["near_earnings"] == True).astype(float),  # noqa: E712
    })
    fit = sm.OLS(d["y"], X, missing="drop").fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d["day0"])[0]})
    return pd.DataFrame({"segment": segment, "coef": fit.params, "se": fit.bse, "p": fit.pvalues,
                         "n": int(fit.nobs)})


def placebo_paths(events: pd.DataFrame, series: dict[str, Series], masks: dict[str, np.ndarray],
                  draws: int, rng: np.random.Generator) -> dict[str, dict[str, np.ndarray]]:
    """Random-day versions of the day-by-day paths, for the charts' baseline bands.

    For each named mask: "car" is the mean cumulative abnormal return in the direction of the
    opinion (0 at the close before day 0) and "vol" the mean abnormal log volume, draws x len(PATH).
    """
    days = np.arange(np.datetime64(STUDY_START), np.datetime64(STUDY_END), dtype="datetime64[D]")
    video_codes, video_of_event = np.unique(events["video_id"].to_numpy(), return_inverse=True)
    picks = days[rng.integers(0, len(days), size=(draws, len(video_codes)))][:, video_of_event]
    ks = np.array(list(PATH))
    sums = {n: {"car": np.zeros((draws, len(ks))), "vol": np.zeros((draws, len(ks)))} for n in masks}
    counts = {n: {"car": np.zeros((draws, len(ks))), "vol": np.zeros((draws, len(ks)))} for n in masks}
    sign_all = np.where(events["sign"] == 0, 1, events["sign"]).astype(float)
    for sym, pos in events.groupby("symbol").indices.items():
        s = series[sym]
        cal = picks[:, pos]
        idx = np.searchsorted(s.dates, cal)
        valid = (cal >= s.dates[0]) & (idx >= 11) & (idx + 5 < len(s.dates))
        i = np.clip(idx, 11, len(s.dates) - 6)
        ar = np.stack([np.nan_to_num(s.ar[i + k]) for k in ks], axis=-1)  # draws x n x K
        vol = np.stack([s.abvol[i + k] for k in ks], axis=-1)
        post = np.cumsum(np.where(ks >= 0, ar, 0), axis=-1)
        pre = -np.cumsum(np.where(ks < 0, ar, 0)[..., ::-1], axis=-1)[..., ::-1]
        pre = np.concatenate([pre[..., 1:], np.zeros(pre.shape[:-1] + (1,))], axis=-1)
        car = np.where(ks >= 0, post, pre) * sign_all[pos][None, :, None]
        car = np.where(valid[..., None], car, np.nan)
        vol = np.where(valid[..., None], vol, np.nan)
        for name, mask in masks.items():
            sel = mask[pos]
            if not sel.any():
                continue
            for key, values in (("car", car[:, sel]), ("vol", vol[:, sel])):
                sums[name][key] += np.nansum(values, axis=1)
                counts[name][key] += np.sum(~np.isnan(values), axis=1)
    return {n: {k: sums[n][k] / np.maximum(counts[n][k], 1) for k in ("car", "vol")} for n in masks}


def run(draws: int, seed: int) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    close = pd.read_parquet(PRICES / "close.parquet")
    volume = pd.read_parquet(PRICES / "volume.parquet")
    series = build_series(close, volume)
    events, dropped = build_events(series)
    print(f"{len(events)} events, {int(events['repeat'].sum())} repeats; dropped: {dropped}", flush=True)
    print(events[(events["sign"] != 0) & ~events["repeat"]]["segment"].value_counts().to_dict(), flush=True)
    null = placebo(events, series, draws, np.random.default_rng(seed))

    rows = []
    for segment, name, mask in groups(events):
        for key in VALUE_KEYS:
            rows.append({"segment": segment, "group": name, "measure": key,
                         **test_group(events, mask, key, null)})
        for key in MOMENTUM_KEYS:
            rows.append({"segment": segment, "group": name, "measure": f"{key}_mom",
                         **test_momentum(events, mask, key, null)})
    tests = pd.DataFrame(rows)
    post = tests["measure"].str.startswith("car_d") & tests["p_placebo"].notna()
    tests.loc[post, "q_bh"] = multipletests(tests.loc[post, "p_placebo"], method="fdr_bh")[1]

    path_masks = {f"{seg}|{name}": mask.to_numpy() for seg, name, mask in groups(events)
                  if name in (ALL, CLEANEST, QUIET, QUIET_NO_NEWS)}
    paths = placebo_paths(events, series, path_masks, min(draws, 1000), np.random.default_rng(seed + 1))
    np.savez_compressed(RESULTS / "placebo_paths.npz",
                        **{f"{n}|{k}": v for n, d in paths.items() for k, v in d.items()})

    events.to_csv(RESULTS / "events.csv", index=False)
    tests.to_csv(RESULTS / "tests.csv", index=False)
    reg = pd.concat([regression(events, seg) for seg in SEGMENTS])
    reg.to_csv(RESULTS / "regression.csv")
    (RESULTS / "coverage.json").write_text(json.dumps(coverage(events, dropped), indent=1, default=int),
                                           encoding="utf-8")

    from .report import write_report
    write_report()


def coverage(events: pd.DataFrame, dropped: dict) -> dict:
    videos = load_videos()
    labelled = {p.stem for p in MENTIONS.glob("*.json")}
    per_channel = {}
    for c in CHANNELS:
        vs = [v for v in videos if v["channel"] == c.key]
        ev = events[events["channel"] == c.key]
        per_channel[c.key] = {
            "videos": len(vs),
            "with_transcript": sum(1 for v in vs if v.get("transcript") or v.get("has_transcript")),
            "classified": sum(1 for v in vs if v["id"] in labelled),
            "events": len(ev),
            "bullish": int((ev["sign"] == 1).sum()),
            "bearish": int((ev["sign"] == -1).sum()),
            "neutral": int((ev["sign"] == 0).sum()),
        }
    return {"per_channel": per_channel, "dropped_mentions": dropped,
            "study_window": [str(STUDY_START), str(STUDY_END)]}
