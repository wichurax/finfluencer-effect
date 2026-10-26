"""The readable page in English and Polish: short answer, glossary, plain method, results. results/index.html.

Two settings only: US channels on US stocks, Polish channels on GPW (Warsaw) stocks. Every term used in the
text and the charts is defined once in the glossary. English is the default; #pl or the switch shows Polish.
"""

import json
from html import escape

import pandas as pd

from .analyze import (ALL, CLEANEST, HIGH_LIQ, HIGH_VIEWS, IN_SESSION, LOW_LIQ, LOW_VIEWS, NEAR_EARNINGS,
                      NO_EARNINGS, QUIET_NO_NEWS)
from .config import CHANNELS, RESULTS, STUDY_END, STUDY_START

CSS = """
/* Layout: one reading column of ~68ch; charts, cards and tables use the wider 1120px frame. */
:root {
  --bg: #f2f4f6; --paper: #fcfcfb; --ink: #14171a; --ink-2: #4a5058; --muted: #737a82;
  --rule: #dde1e5; --accent: #2a6fc4; --accent-soft: #e3eefb; --flat: #e9ebee;
  --display: "Newsreader", "Iowan Old Style", Georgia, serif;
  --body: "Public Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #111213; --paper: #1a1a19; --ink: #eef0f2; --ink-2: #c0c5cb; --muted: #949aa1;
    --rule: #2c2f33; --accent: #6aa6ee; --accent-soft: #1d2b3d; --flat: #26292d; color-scheme: dark;
  }
  :root:not([data-theme="light"]) .th-light { display: none; }
  :root:not([data-theme="light"]) .th-dark { display: block; }
}
:root[data-theme="dark"] {
  --bg: #111213; --paper: #1a1a19; --ink: #eef0f2; --ink-2: #c0c5cb; --muted: #949aa1;
  --rule: #2c2f33; --accent: #6aa6ee; --accent-soft: #1d2b3d; --flat: #26292d; color-scheme: dark;
}
:root[data-theme="dark"] .th-light { display: none; }
:root[data-theme="dark"] .th-dark { display: block; }
.th-dark { display: none; }

/* Language: English unless the root says Polish, so the page reads complete before any script runs. */
html:not([data-lang="pl"]) .lang-pl { display: none; }
html[data-lang="pl"] .lang-en { display: none; }

body { background: var(--bg); color: var(--ink); font: 16px/1.6 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
main { max-width: 1120px; margin: 0 auto; padding-block: 32px 80px; display: grid; gap: 24px; }
.lang-block { display: grid; gap: 64px; }
.prose { max-width: 68ch; }
h1, h2, h3 { font-family: var(--display); font-weight: 600; text-wrap: balance; margin: 0; line-height: 1.15; }
h1 { font-size: clamp(2rem, 5vw, 3.1rem); letter-spacing: -0.01em; }
h2 { font-size: clamp(1.5rem, 3vw, 2rem); }
p { margin: 0; }
section, header { display: grid; gap: 18px; scroll-margin-top: 16px; }
.meta { font-size: 0.9rem; color: var(--muted); }
.lede { font-size: 1.15rem; color: var(--ink-2); }
.num { font-family: var(--mono); font-size: 0.92em; font-variant-numeric: tabular-nums; white-space: nowrap; }
strong { font-weight: 600; }
a { color: var(--accent); }
nav ul { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 8px 18px; font-size: 0.92rem; }

.switch { justify-self: end; display: inline-flex; border: 1px solid var(--rule); border-radius: 8px; overflow: hidden; }
.switch button { font: 600 0.85rem/1 var(--body); padding: 9px 14px; border: 0; background: var(--paper);
  color: var(--ink-2); cursor: pointer; }
.switch button + button { border-left: 1px solid var(--rule); }
.switch button[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
.switch button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

.answer-box { background: var(--paper); border: 1px solid var(--rule); border-radius: 12px; padding: 24px;
  display: grid; gap: 16px; max-width: 80ch; }
.answer-box ul { gap: 12px; }

dl.glossary { display: grid; grid-template-columns: minmax(150px, 230px) minmax(0, 1fr); gap: 14px 28px;
  margin: 0; max-width: 92ch; }
dl.glossary dt { font-weight: 600; }
dl.glossary dd { margin: 0; color: var(--ink-2); }
@media (max-width: 640px) { dl.glossary { grid-template-columns: minmax(0, 1fr); gap: 4px; }
  dl.glossary dd { margin-bottom: 12px; } }

ol.steps { margin: 0; padding-left: 1.4em; display: grid; gap: 18px; max-width: 72ch; }
ol.steps li::marker { font-family: var(--display); font-weight: 600; }
.example { background: var(--paper); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 18px;
  font-size: 0.95rem; color: var(--ink-2); max-width: 92ch; }
.example > strong:first-child { display: block; margin-bottom: 4px; color: var(--ink); }
.example q { font-style: italic; color: var(--ink); }

.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.card { background: var(--paper); border: 1px solid var(--rule); border-radius: 10px; padding: 20px;
  display: grid; gap: 10px; align-content: start; min-width: 0; }
.card h3 { font: 600 0.95rem/1.3 var(--body); color: var(--ink-2); }
.card .big { font: 500 2.2rem/1 var(--mono); font-variant-numeric: tabular-nums; }
.card .unit { font-size: 0.85rem; color: var(--muted); }
.card p { font-size: 0.95rem; color: var(--ink-2); }
.verdict { justify-self: start; font: 600 0.8rem/1 var(--body); padding: 6px 10px; border-radius: 6px; }
.verdict.yes { background: var(--accent-soft); color: var(--accent); }
.verdict.no { background: var(--flat); color: var(--ink-2); }

figure { margin: 0; background: var(--paper); border: 1px solid var(--rule); border-radius: 10px;
  padding: 16px; display: grid; gap: 12px; min-width: 0; }
figure img { width: 100%; height: auto; max-width: 100%; }
figcaption { font-size: 0.92rem; color: var(--ink-2); max-width: 80ch; }
.figs { display: grid; gap: 16px; }

ul { margin: 0; padding-left: 1.2em; display: grid; gap: 8px; }
.table-wrap { overflow-x: auto; background: var(--paper); border: 1px solid var(--rule); border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
th { font-weight: 600; color: var(--muted); font-size: 0.82rem; }
td.r, th.r { text-align: right; }
td.r { font-family: var(--mono); font-variant-numeric: tabular-nums; }
tr:last-child td { border-bottom: 0; }
.note { font-size: 0.88rem; color: var(--muted); }
"""

SCRIPT = """
<script>
(function () {
  var root = document.documentElement;
  function set(lang) {
    root.setAttribute("data-lang", lang);
    root.setAttribute("lang", lang);
    document.querySelectorAll("[data-set-lang]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-set-lang") === lang));
    });
    try { localStorage.setItem("lang", lang); } catch (e) {}
  }
  var hash = location.hash.replace("#", "");
  var lang = hash === "pl" || hash === "en" ? hash : null;
  if (!lang) { try { lang = localStorage.getItem("lang"); } catch (e) {} }
  set(lang === "pl" ? "pl" : "en");
  document.querySelectorAll("[data-set-lang]").forEach(function (b) {
    b.addEventListener("click", function () { set(b.getAttribute("data-set-lang")); });
  });
  window.addEventListener("hashchange", function () {
    var h = location.hash.replace("#", "");
    if (h === "pl" || h === "en") set(h);
  });
})();
</script>
"""

# Hand translations of the Polish quotes the examples may use, keyed by video id.
QUOTE_EN = {
    "RbMT-2GuyU0": "for now the stock continues its downtrend. Next support is PLN 24, another 15% lower",
}


def plural(n: int, one: str, few: str, many: str) -> str:
    """Polish noun form for a count: 1 film, 2-4 filmy (but 12-14 filmów), 5+ filmów."""
    n = int(n)
    if n == 1:
        return f"{n} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


def count(n: float, lang: str, pl: tuple[str, str, str], en: str) -> str:
    if lang == "pl":
        return plural(n, *pl)
    return f"{int(n):,} {en if int(n) != 1 else en.rstrip('s')}"


def opinions(n: float, lang: str) -> str:
    return count(n, lang, ("opinia", "opinie", "opinii"), "calls")


def films(n: float, lang: str) -> str:
    return count(n, lang, ("film", "filmy", "filmów"), "videos")


def pp(x: float, lang: str, digits: int = 2) -> str:
    """A difference of returns in percentage points: +0,48 pkt proc. / +0.48 pp."""
    s = f"{x * 100:+.{digits}f}".replace("-", "−")
    return s.replace(".", ",") + " pkt proc." if lang == "pl" else s + " pp"


def big(x: float, lang: str) -> str:
    s = f"{x * 100:+.2f}".replace("-", "−")
    return s.replace(".", ",") if lang == "pl" else s


def chance(p: float, lang: str) -> str:
    """The permutation p-value in words: how often random days give a result this far out."""
    if lang == "pl":
        if p < 0.001:
            return "rzadziej niż raz na 1000 losowań"
        return f"{round(p * 1000)} razy na 1000 losowań" if p < 0.01 else f"{round(p * 100)} razy na 100 losowań"
    if p < 0.001:
        return "less than once in 1,000 draws"
    return f"{round(p * 1000)} times in 1,000 draws" if p < 0.01 else f"{round(p * 100)} times in 100 draws"


def figure(name: str, lang: str, alt: str, caption: str) -> str:
    return (f'<figure><img class="th-light" src="charts/{name}_{lang}_light.png" alt="{escape(alt)}" loading="lazy">'
            f'<img class="th-dark" src="charts/{name}_{lang}_dark.png" alt="{escape(alt)}" loading="lazy">'
            f"<figcaption>{caption}</figcaption></figure>")


def card(title: str, value: float, lang: str, text: str, verdict: str = "", strong: bool = False) -> str:
    unit = "pkt proc." if lang == "pl" else "pp"
    v = f'<span class="verdict {"yes" if strong else "no"}">{verdict}</span>' if verdict else ""
    return (f'<div class="card"><h3>{title}</h3><div><span class="big">{big(value, lang)}</span> '
            f'<span class="unit">{unit}</span></div>{v}<p>{text}</p></div>')


def facts(tests: pd.DataFrame) -> dict[str, pd.Series]:
    t = tests.set_index(["segment", "group", "measure"])

    def r(seg: str, group: str, measure: str = "car_d0") -> pd.Series:
        return t.loc[(seg, group, measure)]

    return {
        "us_all": r("US", ALL), "us_pre": r("US", ALL, "car_pre"), "us_later": r("US", ALL, "car_d1-3"),
        "us_earn": r("US", NEAR_EARNINGS), "us_noearn": r("US", NO_EARNINGS), "us_clean": r("US", CLEANEST),
        "us_quiet": r("US", QUIET_NO_NEWS), "us_in": r("US", IN_SESSION),
        "pl_all": r("PL-GPW", ALL), "pl_pre": r("PL-GPW", ALL, "car_pre"), "pl_later": r("PL-GPW", ALL, "car_d1-3"),
        "pl_quiet": r("PL-GPW", QUIET_NO_NEWS), "pl_quiet3": r("PL-GPW", QUIET_NO_NEWS, "car_d0-3"),
        "pl_lowliq": r("PL-GPW", LOW_LIQ), "pl_highliq": r("PL-GPW", HIGH_LIQ),
        "pl_lowv": r("PL-GPW", LOW_VIEWS), "pl_highv": r("PL-GPW", HIGH_VIEWS),
        "pl_zi": r("PL-GPW", "Kanał: Zawód Inwestor"),
        "pl_mer": r("PL-GPW", "Kanał: Merytorycznie o Finansach (Piotr Cymcyk)"),
        "pl_sq": r("PL-GPW", "Kanał: Squaber"),
        "pl_gpt": r("PL-GPW", "Oceny: GPT-6.1"),
    }


def extras(lang: str) -> dict[str, str]:
    """Model-agreement lines and the Claude-vs-GPT table, in one language."""
    names = {"US": "USA" if lang == "pl" else "US", "PL": "Polska (GPW)" if lang == "pl" else "Poland (WSE)"}
    out = {"effort": "", "agreement": "", "robustness": ""}
    effort_path = RESULTS / "effort_test_claude-haiku-5-5.json"
    if effort_path.exists():
        e = [v.get("all", v) for v in json.loads(effort_path.read_text(encoding="utf-8")).values() if v]
        same = sorted(round(v["stance_agreement_when_both_named"] * 100) for v in e)
        opposite = max(round(v["directional_opposite"] * 100) for v in e)
        span = f"{same[0]}%" if same[0] == same[-1] else f"{same[0]}–{same[-1]}%"
        out["effort"] = (
            f"<li><strong>Haiku i Opus</strong> ({films(e[0]['videos'], lang)}): ten sam kierunek w {span} spółek przy "
            f"każdym ustawieniu wysiłku modelu, kierunek przeciwny w {opposite}%.</li>" if lang == "pl" else
            f"<li><strong>Haiku vs Opus</strong> ({films(e[0]['videos'], lang)}): same direction for {span} of stocks at "
            f"every effort setting, opposite direction {opposite}%.</li>")
    agreement_path = RESULTS / "agreement.json"
    if agreement_path.exists():
        for country, v in json.loads(agreement_path.read_text(encoding="utf-8")).items():
            if not v:
                continue
            same, opp = f"{v['stance_agreement_when_both_named']:.0%}", f"{round(v['directional_opposite'] * 100)}%"
            out["agreement"] += (
                f"<li><strong>Claude i GPT, {names[country]}</strong> ({films(v['videos'], lang)}): ten sam kierunek "
                f"w {same} spółek, które wymieniły oba modele; kierunek przeciwny w {opp}.</li>" if lang == "pl" else
                f"<li><strong>Claude vs GPT, {names[country]}</strong> ({films(v['videos'], lang)}): same direction for "
                f"{same} of the stocks both models named; opposite direction {opp}.</li>")
    rob_path = RESULTS / "robustness_gpt.csv"
    if rob_path.exists():
        rob = pd.read_csv(rob_path).set_index(["labels", "segment", "group", "measure"])
        rows = []
        for seg, key in (("US", "US"), ("PL-GPW", "PL")):
            for group, glabel in ((ALL, "wszystkie opinie" if lang == "pl" else "all calls"),
                                  (QUIET_NO_NEWS, "test bez newsów" if lang == "pl" else "no-news test")):
                try:
                    c, g = rob.loc[("claude", seg, group, "car_d0")], rob.loc[("gpt", seg, group, "car_d0")]
                except KeyError:
                    continue
                if pd.isna(c.get("excess")) or pd.isna(g.get("excess")):
                    continue
                rows.append(f"<tr><td>{names[key]}</td><td>{glabel}</td>"
                            f'<td class="r">{int(c["n_events"]):,}</td><td class="r">{pp(c["excess"], lang)}</td>'
                            f'<td class="r">{int(g["n_events"]):,}</td><td class="r">{pp(g["excess"], lang)}</td></tr>')
        if rows:
            head = (("Środowisko", "Grupa", "Opinie wg Claude", "Efekt wg Claude", "Opinie wg GPT", "Efekt wg GPT")
                    if lang == "pl" else
                    ("Setting", "Group", "Calls (Claude)", "Effect (Claude)", "Calls (GPT)", "Effect (GPT)"))
            intro = ("Te same filmy ocenione niezależnie przez Claude i przez GPT. Efekt filmu w pierwszej sesji:"
                     if lang == "pl" else
                     "The same videos labelled independently by Claude and by GPT. Video effect in the first session:")
            note = ("GPT ocenił drugi raz tylko część filmów (do wyczerpania limitu), więc w teście bez newsów zostaje "
                    "tu po kilkadziesiąt opinii i żaden wynik w tej tabeli nie jest pewny. Tabela sprawdza tylko, czy "
                    "oba modele prowadzą w tę samą stronę." if lang == "pl" else
                    "GPT relabelled only part of the videos (until its usage limit ran out), so the no-news test has a "
                    "few dozen calls here and no result in this table is conclusive. It only checks that both models "
                    "point the same way.")
            out["robustness"] = (
                f"<p class='prose'>{intro}</p><div class='table-wrap'><table><thead><tr>"
                + "".join(f"<th{' class=\"r\"' if i > 1 else ''}>{h}</th>" for i, h in enumerate(head))
                + "</tr></thead><tbody>" + "".join(rows) + f"</tbody></table></div><p class='prose note'>{note}</p>")
    return out


def channel_table(cov: dict, lang: str) -> str:
    names = {c.key: c for c in CHANNELS}
    country = {"US": "USA" if lang == "pl" else "US", "PL": "Polska" if lang == "pl" else "Poland"}
    rows = "".join(
        f"<tr><td>{escape(names[k].name)}</td><td>{country[names[k].country]}</td>"
        f'<td class="r">{f"{names[k].subscribers:,}".replace(",", " " if lang == "pl" else ",")}</td>'
        f'<td class="r">{c["videos"]:,}</td></tr>'.replace(f'{c["videos"]:,}', str(c["videos"]) if lang == "pl"
                                                            else f'{c["videos"]:,}')
        for k, c in cov["per_channel"].items())
    head = ("Kanał", "Kraj", "Subskrybenci", "Filmy") if lang == "pl" else ("Channel", "Country", "Subscribers", "Videos")
    return ("<div class='table-wrap'><table><thead><tr>"
            + "".join(f"<th{' class=\"r\"' if i > 1 else ''}>{h}</th>" for i, h in enumerate(head))
            + f"</tr></thead><tbody>{rows}</tbody></table></div>")


def example_html(lang: str) -> str:
    path = RESULTS / "examples.json"
    examples = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if "US" not in examples or "PL-GPW" not in examples:
        return ""
    names = {c.key: c.name for c in CHANNELS}
    us, pl = examples["US"], examples["PL-GPW"]
    # The public labels carry no quotes (they are the YouTubers' words); the examples then go without one.
    for ex in (us, pl):
        ex["evidence"] = ex["evidence"] if isinstance(ex.get("evidence"), str) else ""
    if lang == "pl":
        us_quote = f" z cytatem: <q>{escape(us['evidence'])}</q>" if us["evidence"] else "."
        pl_quote = f": <q>{escape(pl['evidence'])}</q>" if pl["evidence"] else "."
        return f"""
  <div class="example">
    <strong>Przykład 1.</strong> {escape(names[us['channel']])}, film „{escape(us['title'])}”.
    Model zapisał opinię pozytywną o {escape(us['company'])}{us_quote}
    W pierwszej sesji po filmie spółka poszła w górę o <span class="num">{pp(us['ar_0'], lang)}</span> mocniej niż
    rynek. Opinia była pozytywna, więc w stronę opinii liczy się to jako <span class="num">{pp(us['ar_0'], lang)}</span>.
  </div>
  <div class="example">
    <strong>Przykład 2.</strong> {escape(names[pl['channel']])}, film „{escape(pl['title'])}”.
    Opinia negatywna o {escape(pl['company'])}{pl_quote}
    W pierwszej sesji po filmie spółka wypadła na tle rynku <span class="num">{pp(pl['ar_0'], lang)}</span>. Opinia
    była negatywna, więc spadek to trafienie: w stronę opinii liczy się jako
    <span class="num">{pp(-pl['ar_0'], lang)}</span>.
  </div>
  {figure("examples", lang, "Kurs dwóch spółek z przykładów na tle rynku, od trzech sesji przed filmem do trzech po nim",
          "Linia niebieska: spółka, szara: rynek, obie liczone od zamknięcia sesji przed filmem. Szary pas: pierwsza "
          "sesja po filmie.")}"""
    quote = QUOTE_EN.get(pl["video_id"]) if pl["evidence"] else None
    pl_quote = (f": <q>{escape(quote)}</q> (translated from Polish)" if quote
                else f": <q>{escape(pl['evidence'])}</q> (in Polish)" if pl["evidence"] else "")
    us_quote = f", with the quote <q>{escape(us['evidence'])}</q>" if us["evidence"] else "."
    return f"""
  <div class="example">
    <strong>Example 1.</strong> {escape(names[us['channel']])}, video “{escape(us['title'])}”.
    The model logged a bullish call on {escape(us['company'])}{us_quote}
    In the first session after the video the stock beat the market by <span class="num">{pp(us['ar_0'], lang)}</span>.
    The call was bullish, so in the call's direction this counts as <span class="num">{pp(us['ar_0'], lang)}</span>.
  </div>
  <div class="example">
    <strong>Example 2.</strong> {escape(names[pl['channel']])}, a Polish video on Warsaw stocks.
    Bearish call on {escape(pl['company'])}{pl_quote}.
    In the first session after the video the stock lagged the market by <span class="num">{pp(pl['ar_0'], lang)}</span>.
    The call was bearish, so the drop is a hit: in the call's direction it counts as
    <span class="num">{pp(-pl['ar_0'], lang)}</span>.
  </div>
  {figure("examples", lang, "Price of the two example stocks against the market, from three sessions before the video to three after",
          "Blue line: the stock; grey: the market; both measured from the close before the video. Grey strip: the "
          "first session after the video.")}"""


def body_pl(f: dict, cov: dict, ex: dict) -> str:
    L = "pl"
    total = sum(c["videos"] for c in cov["per_channel"].values())
    P = lambda key, field="excess": f'<span class="num">{pp(f[key][field], L)}</span>'  # noqa: E731
    return f"""
<header>
  <p class="meta">Eksperyment · {films(total, L)} · {STUDY_START:%m.%Y}–{STUDY_END:%m.%Y}</p>
  <p class="meta">Poprawione 26.10.2026: trzy drobne błędy w kodzie. Wyniki dla USA przesunęły się najwyżej o
  0,02 pkt proc., dla Polski bez zmian; wnioski te same. Szczegóły w README projektu.</p>
  <h1>Czy finansowi youtuberzy ruszają kursami akcji?</h1>
  <nav aria-label="Spis treści"><ul>
    <li><a href="#odpowiedz">Krótka odpowiedź</a></li><li><a href="#slowniczek">Słowniczek</a></li>
    <li><a href="#metoda">Jak to sprawdziłem</a></li><li><a href="#wyniki-usa">Wyniki: USA</a></li>
    <li><a href="#wyniki-polska">Wyniki: Polska</a></li><li><a href="#zaufanie">Na ile ufać ocenom AI</a></li>
    <li><a href="#ograniczenia">Czego nie wiemy</a></li>
  </ul></nav>
</header>

<section id="odpowiedz">
  <h2>Krótka odpowiedź</h2>
  <div class="answer-box">
    <ul>
      <li><strong>USA: nie.</strong> Kurs spółki faktycznie rusza się w dniu filmu w stronę opinii youtubera, ale
      dlatego, że youtuber mówi o spółce w dniu, w którym ruszyła ją jakaś wiadomość, najczęściej wyniki kwartalne.
      Gdy odsiać takie dni, z efektu nie zostaje nic, co dałoby się odróżnić od przypadku.</li>
      <li><strong>Polska (GPW): tak, ale bardzo słabo.</strong> Nawet w dniach bez widocznych wiadomości kurs w
      pierwszej sesji po filmie idzie w stronę opinii o około pół punktu procentowego mocniej niż przypadkiem. Efekt
      się nie cofa i jest większy na małych spółkach.</li>
      <li><strong>Na tym się nie zarobi.</strong> Pół punktu procentowego na jednej sesji to mniej niż różnica między
      ceną kupna i sprzedaży plus prowizja na małej spółce.</li>
    </ul>
    <p class="note">Liczby, wykresy i zastrzeżenia są niżej. Najpierw słowniczek i opis metody, żeby było jasne,
    co dokładnie liczyłem.</p>
  </div>
</section>

<section id="slowniczek">
  <h2>Słowniczek</h2>
  <dl class="glossary">
    <dt>Finfluencer</dt><dd>Youtuber, który mówi o inwestowaniu i giełdzie.</dd>
    <dt>Opinia</dt><dd>Zdanie samego youtubera o przyszłości kursu. Pozytywna: „kupuję”, „jest tania”, „wzrośnie”.
      Negatywna: „sprzedaję”, „jest za droga”, „spadnie”. Samo wspomnienie spółki bez zdania o niej to
      <em>wzmianka bez opinii</em>.</dd>
    <dt>Sesja</dt><dd>Dzień handlu na giełdzie. GPW handluje od 9:00 do 17:05, giełdy w USA od 15:30 do 22:00 czasu
      polskiego.</dd>
    <dt>Pierwsza sesja po filmie</dt><dd>Sesja, która jako pierwsza kończy się po publikacji filmu. Film w niedzielę:
      poniedziałek. Film we wtorek o 20:00: środa. Film we wtorek o 11:00, w trakcie sesji: ten sam wtorek, ale wtedy
      część ruchu z tego dnia wydarzyła się jeszcze przed filmem.</dd>
    <dt>Ruch na tle rynku</dt><dd>Zmiana kursu spółki minus zmiana całego rynku tego samego dnia. Dla USA rynkiem jest
      fundusz SPY (500 największych spółek), dla GPW fundusz na indeks WIG20. Przykład: spółka +3%, rynek +1%, czyli
      ruch na tle rynku to +2 punkty procentowe.</dd>
    <dt>Punkt procentowy (pkt proc.)</dt><dd>Różnica między dwoma procentami: 3% minus 1% to 2 pkt proc.</dd>
    <dt>W stronę opinii</dt><dd>Ruch liczony tak, żeby trafiona opinia dawała plus. Opinia pozytywna i spółka rośnie na
      tle rynku: plus. Opinia negatywna i spółka spada na tle rynku: też plus.</dd>
    <dt>Losowe dni</dt><dd>Punkt odniesienia. Te same filmy przenoszę na przypadkowe dni z tych samych dwóch lat i
      liczę to samo. To pokazuje, ile wychodzi przypadkiem, na przykład dlatego, że youtuberzy chwalą spółki, które
      i tak rosną cały rok.</dd>
    <dt>Efekt filmu</dt><dd>O ile punktów procentowych kurs poszedł w stronę opinii w prawdziwych datach filmów
      mocniej niż w losowych dniach. Zero znaczy, że film niczego nie zmienia.</dd>
    <dt>Szansa przypadku</dt><dd>Jak często losowe dni dają wynik co najmniej tak duży jak prawdziwy (w statystyce:
      p). Przyjmuję, że poniżej 5 razy na 100 to już mało prawdopodobny przypadek. Testów jest kilkadziesiąt, więc
      stosuję też poprawkę na to, że część z nich wyjdzie „ciekawie” przez sam przypadek.</dd>
    <dt>Najmniejszy wykrywalny efekt</dt><dd>Jak mały efekt dane zauważyłyby w 8 przypadkach na 10. Jeśli efektu nie
      widać, a ta liczba jest mała, to mocny znak, że efektu naprawdę nie ma, a nie że danych jest za mało.</dd>
    <dt>News</dt><dd>Wiadomość o spółce, która sama rusza kursem: wyniki kwartalne, raport bieżący (w Polsce ESPI),
      duża umowa, przejęcie, dywidenda.</dd>
    <dt>Test bez newsów</dt><dd>Tylko te filmy, które wyszły poza sesją (wieczorem, w nocy, w weekend), w tygodniu
      przed nimi spółka nie miała dużego ruchu (mniej niż 3% na tle rynku), w trzech sesjach przed nimi dużego
      obrotu (najwyżej 20% ponad zwykły), a tytuł filmu nie mówi o wynikach, raporcie, umowie, dywidendzie ani przejęciu.</dd>
    <dt>Płynność</dt><dd>Ile pieniędzy dziennie obraca się akcjami spółki. W mało płynnej spółce kilkadziesiąt osób,
      które kupują tego samego dnia, może poruszyć kursem.</dd>
  </dl>
</section>

<section id="metoda">
  <h2>Jak to sprawdziłem</h2>
  <ol class="steps">
    <li><strong>Kanały.</strong> Po trzy największe kanały w USA i w Polsce, które regularnie oceniają konkretne
      spółki. Najwięksi ogólnie (Graham Stephan, Andrei Jikh, Marcin Iwuć) prawie nie mówią o pojedynczych
      spółkach, więc nie da się ich tak sprawdzić. Dwa osobne środowiska: kanały z USA i spółki z USA, kanały z
      Polski i spółki z GPW. Polskie kanały często mówią też o spółkach z USA, ale te opinie pominąłem, bo pytanie
      dotyczy wpływu na własną giełdę.</li>
    <li><strong>Filmy.</strong> Wszystkie zwykłe filmy z dwóch lat ({total}), z godziną publikacji co do minuty
      i automatycznymi napisami z YouTube.</li>
    <li><strong>Opinie.</strong> Model językowy (AI) przeczytał napisy każdego filmu i zapisał każdą spółkę, o której
      youtuber ma zdanie: jaka to opinia, jak mocna i krótki cytat jako dowód. Każdą opinię można sprawdzić w pliku
      events.csv.</li>
    <li><strong>Kurs.</strong> Dla każdej opinii policzyłem ruch spółki na tle rynku w trzech oknach: 5 sesji przed
      filmem, pierwsza sesja po filmie i 3 kolejne sesje.</li>
    <li><strong>Porównanie z losowymi dniami.</strong> Każdy film przeniosłem 2000 razy na przypadkową datę z tych
      dwóch lat i policzyłem to samo. Tak jakby ten sam film wyszedł w losowy wtorek sprzed roku. Różnica między
      prawdziwymi datami a losowymi to efekt filmu.</li>
    <li><strong>Odsiewanie newsów.</strong> Najpierw osobno filmy z okolic wyników kwartalnych (±3 sesje) i filmy
      wrzucone w trakcie sesji, potem najostrzejszy filtr: test bez newsów.</li>
  </ol>
  {example_html(L)}
</section>

<section>
  <h2>Co wyszło w obu krajach</h2>
  <p class="prose">W obu krajach wszystko dzieje się przed filmem i w pierwszej sesji po nim. W kolejnych 3 sesjach
  nie ma już żadnego dodatkowego ruchu: USA {P('us_later')}, Polska {P('pl_later')}. W Polsce spółki ruszają się w
  stronę późniejszej opinii już w tygodniu przed filmem ({P('pl_pre')}): polscy youtuberzy często opowiadają o
  spółkach, które właśnie zrobiły ruch.</p>
  {figure("timeline", L, "Efekt filmu przed filmem, w pierwszej sesji po nim i w kolejnych 3 sesjach, w obu krajach",
          "Słupek: efekt filmu. Szara kreska: zakres, w którym mieści się 95% wyników losowych dni. Słupek, który "
          "wychodzi poza kreskę, to wynik, którego przypadek raczej nie wyjaśni.")}
  {figure("path_grid", L, "Ruch na tle rynku w stronę opinii od 5 sesji przed filmem do 5 sesji po nim",
          "Linia niebieska: średni ruch na tle rynku w stronę opinii, liczony od zamknięcia sesji przed filmem. Szare "
          "pole: zakres typowy dla losowych dni. Górny wiersz: wszystkie opinie, dolny: test bez newsów.")}
</section>

<section id="wyniki-usa">
  <h2>USA: kurs rusza wiadomość, nie youtuber</h2>
  <div class="cards">
    {card("Wszystkie opinie", f['us_all']['excess'], L,
          f"Efekt filmu w pierwszej sesji, {opinions(f['us_all']['n_events'], L)}. Szansa przypadku: "
          f"{chance(f['us_all']['p_placebo'], L)}.")}
    {card("Przy wynikach kwartalnych", f['us_earn']['excess'], L,
          f"Filmy w okolicy wyników spółki (±3 sesje), {opinions(f['us_earn']['n_events'], L)}. To tu jest prawie "
          "cały efekt.")}
    {card("Test bez newsów", f['us_quiet']['excess'], L,
          f"{opinions(f['us_quiet']['n_events'], L)}. Szansa przypadku: {chance(f['us_quiet']['p_placebo'], L)}.",
          "w granicach przypadku")}
  </div>
  <ul class="prose">
    <li>Bez filmów z okolic wyników kwartalnych efekt spada do {P('us_noearn')}, a gdy odrzucić też filmy
    wrzucone w trakcie sesji, do {P('us_clean')} (szansa przypadku: {chance(f['us_clean']['p_placebo'], L)}).</li>
    <li>Filmy wrzucone w trakcie sesji mają efekt {P('us_in')}, ale tam część ruchu tego dnia wydarzyła się, zanim
    film się pojawił.</li>
    <li>Dane wykryłyby efekt od około <span class="num">{pp(f['us_clean']['mde_80'], L).lstrip('+')}</span>. Jeśli
    więc amerykańscy youtuberzy w ogóle ruszają kursami, to o mniej.</li>
  </ul>
  {figure("controls", L, "Efekt filmu po kolejnych filtrach odsiewających newsy, w obu krajach",
          "Kropka niebieska: pierwsza sesja po filmie, zielona: kolejne 3 sesje. Szary pasek: zakres typowy dla "
          "losowych dni. W USA kropka pierwszej sesji wraca w szary pasek, gdy odsiać newsy. W Polsce zostaje poza "
          "nim.")}
</section>

<section id="wyniki-polska">
  <h2>Polska (GPW): mały efekt, który zostaje po odsianiu newsów</h2>
  <div class="cards">
    {card("Wszystkie opinie", f['pl_all']['excess'], L,
          f"Efekt filmu w pierwszej sesji, {opinions(f['pl_all']['n_events'], L)}. Szansa przypadku: "
          f"{chance(f['pl_all']['p_placebo'], L)}.")}
    {card("Test bez newsów", f['pl_quiet']['excess'], L,
          f"{opinions(f['pl_quiet']['n_events'], L)}. Szansa przypadku: {chance(f['pl_quiet']['p_placebo'], L)}, "
          "także po poprawce na liczbę testów.", "mało prawdopodobny przypadek", strong=True)}
    {card("Test bez newsów, 4 sesje", f['pl_quiet3']['excess'], L,
          "Pierwsza sesja i 3 kolejne razem. Efekt się nie cofa.")}
  </div>
  <p class="prose"><strong>Co przemawia za tym, że to widzowie:</strong></p>
  <ul class="prose">
    <li><strong>Małe spółki reagują mocniej.</strong> Najmniej płynne spółki: {P('pl_lowliq')}, najbardziej
    płynne: {P('pl_highliq')}.</li>
    <li><strong>Większe kanały mają większy efekt.</strong> Zawód Inwestor (206 tys. subskrybentów) {P('pl_zi')},
    Merytorycznie o Finansach (120 tys.) {P('pl_mer')}, Squaber (44 tys.) {P('pl_sq')}. Kanały są tylko trzy, więc
    to słaba wskazówka.</li>
    <li><strong>Częściej oglądane filmy mają nieco większy efekt.</strong> Test bez newsów: najczęściej oglądane
    filmy kanału {P('pl_highv')}, najrzadziej {P('pl_lowv')}. Różnica mieści się jednak w przypadku.</li>
  </ul>
  <p class="prose"><strong>Co przemawia przeciw:</strong></p>
  <ul class="prose">
    <li>Spółki z GPW publikują dużo raportów bieżących (ESPI), często po zamknięciu sesji. Daty wyników
    kwartalnych miałem tylko dla 45 ze 116 spółek, a filtr tytułów łapie tylko filmy, które o newsie mówią wprost.
    Część efektu może więc nadal pochodzić z newsów, których nie widzę.</li>
    <li>W opiniach ocenionych przez GPT efekt jest słabszy ({P('pl_gpt')}, {opinions(f['pl_gpt']['n_events'], L)})
    i nie odróżnia się od przypadku. To inny, losowy zestaw filmów niż ten oceniony przez Claude, więc może to być
    przypadek, ale warto o tym wiedzieć.</li>
  </ul>
  {figure("channels", L, "Efekt filmu przed filmem i w pierwszej sesji po nim, dla każdego kanału",
          "Pomarańczowy: 5 sesji przed filmem, niebieski: pierwsza sesja po filmie. Kanały z Polski liczone tylko "
          "dla spółek z GPW.")}
</section>

<section>
  <h2>Opinie pozytywne i negatywne osobno</h2>
  {figure("bull_bear", L, "Ruch na tle rynku po opiniach pozytywnych i negatywnych",
          "Tu kierunek nie jest odwracany: trafiona opinia negatywna idzie w dół. Jasne pola: niepewność średniej "
          "(95%). Opinii negatywnych jest 3–5 razy mniej, więc ich linia jest mniej pewna.")}
</section>

<section>
  <h2>Obrót akcjami</h2>
  <p class="prose">Wokół filmów handluje się akcjami więcej niż zwykle, ale obrót rośnie już przed filmem. To ten
  sam obraz co w kursach: youtuberzy mówią o spółkach, którymi rynek już się zajmuje.</p>
  {figure("volume", L, "Obrót akcjami ponad zwykły, od 5 sesji przed filmem do 5 sesji po nim",
          "Obrót w stosunku do zwykłego obrotu spółki z ostatnich miesięcy, w przybliżeniu w procentach. Szare pole: "
          "zakres typowy dla losowych dni.")}
</section>

<section id="zaufanie">
  <h2>Na ile ufać ocenom AI</h2>
  <p class="prose">Opinie z napisów ocenił model językowy: większość Claude Haiku 5.5, część Claude Opus 5.5 i GPT-6.1.
  Żeby sprawdzić, czy oceny są wiarygodne, część filmów oceniły niezależnie dwa różne modele. Najczęściej różnią się
  tym, czy krótka wzmianka to już opinia. Odwrotnych kierunków prawie nie ma.</p>
  <ul class="prose">{ex['effort']}{ex['agreement']}</ul>
  {figure("label_quality", L, "Zgodność ocen między modelami",
          "Niebieski: ten sam kierunek, gdy oba modele wymieniły spółkę. Zielony: opinia jednego modelu potwierdzona "
          "przez drugi. Pomarańczowy: kierunek przeciwny.")}
  {ex['robustness']}
</section>

<section id="ograniczenia" class="prose">
  <h2>Czego nie wiemy</h2>
  <ul>
    <li><strong>To korelacja, nie dowód przyczyny.</strong> W Polsce nie da się wykluczyć newsów, których nie ma w
    danych.</li>
    <li><strong>Oglądalność to wyświetlenia dziś</strong>, a nie w dniu filmu. Starsze filmy miały więcej czasu, by
    je zebrać.</li>
    <li><strong>Rynek dla GPW to fundusz na WIG20</strong>, czyli 20 największych spółek. Szeroki indeks WIG byłby
    lepszy dla małych spółek, ale nie udało mi się pobrać jego notowań. Nie zmienia to wniosków, bo losowe dni
    liczę tak samo, ale dodaje szumu.</li>
    <li><strong>Brak efektu w USA nie znaczy, że rynek jest racjonalny.</strong> Znaczy tylko, że ci youtuberzy nie są
    źródłem ruchu, tylko go komentują.</li>
  </ul>
</section>

<section>
  <h2>Wszystkie testy</h2>
  <p class="prose">Każda kropka to efekt filmu w pierwszej sesji dla jednej grupy opinii; w nawiasie liczba opinii.
  Kropka poza szarym paskiem to wynik, którego przypadek raczej nie wyjaśni. Pełne tabele są w pliku report.md.</p>
  <div class="figs">
    {figure("groups_US", L, "Wszystkie testy dla USA", "USA.")}
    {figure("groups_PL-GPW", L, "Wszystkie testy dla Polski", "Polska (GPW).")}
  </div>
</section>

<section>
  <h2>Kanały</h2>
  {channel_table(cov, L)}
</section>
"""


def body_en(f: dict, cov: dict, ex: dict) -> str:
    L = "en"
    total = sum(c["videos"] for c in cov["per_channel"].values())
    P = lambda key, field="excess": f'<span class="num">{pp(f[key][field], L)}</span>'  # noqa: E731
    return f"""
<header>
  <p class="meta">Experiment · {films(total, L)} · {STUDY_START:%b %Y} – {STUDY_END:%b %Y}</p>
  <p class="meta">Corrected 26 Oct 2026: three small faults in the code. U.S. numbers moved by at most 0.02 pp,
  Polish ones not at all; the conclusions stand. Details in the project's README.</p>
  <h1>Do finance YouTubers move stock prices?</h1>
  <nav aria-label="Contents"><ul>
    <li><a href="#answer">Short answer</a></li><li><a href="#glossary">Glossary</a></li>
    <li><a href="#method">How I tested it</a></li><li><a href="#results-us">Results: US</a></li>
    <li><a href="#results-poland">Results: Poland</a></li><li><a href="#trust">How far to trust the AI labels</a></li>
    <li><a href="#limits">What we don't know</a></li>
  </ul></nav>
</header>

<section id="answer">
  <h2>Short answer</h2>
  <div class="answer-box">
    <ul>
      <li><strong>US: no.</strong> Stocks do move in the direction of the YouTuber's call on the day of the video, but
      because YouTubers talk about stocks on days when news is already moving them, most often quarterly earnings.
      Take those days out and nothing is left that can be told apart from chance.</li>
      <li><strong>Poland (Warsaw Stock Exchange): yes, but only slightly.</strong> Even on days with no visible news,
      the stock moves in the call's direction by about half a percentage point more than chance in the first session
      after the video. The move doesn't reverse, and it's larger in small stocks.</li>
      <li><strong>You can't trade on it.</strong> Half a percentage point in one session is less than the bid-ask
      spread plus commission on a small stock.</li>
    </ul>
    <p class="note">Numbers, charts and caveats are below. First a glossary and the method, so it's clear what
    exactly I measured.</p>
  </div>
</section>

<section id="glossary">
  <h2>Glossary</h2>
  <dl class="glossary">
    <dt>Finfluencer</dt><dd>A YouTuber who talks about investing and the stock market.</dd>
    <dt>Call</dt><dd>The YouTuber's own view of where a stock goes next. Bullish: “I'm buying”, “it's cheap”, “it'll
      go up”. Bearish: “I'm selling”, “it's overvalued”, “it'll drop”. Naming a stock without a view is a
      <em>mention without a call</em>.</dd>
    <dt>Session</dt><dd>A trading day. Warsaw trades 9:00–17:05 Central European time; US exchanges trade
      9:30–16:00 Eastern time.</dd>
    <dt>First session after the video</dt><dd>The first session that closes after the video goes live. Video on a
      Sunday: Monday. Video on Tuesday evening: Wednesday. Video on Tuesday during trading hours: that same Tuesday,
      but then part of that day's move happened before the video.</dd>
    <dt>Move vs the market</dt><dd>The stock's change minus the whole market's change on the same day. For the US the
      market is the SPY fund (the 500 largest companies); for Warsaw it's a fund tracking the WIG20 index. Example:
      stock +3%, market +1%, so the move vs the market is +2 percentage points.</dd>
    <dt>Percentage point (pp)</dt><dd>The difference between two percentages: 3% minus 1% is 2 pp.</dd>
    <dt>In the call's direction</dt><dd>The move counted so that a correct call scores a plus. Bullish call and the
      stock beats the market: plus. Bearish call and the stock lags the market: also plus.</dd>
    <dt>Random days</dt><dd>The baseline. I move the same videos to random dates in the same two years and measure
      the same thing. That shows what you get by chance, for example because YouTubers praise stocks that rise all
      year anyway.</dd>
    <dt>Video effect</dt><dd>How many percentage points more the stock moved in the call's direction on the real
      video dates than on random days. Zero means the video changes nothing.</dd>
    <dt>Chance of a fluke</dt><dd>How often random days give a result at least as large as the real one (in
      statistics: p). Below 5 times in 100 I treat it as unlikely to be chance. There are dozens of tests, so I
      also correct for some of them looking “interesting” by luck alone.</dd>
    <dt>Smallest detectable effect</dt><dd>How small an effect the data would catch 8 times out of 10. If there's no
      effect and this number is small, that's strong evidence the effect really isn't there, rather than too little
      data.</dd>
    <dt>News</dt><dd>Company news that moves the price by itself: quarterly earnings, regulatory filings (current
      reports in Poland), a big contract, a takeover, a dividend.</dd>
    <dt>No-news test</dt><dd>Only videos that went live outside trading hours (evening, night, weekend), where the
      stock had no big move (under 3% vs the market) in the week before and no unusual volume (at most 20% above
      normal) in the three sessions before, and whose title doesn't mention earnings, a report, a contract, a dividend or a takeover.</dd>
    <dt>Liquidity</dt><dd>How much money trades in the stock each day. In an illiquid stock, a few dozen people buying
      on the same day can move the price.</dd>
  </dl>
</section>

<section id="method">
  <h2>How I tested it</h2>
  <ol class="steps">
    <li><strong>Channels.</strong> The three largest channels in the US and in Poland that regularly give calls on
      specific stocks. The largest finance channels overall (Graham Stephan, Andrei Jikh, Marcin Iwuć) hardly ever
      talk about individual stocks, so they can't be tested this way. Two separate settings: US channels and US
      stocks, Polish channels and Warsaw stocks. Polish channels often talk about US stocks too, but I left those
      calls out, because the question is about influence on the home market.</li>
    <li><strong>Videos.</strong> Every regular video from two years ({total:,}), with the publish time to the minute
      and YouTube's automatic captions.</li>
    <li><strong>Calls.</strong> A language model (AI) read the captions of each video and logged every stock the
      YouTuber has a view on: which way, how strongly, and a short quote as evidence. Every call can be checked in
      events.csv.</li>
    <li><strong>Price.</strong> For each call I measured the stock's move vs the market in three windows: 5 sessions
      before the video, the first session after it, and the next 3 sessions.</li>
    <li><strong>Comparison with random days.</strong> I moved each video to a random date in those two years 2,000
      times and measured the same thing. As if the same video had come out on a random Tuesday a year earlier. The
      difference between the real dates and the random ones is the video effect.</li>
    <li><strong>Filtering out news.</strong> First separately: videos near quarterly earnings (±3 sessions) and videos
      posted during trading hours. Then the strictest filter: the no-news test.</li>
  </ol>
  {example_html(L)}
</section>

<section>
  <h2>What happened in both countries</h2>
  <p class="prose">In both countries everything happens before the video and in the first session after it. The next
  3 sessions add nothing: US {P('us_later')}, Poland {P('pl_later')}. In Poland stocks are already moving in the
  direction of the later call in the week before the video ({P('pl_pre')}): Polish YouTubers often talk about stocks
  that have just made a move.</p>
  {figure("timeline", L, "Video effect before the video, in the first session after it and in the next 3 sessions",
          "Bar: the video effect. Grey whisker: the range that holds 95% of random-day results. A bar that goes "
          "beyond the whisker is unlikely to be chance.")}
  {figure("path_grid", L, "Move vs the market in the call's direction, from 5 sessions before to 5 after the video",
          "Blue line: the average move vs the market in the call's direction, measured from the close before the "
          "video. Grey area: the range typical for random days. Top row: all calls; bottom row: the no-news test.")}
</section>

<section id="results-us">
  <h2>US: news moves the stock, not the YouTuber</h2>
  <div class="cards">
    {card("All calls", f['us_all']['excess'], L,
          f"Video effect in the first session, {opinions(f['us_all']['n_events'], L)}. Chance of a fluke: "
          f"{chance(f['us_all']['p_placebo'], L)}.")}
    {card("Near quarterly earnings", f['us_earn']['excess'], L,
          f"Videos around a company's earnings (±3 sessions), {opinions(f['us_earn']['n_events'], L)}. Almost the "
          "whole effect sits here.")}
    {card("No-news test", f['us_quiet']['excess'], L,
          f"{opinions(f['us_quiet']['n_events'], L)}. Chance of a fluke: {chance(f['us_quiet']['p_placebo'], L)}.",
          "within chance")}
  </div>
  <ul class="prose">
    <li>Without videos near quarterly earnings the effect falls to {P('us_noearn')}, and without videos posted during
    trading hours as well, to {P('us_clean')} (chance of a fluke: {chance(f['us_clean']['p_placebo'], L)}).</li>
    <li>Videos posted during trading hours show {P('us_in')}, but part of that day's move happened before the video
    appeared.</li>
    <li>The data would catch an effect from about <span class="num">{pp(f['us_clean']['mde_80'], L).lstrip('+')}</span>.
    So if US YouTubers move prices at all, it's by less than that.</li>
  </ul>
  {figure("controls", L, "Video effect after each news filter, in both countries",
          "Blue dot: first session after the video; green: the next 3 sessions. Grey bar: the range typical for random "
          "days. In the US the first-session dot falls back into the grey bar once news is filtered out. In Poland it "
          "stays outside.")}
</section>

<section id="results-poland">
  <h2>Poland (WSE): a small effect that survives the news filter</h2>
  <div class="cards">
    {card("All calls", f['pl_all']['excess'], L,
          f"Video effect in the first session, {opinions(f['pl_all']['n_events'], L)}. Chance of a fluke: "
          f"{chance(f['pl_all']['p_placebo'], L)}.")}
    {card("No-news test", f['pl_quiet']['excess'], L,
          f"{opinions(f['pl_quiet']['n_events'], L)}. Chance of a fluke: {chance(f['pl_quiet']['p_placebo'], L)}, "
          "also after correcting for the number of tests.", "unlikely to be chance", strong=True)}
    {card("No-news test, 4 sessions", f['pl_quiet3']['excess'], L,
          "The first session and the next 3 together. The effect doesn't reverse.")}
  </div>
  <p class="prose"><strong>What points to the viewers:</strong></p>
  <ul class="prose">
    <li><strong>Small stocks react more.</strong> Least liquid stocks: {P('pl_lowliq')}; most liquid: {P('pl_highliq')}.</li>
    <li><strong>Bigger channels show a bigger effect.</strong> Zawód Inwestor (206k subscribers) {P('pl_zi')},
    Merytorycznie o Finansach (120k) {P('pl_mer')}, Squaber (44k) {P('pl_sq')}. There are only three channels, so
    this is a weak hint.</li>
    <li><strong>More-watched videos show a slightly bigger effect.</strong> No-news test: a channel's most-watched
    videos {P('pl_highv')}, least-watched {P('pl_lowv')}. The difference is within chance, though.</li>
  </ul>
  <p class="prose"><strong>What points against it:</strong></p>
  <ul class="prose">
    <li>Warsaw-listed companies publish many current reports (ESPI), often after the close. I had earnings dates for
    only 45 of 116 stocks, and the title filter only catches videos that name the news. Part of the effect may still
    come from news I can't see.</li>
    <li>Among the calls labelled by GPT the effect is weaker ({P('pl_gpt')}, {opinions(f['pl_gpt']['n_events'], L)})
    and can't be told apart from chance. That's a different, random set of videos from the one Claude labelled, so it
    may be luck, but it's worth knowing.</li>
  </ul>
  {figure("channels", L, "Video effect before the video and in the first session after it, per channel",
          "Orange: 5 sessions before the video; blue: first session after. Polish channels counted on Warsaw stocks only.")}
</section>

<section>
  <h2>Bullish and bearish calls separately</h2>
  {figure("bull_bear", L, "Move vs the market after bullish and bearish calls",
          "The direction isn't flipped here: a correct bearish call goes down. Shaded areas: uncertainty of the "
          "average (95%). There are 3–5 times fewer bearish calls, so their line is less certain.")}
</section>

<section>
  <h2>Trading volume</h2>
  <p class="prose">More shares trade around the videos than usual, but volume rises before the video. Same picture as
  in prices: YouTubers talk about stocks the market is already busy with.</p>
  {figure("volume", L, "Trading volume above normal, from 5 sessions before to 5 after the video",
          "Volume relative to the stock's normal volume over recent months, roughly in percent. Grey area: the range "
          "typical for random days.")}
</section>

<section id="trust">
  <h2>How far to trust the AI labels</h2>
  <p class="prose">A language model labelled the calls in the captions: mostly Claude Haiku 5.5, some Claude Opus 5.5
  and GPT-6.1. To check the labels, part of the videos were labelled independently by two different models. They
  mostly disagree on whether a passing mention is already a call. Opposite directions are rare.</p>
  <ul class="prose">{ex['effort']}{ex['agreement']}</ul>
  {figure("label_quality", L, "Agreement between models",
          "Blue: same direction when both models named the stock. Green: one model's call confirmed by the other. "
          "Orange: opposite direction.")}
  {ex['robustness']}
</section>

<section id="limits" class="prose">
  <h2>What we don't know</h2>
  <ul>
    <li><strong>This is correlation, not proof of cause.</strong> In Poland I can't rule out news that isn't in the
    data.</li>
    <li><strong>Views are today's view counts</strong>, not the count on the day of the video. Older videos had more
    time to collect them.</li>
    <li><strong>The Warsaw market proxy is a WIG20 fund</strong>, the 20 largest companies. The broad WIG index would
    suit small stocks better, but I couldn't download its prices. It doesn't change the conclusions, because random
    days are measured the same way, but it adds noise.</li>
    <li><strong>No effect in the US doesn't mean the market is rational.</strong> It only means these YouTubers aren't
    the source of the moves; they comment on them.</li>
  </ul>
</section>

<section>
  <h2>All tests</h2>
  <p class="prose">Each dot is the video effect in the first session for one group of calls; the number of calls is in
  brackets. A dot outside the grey bar is unlikely to be chance. Full tables are in report.md.</p>
  <div class="figs">
    {figure("groups_US", L, "All tests for the US", "US.")}
    {figure("groups_PL-GPW", L, "All tests for Poland", "Poland (WSE).")}
  </div>
</section>

<section>
  <h2>Channels</h2>
  {channel_table(cov, L)}
</section>
"""


def write_page(tests: pd.DataFrame, cov: dict, charts: list[str]) -> None:
    f = facts(tests)
    html = f"""<title>Finfluencers vs Stock Prices</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,500;6..72,600&family=Public+Sans:wght@400;600&display=swap">
<style>{CSS}</style>
<main>
  <div class="switch" role="group" aria-label="Language / Język">
    <button type="button" data-set-lang="en" aria-pressed="true">EN</button>
    <button type="button" data-set-lang="pl" aria-pressed="false">PL</button>
  </div>
  <div class="lang-block lang-en" lang="en">{body_en(f, cov, extras("en"))}</div>
  <div class="lang-block lang-pl" lang="pl">{body_pl(f, cov, extras("pl"))}</div>
</main>
{SCRIPT}
"""
    html = html.replace("p.p.</span>.", "p.p.</span>").replace("p.p..", "p.p.")
    (RESULTS / "index.html").write_text(html, encoding="utf-8")
