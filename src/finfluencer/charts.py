"""The page's charts, in Polish and English, each for a light and a dark page:
results/charts/<name>_<lang>_<theme>.png.

Colors are the dataviz skill's reference palette (slots 1-3, validated as a set in both modes).
Exactly two settings, always side by side: US channels on US stocks, Polish channels on GPW stocks.
Labels use the page's glossary ("efekt filmu" / "video effect", "pierwsza sesja po filmie" / "first session after").
"""

import json
from collections.abc import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .analyze import (ALL, CLEANEST, HIGH_LIQ, HIGH_VIEWS, IN_SESSION, LOW_LIQ, LOW_VIEWS,  # noqa: E402
                      NEAR_EARNINGS, NO_EARNINGS, NO_EARNINGS_DATES, OFF_SESSION, PATH, QUIET, QUIET_NO_NEWS,
                      SEGMENTS, groups)
from .config import CHANNELS, MARKETS, RESULTS  # noqa: E402
from .prices import PRICES  # noqa: E402

CHARTS = RESULTS / "charts"
LANGS = ("pl", "en")
THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  axis="#c3c2b7", band="#d9d7cf", s1="#2a78d6", s2="#eb6834", s3="#1baf7a"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 axis="#383835", band="#3b3b38", s1="#3987e5", s2="#d95926", s3="#199e70"),
}
DAYS = list(PATH)

TX = {
    "pl": {
        "short": {"US": "USA", "PL-GPW": "Polska (GPW)"},
        "long": {"US": "USA: youtuberzy z USA, spółki z USA", "PL-GPW": "Polska: youtuberzy z Polski, spółki z GPW"},
        "band": "zakres typowy dla losowych dni (95%)",
        "x_days": "sesje przed filmem i po nim (0 = pierwsza sesja po filmie)",
        "y_effect": "efekt filmu, pkt proc.",
        "before5": "5 sesji przed filmem",
        "first": "pierwsza sesja po filmie",
        "next3": "kolejne 3 sesje",
        "timeline_note": "Szara kreska: zakres typowy dla losowych dni (95%). Słupek poza kreską = wynik, którego "
                         "przypadek raczej nie wyjaśni.",
        "row_all": "Wszystkie opinie",
        "row_no_news": "Test bez newsów",
        "move_signed": "ruch na tle rynku, %\n(w stronę opinii)",
        "move": "ruch na tle rynku, %",
        "random_avg": "średnia losowych dni",
        "actual": "prawdziwe daty filmów",
        "bull": "opinia pozytywna",
        "bear": "opinia negatywna",
        "volume": "obrót ponad zwykły, ≈ %",
        "first_x": "efekt filmu, pkt proc., pierwsza sesja po filmie",
        "change_since": "zmiana od zamknięcia przed filmem, %",
        "video_first": "film →\npierwsza sesja",
        "example_line": "Pierwsza sesja: spółka {s}%, rynek {m}%, na tle rynku {d} pkt proc.",
        "market_us": "rynek: SPY",
        "market_gpw": "rynek: fundusz na WIG20",
        "haiku_opus": "Haiku 5.5 ({e}) i Opus 5.5",
        "claude_gpt": "Claude i GPT · {seg} ({n})",
        "m_same": "ten sam kierunek, gdy oba modele wymieniły spółkę",
        "m_confirmed": "opinia jednego modelu potwierdzona przez drugi",
        "m_opposite": "kierunek przeciwny",
        "pct_stocks": "% spółek",
        "controls": {ALL: "Wszystkie opinie", OFF_SESSION: "Film poza sesją", NO_EARNINGS: "Bez wyników kwartalnych",
                     CLEANEST: "Poza sesją i bez wyników", QUIET: "Poza sesją, spokojny tydzień",
                     QUIET_NO_NEWS: "Test bez newsów", NEAR_EARNINGS: "Przy wynikach kwartalnych"},
    },
    "en": {
        "short": {"US": "US", "PL-GPW": "Poland (WSE)"},
        "long": {"US": "US: US YouTubers, US stocks", "PL-GPW": "Poland: Polish YouTubers, Warsaw stocks"},
        "band": "range typical for random days (95%)",
        "x_days": "sessions before and after the video (0 = first session after)",
        "y_effect": "video effect, pp",
        "before5": "5 sessions before",
        "first": "first session after",
        "next3": "next 3 sessions",
        "timeline_note": "Grey whisker: range typical for random days (95%). A bar beyond it is unlikely to be chance.",
        "row_all": "All calls",
        "row_no_news": "No-news test",
        "move_signed": "move vs the market, %\n(in the call's direction)",
        "move": "move vs the market, %",
        "random_avg": "random-day average",
        "actual": "actual video dates",
        "bull": "bullish call",
        "bear": "bearish call",
        "volume": "volume above normal, ≈ %",
        "first_x": "video effect, pp, first session after",
        "change_since": "change since the close before the video, %",
        "video_first": "video →\nfirst session",
        "example_line": "First session: stock {s}%, market {m}%, vs the market {d} pp",
        "market_us": "market: SPY",
        "market_gpw": "market: WIG20 fund",
        "haiku_opus": "Haiku 5.5 ({e}) vs Opus 5.5",
        "claude_gpt": "Claude vs GPT · {seg} ({n})",
        "m_same": "same direction when both models named the stock",
        "m_confirmed": "one model's call confirmed by the other",
        "m_opposite": "opposite direction",
        "pct_stocks": "% of stocks",
        "controls": {ALL: "All calls", OFF_SESSION: "Video outside trading hours", NO_EARNINGS: "No earnings nearby",
                     CLEANEST: "Outside hours, no earnings", QUIET: "Outside hours, quiet week",
                     QUIET_NO_NEWS: "No-news test", NEAR_EARNINGS: "Near earnings"},
    },
}

# Test-group names (Polish in analyze.py) as they appear on the English charts.
GROUP_EN = {
    ALL: "All calls",
    "Tylko opinie pozytywne": "Bullish calls only",
    "Tylko opinie negatywne": "Bearish calls only",
    "Główny temat filmu, mocna opinia": "Main topic, strong call",
    OFF_SESSION: "Video outside trading hours",
    IN_SESSION: "Video during trading hours",
    NO_EARNINGS: "No earnings within ±3 sessions",
    NEAR_EARNINGS: "Earnings within ±3 sessions",
    NO_EARNINGS_DATES: "No earnings dates available",
    CLEANEST: "Outside hours, no earnings",
    QUIET: "Outside hours, quiet week before",
    QUIET_NO_NEWS: "No-news test",
    LOW_VIEWS: "No-news test: least-watched videos (bottom 1/3)",
    HIGH_VIEWS: "No-news test: most-watched videos (top 1/3)",
    LOW_LIQ: "Least liquid stocks (bottom 1/3)",
    HIGH_LIQ: "Most liquid stocks (top 1/3)",
    "Oceny: Claude Opus 5.5": "Labels: Claude Opus 5.5",
    "Oceny: Claude Haiku 5.5": "Labels: Claude Haiku 5.5",
    "Oceny: GPT-6.1": "Labels: GPT-6.1",
    "Wzmianki bez opinii": "Mentions without a call",
}


def plural(n: int, one: str, few: str, many: str) -> str:
    """Polish noun form for a count: 1 film, 2-4 filmy (but 12-14 filmów), 5+ filmów."""
    n = int(n)
    if n == 1:
        return f"{n} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


def opinions(n: int, lang: str = "pl") -> str:
    return plural(n, "opinia", "opinie", "opinii") if lang == "pl" else f"{int(n):,} calls"


def films(n: int, lang: str = "pl") -> str:
    return plural(n, "film", "filmy", "filmów") if lang == "pl" else f"{int(n):,} videos"


def _num(v: float, digits: int = 2, lang: str = "pl") -> str:
    s = f"{v:+.{digits}f}".replace("-", "−")
    return s.replace(".", ",") if lang == "pl" else s


def _style(ax, th: dict, grid_axis: str = "y") -> None:
    ax.set_facecolor(th["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(th["axis"])
    ax.tick_params(colors=th["muted"], labelsize=9, length=0)
    ax.grid(axis=grid_axis, color=th["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    # Axis numbers in the page's language: Polish decimal comma, and a true minus sign in both.
    comma = th["lang"] == "pl"
    fmt = FuncFormatter(lambda v, _: (f"{v:g}".replace(".", ",") if comma else f"{v:g}").replace("-", "−"))
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)


def _figure(th: dict, *args, **kwargs):
    return plt.subplots(*args, facecolor=th["surface"], **kwargs)


def _title(ax, text: str, th: dict) -> None:
    ax.set_title(text, color=th["ink"], fontsize=11, loc="left", pad=10)


def _render(name: str, draw: Callable[[dict], plt.Figure]) -> None:
    """Calls draw once per language and theme; th carries the colors plus "lang" and the strings "tx"."""
    CHARTS.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        for theme, colors in THEMES.items():
            th = {**colors, "lang": lang, "tx": TX[lang]}
            fig = draw(th)
            fig.savefig(CHARTS / f"{name}_{lang}_{theme}.png", dpi=150, facecolor=th["surface"])
            plt.close(fig)


class Data:
    def __init__(self) -> None:
        self.events = pd.read_csv(RESULTS / "events.csv", low_memory=False)
        self.tests = pd.read_csv(RESULTS / "tests.csv").set_index(["segment", "group", "measure"])
        npz = np.load(RESULTS / "placebo_paths.npz")
        self.paths = {k: npz[k] for k in npz.files}
        self.masks = {(seg, name): mask.to_numpy() for seg, name, mask in groups(self.events)}

    def t(self, seg: str, group: str, measure: str) -> pd.Series | None:
        try:
            row = self.tests.loc[(seg, group, measure)]
        except KeyError:
            return None
        return None if pd.isna(row.get("mean")) else row

    def signed_path(self, mask: np.ndarray) -> np.ndarray:
        """Per opinion, the move against the market in the direction of the opinion, 0 at the close before."""
        ev = self.events[mask]
        ar = np.nan_to_num(ev[[f"ar_{k}" for k in DAYS]].to_numpy())
        ks = np.array(DAYS)
        post = np.cumsum(np.where(ks >= 0, ar, 0), axis=1)
        pre = -np.cumsum(np.where(ks < 0, ar, 0)[:, ::-1], axis=1)[:, ::-1]
        pre = np.concatenate([pre[:, 1:], np.zeros((len(ar), 1))], axis=1)
        sign = np.where(ev["sign"] == 0, 1, ev["sign"])[:, None]
        return np.where(ks >= 0, post, pre) * sign


def _whisker(ax, x, r: pd.Series, th: dict, width: float = 0.05) -> tuple[float, float]:
    lo = (r["placebo_lo"] - r["placebo_mean"]) * 100
    hi = (r["placebo_hi"] - r["placebo_mean"]) * 100
    ax.plot([x, x], [lo, hi], color=th["muted"], linewidth=1.4, zorder=3)
    for y in (lo, hi):
        ax.plot([x - width, x + width], [y, y], color=th["muted"], linewidth=1.4, zorder=3)
    return lo, hi


def timeline(d: Data) -> None:
    """Before the video, the first session after it, the next three: effect against random days."""

    def draw(th: dict) -> plt.Figure:
        tx, lang = th["tx"], th["lang"]
        windows = [("car_pre", tx["before5"], "s2"), ("car_d0", tx["first"], "s1"), ("car_d1-3", tx["next3"], "s3")]
        fig, ax = _figure(th, figsize=(10, 4.6))
        _style(ax, th)
        ax.axhline(0, color=th["axis"], linewidth=1)
        width = 0.24
        for j, (key, label, slot) in enumerate(windows):
            for i, seg in enumerate(SEGMENTS):
                r = d.t(seg, ALL, key)
                x = i + (j - 1) * (width + 0.03)
                v = r["excess"] * 100
                ax.bar(x, v, width=width, color=th[slot], label=label if i == 0 else None, zorder=2)
                lo, hi = _whisker(ax, x, r, th)
                ax.annotate(_num(v, 2, lang), (x, max(v, hi) if v >= 0 else min(v, lo)),
                            xytext=(0, 4 if v >= 0 else -12), textcoords="offset points", ha="center",
                            color=th["ink2"], fontsize=9)
        ax.set_xticks(range(len(SEGMENTS)), [f"{tx['long'][s]}\n{opinions(d.t(s, ALL, 'car_d0')['n_events'], lang)}"
                                             for s in SEGMENTS], color=th["ink2"], fontsize=9.5)
        ax.set_ylabel(tx["y_effect"], color=th["muted"], fontsize=9)
        bottom, top = ax.get_ylim()
        ax.set_ylim(bottom, top + (top - bottom) * 0.22)
        ax.legend(frameon=False, fontsize=9, labelcolor=th["ink2"], ncol=3, loc="upper left")
        ax.text(0, -0.22, tx["timeline_note"], transform=ax.transAxes, color=th["muted"], fontsize=8.5)
        fig.tight_layout()
        return fig

    _render("timeline", draw)


def path_grid(d: Data) -> None:
    def draw(th: dict) -> plt.Figure:
        tx, lang = th["tx"], th["lang"]
        rows = [(ALL, tx["row_all"]), (QUIET_NO_NEWS, tx["row_no_news"])]
        fig, axes = _figure(th, len(rows), len(SEGMENTS), figsize=(11, 3.6 * len(rows) + 0.7), sharey=True)
        for r, (group, row_label) in enumerate(rows):
            for c, seg in enumerate(SEGMENTS):
                ax = axes[r, c]
                _style(ax, th)
                ax.axhline(0, color=th["axis"], linewidth=1)
                ax.axvline(-0.5, color=th["grid"], linewidth=1, linestyle=(0, (3, 3)))
                null = d.paths.get(f"{seg}|{group}|car")
                mask = d.masks[(seg, group)]
                lo, hi = np.quantile(null, [0.025, 0.975], axis=0) * 100
                ax.fill_between(DAYS, lo, hi, color=th["band"], linewidth=0, label=tx["band"])
                ax.plot(DAYS, null.mean(axis=0) * 100, color=th["muted"], linewidth=1.2, linestyle=(0, (4, 3)),
                        label=tx["random_avg"])
                obs = d.signed_path(mask).mean(axis=0) * 100
                ax.plot(DAYS, obs, color=th["s1"], linewidth=2, label=tx["actual"])
                ax.scatter([DAYS[-1]], [obs[-1]], color=th["s1"], s=28, zorder=3)
                ax.annotate(f"{_num(obs[-1], 2, lang)}%", (DAYS[-1], obs[-1]), xytext=(6, 0),
                            textcoords="offset points", color=th["ink2"], fontsize=9, va="center")
                ax.text(0.98, 0.04, opinions(mask.sum(), lang), transform=ax.transAxes, ha="right",
                        color=th["muted"], fontsize=9)
                ax.set_xticks(DAYS)
                ax.set_xlim(DAYS[0] - 0.3, DAYS[-1] + 1.8)
                if r == 0:
                    _title(ax, tx["long"][seg], th)
                if c == 0:
                    ax.set_ylabel(f"{row_label}\n\n{tx['move_signed']}", color=th["muted"], fontsize=9)
                if r == len(rows) - 1:
                    ax.set_xlabel(tx["x_days"], color=th["muted"], fontsize=9)
        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=9, labelcolor=th["ink2"])
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        return fig

    _render("path_grid", draw)


def controls(d: Data) -> None:
    order = [ALL, OFF_SESSION, NO_EARNINGS, CLEANEST, QUIET, QUIET_NO_NEWS, NEAR_EARNINGS]

    def draw(th: dict) -> plt.Figure:
        tx = th["tx"]
        series = [("car_d0", tx["first"], "s1", 0.16), ("car_d1-3", tx["next3"], "s3", -0.16)]
        fig, axes = _figure(th, 1, len(SEGMENTS), figsize=(11, 4.8), sharex=True, sharey=True)
        for ax, seg in zip(axes, SEGMENTS):
            _style(ax, th, grid_axis="x")
            ax.axvline(0, color=th["muted"], linewidth=1)
            for i, group in enumerate(order):
                y = len(order) - 1 - i
                for key, label, slot, off in series:
                    r = d.t(seg, group, key)
                    if r is None:
                        continue
                    lo = (r["placebo_lo"] - r["placebo_mean"]) * 100
                    hi = (r["placebo_hi"] - r["placebo_mean"]) * 100
                    ax.hlines(y + off, lo, hi, color=th["band"], linewidth=5)
                    ax.scatter(r["excess"] * 100, y + off, s=34, color=th[slot], zorder=3,
                               edgecolor=th["surface"], linewidth=1.5, label=label if i == 0 else None)
            ax.set_yticks(range(len(order)), [tx["controls"][g] for g in order][::-1], color=th["ink2"], fontsize=9)
            _title(ax, tx["long"][seg], th)
            ax.set_xlabel(tx["y_effect"], color=th["muted"], fontsize=9)
        handles, labels = axes[0].get_legend_handles_labels()
        handles.append(plt.Line2D([], [], color=th["band"], linewidth=5))
        labels.append(tx["band"])
        fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=9, labelcolor=th["ink2"])
        fig.tight_layout(rect=(0, 0.07, 1, 1))
        return fig

    _render("controls", draw)


def channels(d: Data) -> None:
    rows = []
    for seg in SEGMENTS:
        for c in CHANNELS:
            pre, post = d.t(seg, f"Kanał: {c.name}", "car_pre"), d.t(seg, f"Kanał: {c.name}", "car_d0")
            if pre is not None and post is not None:
                rows.append((c.name.split(" (")[0], seg, pre, post))

    def draw(th: dict) -> plt.Figure:
        tx, lang = th["tx"], th["lang"]
        fig, ax = _figure(th, figsize=(10, 0.7 * len(rows) + 1.6))
        _style(ax, th, grid_axis="x")
        ax.axvline(0, color=th["muted"], linewidth=1)
        h = 0.36
        for i, (_, _, pre, post) in enumerate(rows):
            y = len(rows) - 1 - i
            for off, r, slot, name in [(h / 2 + 0.02, pre, "s2", tx["before5"]),
                                       (-h / 2 - 0.02, post, "s1", tx["first"])]:
                v = r["excess"] * 100
                ax.barh(y + off, v, height=h, color=th[slot], label=name if i == 0 else None, zorder=2)
                ax.annotate(_num(v, 2, lang), (v, y + off), xytext=(4 if v >= 0 else -4, 0),
                            textcoords="offset points", ha="left" if v >= 0 else "right", va="center",
                            color=th["ink2"], fontsize=8.5)
        market = {"US": "USA" if lang == "pl" else "US", "PL-GPW": "GPW" if lang == "pl" else "WSE"}
        ax.set_yticks(range(len(rows)), [f"{n} · {market[s]}" for n, s, _, _ in rows][::-1], color=th["ink2"],
                      fontsize=9)
        ax.set_xlabel(tx["y_effect"], color=th["muted"], fontsize=9)
        ax.legend(frameon=False, fontsize=9, labelcolor=th["ink2"], loc="lower center", ncol=2,
                  bbox_to_anchor=(0.5, 1.0))
        values = [v * 100 for _, _, a, b in rows for v in (a["excess"], b["excess"])]
        ax.set_xlim(min(-0.5, min(values) * 1.35), max(values) * 1.25)
        fig.tight_layout()
        return fig

    _render("channels", draw)


def bull_bear(d: Data) -> None:
    def draw(th: dict) -> plt.Figure:
        tx = th["tx"]
        fig, axes = _figure(th, 1, len(SEGMENTS), figsize=(11, 4.4), sharey=True)
        for ax, seg in zip(axes, SEGMENTS):
            _style(ax, th)
            ax.axhline(0, color=th["axis"], linewidth=1)
            ax.axvline(-0.5, color=th["grid"], linewidth=1, linestyle=(0, (3, 3)))
            ends = []
            for stance, color, label in [(1, th["s1"], tx["bull"]), (-1, th["s2"], tx["bear"])]:
                mask = d.masks[(seg, ALL)] & (d.events["sign"] == stance).to_numpy()
                cum = d.signed_path(mask) * stance * 100
                mean = cum.mean(axis=0)
                se = cum.std(axis=0, ddof=1) / np.sqrt(len(cum))
                ax.fill_between(DAYS, mean - 1.96 * se, mean + 1.96 * se, color=color, alpha=0.15, linewidth=0)
                ax.plot(DAYS, mean, color=color, linewidth=2, label=f"{label} ({int(mask.sum()):,})")
                ends.append([mean[-1], label])
            lo, hi = sorted(ends, key=lambda e: e[0])
            gap = 0.08 * (ax.get_ylim()[1] - ax.get_ylim()[0])
            if hi[0] - lo[0] < gap:
                mid = (hi[0] + lo[0]) / 2
                lo[0], hi[0] = mid - gap / 2, mid + gap / 2
            for y, label in ends:
                ax.annotate(label, (DAYS[-1], y), xytext=(6, 0), textcoords="offset points",
                            color=th["ink2"], fontsize=9, va="center")
            _title(ax, tx["long"][seg], th)
            ax.set_xticks(DAYS)
            ax.set_xlim(DAYS[0] - 0.3, DAYS[-1] + 3.4)
            ax.set_xlabel(tx["x_days"], color=th["muted"], fontsize=9)
            ax.legend(frameon=False, fontsize=8.5, labelcolor=th["ink2"], loc="upper left")
        axes[0].set_ylabel(tx["move"], color=th["muted"], fontsize=9)
        fig.tight_layout()
        return fig

    _render("bull_bear", draw)


def volume(d: Data) -> None:
    def draw(th: dict) -> plt.Figure:
        tx = th["tx"]
        fig, axes = _figure(th, 1, len(SEGMENTS), figsize=(11, 4.0), sharey=True)
        for ax, seg in zip(axes, SEGMENTS):
            _style(ax, th)
            ax.axvline(-0.5, color=th["grid"], linewidth=1, linestyle=(0, (3, 3)))
            null = d.paths.get(f"{seg}|{ALL}|vol")
            mask = d.masks[(seg, ALL)]
            lo, hi = np.quantile(null, [0.025, 0.975], axis=0) * 100
            ax.fill_between(DAYS, lo, hi, color=th["band"], linewidth=0, label=tx["band"])
            ax.plot(DAYS, null.mean(axis=0) * 100, color=th["muted"], linewidth=1.2, linestyle=(0, (4, 3)),
                    label=tx["random_avg"])
            obs = np.nanmean(d.events.loc[mask, [f"vol_{k}" for k in DAYS]].to_numpy(), axis=0) * 100
            ax.plot(DAYS, obs, color=th["s1"], linewidth=2, label=tx["actual"])
            peak = int(np.nanargmax(obs))
            ax.annotate(f"{obs[peak]:+.0f}%".replace("-", "−"), (DAYS[peak], obs[peak]), xytext=(0, 6),
                        textcoords="offset points", ha="center", color=th["ink2"], fontsize=9)
            _title(ax, tx["long"][seg], th)
            ax.set_xticks(DAYS)
            ax.set_xlabel(tx["x_days"], color=th["muted"], fontsize=9)
        axes[0].set_ylabel(tx["volume"], color=th["muted"], fontsize=9)
        axes[0].legend(frameon=False, fontsize=8.5, labelcolor=th["ink2"], loc="upper left")
        fig.tight_layout()
        return fig

    _render("volume", draw)


def group_forest(d: Data) -> None:
    for seg in SEGMENTS:
        rows = [(name, d.t(seg, name, "car_d0")) for s, name in d.masks if s == seg]
        rows = [(n, r) for n, r in rows if r is not None]

        def draw(th: dict, rows=rows, seg=seg) -> plt.Figure:
            tx, lang = th["tx"], th["lang"]

            def label(name: str) -> str:
                if name.startswith("Kanał: "):
                    return name.removeprefix("Kanał: ")
                return name if lang == "pl" else GROUP_EN.get(name, name)

            fig, ax = _figure(th, figsize=(10, 0.4 * len(rows) + 1.3))
            _style(ax, th, grid_axis="x")
            ax.axvline(0, color=th["muted"], linewidth=1)
            for i, (name, r) in enumerate(rows):
                y = len(rows) - 1 - i
                lo = (r["placebo_lo"] - r["placebo_mean"]) * 100
                hi = (r["placebo_hi"] - r["placebo_mean"]) * 100
                ax.hlines(y, lo, hi, color=th["band"], linewidth=6)
                ax.scatter(r["excess"] * 100, y, s=40, color=th["s1"], zorder=3, edgecolor=th["surface"],
                           linewidth=1.5)
            ax.set_yticks(range(len(rows)), [f"{label(n)} ({int(r['n_events']):,})" for n, r in rows][::-1],
                          color=th["ink2"], fontsize=9)
            ax.set_xlabel(tx["first_x"], color=th["muted"], fontsize=9)
            _title(ax, tx["long"][seg], th)
            fig.tight_layout()
            return fig

        _render(f"groups_{seg}", draw)


def pick_examples(d: Data) -> dict:
    """One clear real case per setting, for the method section: off-session, a firm opinion, a 1.5-4% move."""
    ev = d.events
    out = {}
    for seg, stance in (("US", 1), ("PL-GPW", -1)):
        cand = ev[(ev["segment"] == seg) & (ev["sign"] == stance) & ~ev["repeat"] & (ev["timing"] != "in_session")
                  & (ev["conviction"] >= 2) & (ev["focus"] == "main")
                  & (ev["evidence"].fillna("").str.len() < 160)]  # no quotes in the public labels: any length
        signed = cand["car_d0"] * cand["sign"]
        cand = cand[(signed > 0.015) & (signed < 0.04) & (cand["car_pre"].abs() < 0.03)]
        if cand.empty:
            continue
        row = cand.sort_values("published_utc").iloc[-1]
        out[seg] = {k: (v.item() if hasattr(v, "item") else v) for k, v in row[
            ["video_id", "channel", "symbol", "company", "stance", "evidence", "title", "published_utc", "day0",
             "timing", "ar_-1", "ar_0", "car_d0"]].items()}
    (RESULTS / "examples.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def examples(d: Data) -> None:
    picked = pick_examples(d)
    close = pd.read_parquet(PRICES / "close.parquet")
    names = {c.key: c.name for c in CHANNELS}

    def draw(th: dict) -> plt.Figure:
        tx, lang = th["tx"], th["lang"]
        fig, axes = _figure(th, 1, len(picked), figsize=(11, 4.2))
        for ax, (seg, ex) in zip(np.atleast_1d(axes), picked.items()):
            _style(ax, th)
            bench = MARKETS["US" if seg == "US" else "GPW"].benchmark
            px = close[[ex["symbol"], bench]].dropna()
            i = px.index.get_indexer([pd.Timestamp(ex["day0"])])[0]
            window = px.iloc[i - 3:i + 4]
            idx = (window / window.iloc[2] - 1) * 100  # 0 at the close of the session before the video
            ks = list(range(-3, len(idx) - 3))
            ax.axhline(0, color=th["axis"], linewidth=1)
            ax.axvspan(-1, 0, color=th["band"], alpha=0.6, linewidth=0)
            market_label = tx["market_us"] if seg == "US" else tx["market_gpw"]
            ax.plot(ks, idx[ex["symbol"]], color=th["s1"], linewidth=2, marker="o", markersize=4,
                    label=f"{ex['company']} ({ex['symbol']})")
            ax.plot(ks, idx[bench], color=th["muted"], linewidth=1.6, marker="o", markersize=3, label=market_label)
            ax.text(-0.5, 0.02, tx["video_first"], transform=ax.get_xaxis_transform(), ha="center",
                    va="bottom", color=th["ink2"], fontsize=8)
            s0, m0 = idx[ex["symbol"]].iloc[3], idx[bench].iloc[3]
            ax.text(0, 1.13, tx["example_line"].format(s=_num(s0, 1, lang), m=_num(m0, 1, lang),
                                                       d=_num(s0 - m0, 1, lang)),
                    transform=ax.transAxes, color=th["ink2"], fontsize=9)
            ax.legend(frameon=False, fontsize=8.5, labelcolor=th["ink2"], loc="lower center",
                      bbox_to_anchor=(0.5, 1.0), ncol=2)
            opinion = tx["bull"] if ex["stance"] == "bullish" else tx["bear"]
            ax.set_title(f"{names[ex['channel']]}: {opinion}", color=th["ink"], fontsize=11, loc="left", pad=44)
            ax.set_xticks(ks)
            ax.set_xlabel(tx["x_days"], color=th["muted"], fontsize=9)
        np.atleast_1d(axes)[0].set_ylabel(tx["change_since"], color=th["muted"], fontsize=9)
        fig.tight_layout()
        return fig

    if picked:
        _render("examples", draw)


def label_quality() -> None:
    effort_path = RESULTS / "effort_test_claude-haiku-5-5.json"
    agreement_path = RESULTS / "agreement.json"
    effort = json.loads(effort_path.read_text(encoding="utf-8")) if effort_path.exists() else {}
    agreement = json.loads(agreement_path.read_text(encoding="utf-8")) if agreement_path.exists() else {}
    if not effort and not agreement:
        return

    def draw(th: dict) -> plt.Figure:
        tx, lang = th["tx"], th["lang"]
        rows = [(tx["haiku_opus"].format(e=eff), r.get("all", r)) for eff, r in effort.items() if r]
        rows += [(tx["claude_gpt"].format(seg=tx["short"]["US" if c == "US" else "PL-GPW"], n=films(r["videos"], lang)), r)
                 for c, r in agreement.items() if r]
        metrics = [("stance_agreement_when_both_named", tx["m_same"], "s1"),
                   ("directional_same", tx["m_confirmed"], "s3"),
                   ("directional_opposite", tx["m_opposite"], "s2")]
        fig, ax = _figure(th, figsize=(10, 0.85 * len(rows) + 1.6))
        _style(ax, th, grid_axis="x")
        h = 0.24
        for i, (label, r) in enumerate(rows):
            y = len(rows) - 1 - i
            for j, (key, name, slot) in enumerate(metrics):
                v = r[key] * 100
                yy = y + (1 - j) * (h + 0.02)
                ax.barh(yy, v, height=h, color=th[slot], label=name if i == 0 else None, zorder=2)
                ax.annotate(f"{v:.0f}%", (v, yy), xytext=(4, 0), textcoords="offset points", va="center",
                            color=th["ink2"], fontsize=8.5)
        ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1], color=th["ink2"], fontsize=9)
        ax.set_xlim(0, 108)
        ax.set_xlabel(tx["pct_stocks"], color=th["muted"], fontsize=9)
        ax.legend(frameon=False, fontsize=8.5, labelcolor=th["ink2"], loc="lower center", ncol=1,
                  bbox_to_anchor=(0.5, 1.0))
        fig.tight_layout()
        return fig

    _render("label_quality", draw)


def render_all() -> list[str]:
    for old in CHARTS.glob("*.png"):
        old.unlink()
    d = Data()
    for chart in (timeline, examples, path_grid, controls, channels, bull_bear, volume, group_forest):
        chart(d)
    label_quality()
    return sorted(p.name for p in CHARTS.glob("*.png"))
