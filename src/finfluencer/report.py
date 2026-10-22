"""Writes results/report.md (all tables, per segment), the charts, and the HTML page."""

import json

import pandas as pd

from .analyze import (ALL, CLEANEST, NEAR_EARNINGS, NO_EARNINGS, OFF_SESSION, QUIET, QUIET_NO_NEWS,
                      SEGMENTS, WINDOWS)
from .config import CHANNELS, RESULTS, STUDY_END, STUDY_START

WINDOW_LABEL = {"car_d0": "dzień 0", "car_d0-1": "dni 0-1", "car_d0-2": "dni 0-2",
                "car_d0-3": "dni 0-3", "car_d1-3": "dni 1-3 (bez dnia 0)", "carb_d0-3": "dni 0-3, model z betą",
                "car_pre": "dni -5..-1 (przed filmem)", "abvol_d0": "wolumen, dzień 0",
                "abvol_d1": "wolumen, dzień 1", "absar_d0": "ruch dnia 0 bez kierunku",
                "car_d0_mom": "dzień 0, wobec losowych dni z podobnym ruchem przed",
                "car_d0-3_mom": "dni 0-3, wobec losowych dni z podobnym ruchem przed"}
KEY_GROUPS = [ALL, OFF_SESSION, NO_EARNINGS, NEAR_EARNINGS, CLEANEST, QUIET, QUIET_NO_NEWS]


def pct(x: float, digits: int = 2) -> str:
    return "–" if pd.isna(x) else f"{x * 100:+.{digits}f}%"


def verdict(row: pd.Series) -> str:
    if pd.isna(row.get("p_placebo")):
        return "za mało danych"
    if row["q_bh"] < 0.05:
        return "efekt istotny" + (" (zgodny z opinią)" if row["excess"] > 0 else " (PRZECIWNY do opinii)")
    return "brak istotnego efektu"


def load() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    tests = pd.read_csv(RESULTS / "tests.csv")
    reg = pd.read_csv(RESULTS / "regression.csv", index_col=0)
    cov = json.loads((RESULTS / "coverage.json").read_text(encoding="utf-8"))
    return tests, reg, cov


def segment_markdown(seg: str, tests: pd.DataFrame, reg: pd.DataFrame) -> list[str]:
    t = tests[tests["segment"] == seg].set_index(["group", "measure"])
    out = [f"## {SEGMENTS[seg]}", ""]

    out += ["### Wszystkie grupy, dni 0-3", "",
            "| Grupa | Opinie | Filmy | Średnio w kierunku opinii | Losowe dni | Nadwyżka | 95% losowych dni | p | q (BH) | Trafienia | MDE 80% | Werdykt |",
            "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|"]
    for group in dict.fromkeys(t.index.get_level_values(0)):
        r = t.loc[(group, "car_d0-3")]
        if pd.isna(r.get("mean")):
            out.append(f"| {group} | {int(r['n_events'])} | {int(r['n_videos'])} | za mało danych |||||||||")
            continue
        out.append(
            f"| {group} | {int(r['n_events'])} | {int(r['n_videos'])} | {pct(r['mean'])} | {pct(r['placebo_mean'])} "
            f"| {pct(r['excess'])} | {pct(r['placebo_lo'])} … {pct(r['placebo_hi'])} | {r['p_placebo']:.3f} "
            f"| {r['q_bh']:.3f} | {r['hit_rate']:.0%} vs {r['placebo_hit_rate']:.0%} | ±{r['mde_80'] * 100:.2f} p.p. "
            f"| {verdict(r)} |")

    out += ["", "### Okna czasowe", "",
            "| Grupa | Okno | Średnio | Losowe dni | Nadwyżka | p | q (BH) | MDE 80% |",
            "|---|---|---:|---:|---:|---:|---:|---:|"]
    for group in KEY_GROUPS:
        for key in ["car_pre", *(f"car_{w}" for w in WINDOWS), "carb_d0-3", "car_d0_mom", "car_d0-3_mom"]:
            if (group, key) not in t.index:
                continue
            r = t.loc[(group, key)]
            if pd.isna(r.get("mean")):
                continue
            q = "" if pd.isna(r.get("q_bh")) else f"{r['q_bh']:.3f}"
            out.append(f"| {group} | {WINDOW_LABEL[key]} | {pct(r['mean'])} | {pct(r['placebo_mean'])} "
                       f"| {pct(r['excess'])} | {r['p_placebo']:.3f} | {q} | ±{r['mde_80'] * 100:.2f} p.p. |")

    out += ["", "### Wolumen i ruch dnia 0 bez kierunku", "",
            "Wolumen: logarytm względem mediany z sesji -60..-11 (+0.10 ≈ 10% więcej niż zwykle). Ruch bez kierunku: "
            "średni |zwrot ponad rynek| w dniu 0; wyraźnie wyższy niż w losowe dni znaczy, że filmy trafiają na dni z "
            "newsami.", "",
            "| Grupa | Wolumen d0 | Losowe | p | Wolumen d1 | Losowe | p | Ruch d0 bez kierunku | Losowe | p |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for group in KEY_GROUPS + ["Wzmianki bez opinii"]:
        if (group, "abvol_d0") not in t.index:
            continue
        a, b, c = t.loc[(group, "abvol_d0")], t.loc[(group, "abvol_d1")], t.loc[(group, "absar_d0")]
        if pd.isna(a.get("mean")):
            continue
        out.append(f"| {group} | {a['mean']:+.2f} | {a['placebo_mean']:+.2f} | {a['p_placebo']:.3f} "
                   f"| {b['mean']:+.2f} | {b['placebo_mean']:+.2f} | {b['p_placebo']:.3f} "
                   f"| {c['mean'] * 100:.2f}% | {c['placebo_mean'] * 100:.2f}% | {c['p_placebo']:.3f} |")

    r = reg[reg["segment"] == seg]
    out += ["", "### Regresja: co wiąże się z większym ruchem w kierunku opinii (dni 0-3)", "",
            "| Zmienna | Współczynnik | Błąd (klastry po dniu) | p |", "|---|---:|---:|---:|"]
    for name, row in r.iterrows():
        out.append(f"| {name} | {row['coef']:+.4f} | {row['se']:.4f} | {row['p']:.3f} |")
    out += [f"\nObserwacji: {int(r['n'].iloc[0])}.", ""]
    return out


def markdown(tests: pd.DataFrame, reg: pd.DataFrame, cov: dict) -> str:
    out = ["# Czy opinie finansowych youtuberów ruszają kursami akcji?", "",
           f"Okno badania: {STUDY_START} – {STUDY_END}. Dwa osobne środowiska: youtuberzy z USA i spółki z USA, "
           "youtuberzy z Polski i spółki z GPW. Słowniczek i opis metody: `index.html`.", "",
           "Wykresy i wnioski: `index.html`.", ""]
    for seg in SEGMENTS:
        out += segment_markdown(seg, tests, reg)

    names = {c.key: c for c in CHANNELS}
    out += ["## Dane", "", "| Kanał | Kraj | Subskrybenci | Filmy | Z transkrypcją | Ocenione | Pozytywne | Negatywne | Neutralne |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for key, c in cov["per_channel"].items():
        ch = names[key]
        out.append(f"| {ch.name} | {ch.country} | {ch.subscribers:,} | {c['videos']} | {c['with_transcript']} | "
                   f"{c['classified']} | {c['bullish']} | {c['bearish']} | {c['neutral']} |".replace(",", " "))
    out.append(f"\nPominięte wzmianki: {', '.join(f'{k}: {v}' for k, v in cov['dropped_mentions'].items())}.")
    return "\n".join(out) + "\n"


def write_report() -> None:
    from .charts import render_all
    from .page import write_page

    charts = render_all()
    tests, reg, cov = load()
    (RESULTS / "report.md").write_text(markdown(tests, reg, cov), encoding="utf-8")
    write_page(tests, cov, charts)
    print(f"report, {len(charts)} chart images and page written to {RESULTS}", flush=True)
